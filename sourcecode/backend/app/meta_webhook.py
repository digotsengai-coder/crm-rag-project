"""
Meta 平台（Facebook 粉專 + Instagram 私訊）Webhook。

Meta 的 Webhooks 是「整個 App 一組 Callback URL／Verify Token」，不是每個產品各自一組：
商家在 Meta App 後台只設定一次這支端點，之後不論是粉專訊息（payload.object == "page"）
還是 Instagram 私訊（payload.object == "instagram"），Meta 都會打同一個 URL，所以這裡
用同一個 router 依 object 分流，而不是拆成兩條平行路由。

Facebook／Instagram 都僅作為 CRM 的另一個聊天入口。實際問題處理由 main.py 的
_handle_chat() 負責，避免重複實作訂單查詢、RAG、LLM 等邏輯。
"""

import hashlib
import hmac
import json
import urllib.error
import urllib.request
from typing import Awaitable, Callable

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from app.schemas import ChatResponse
from app.accounts_store import get_chatbot
from app.chat_log import log_chat


FACEBOOK_SEND_API = "https://graph.facebook.com/v21.0/me/messages"

# 走的是「Instagram API with Instagram Login」這條新流程（後台「含有 Instagram 登入的
# API 設定」分頁，取得的是 instagram_business_basic／instagram_business_manage_messages
# 權限），這條流程的所有端點主機是 graph.instagram.com，不是 graph.facebook.com——
# 之前誤用 graph.facebook.com 會讓回覆送出失敗（收到訊息、RAG 也答得出來，但 Send API
# 呼叫失敗，使用者端完全看不到任何回覆）。
INSTAGRAM_SEND_API_TEMPLATE = "https://graph.instagram.com/v21.0/{ig_id}/messages"


def create_meta_router(
    chat_handler: Callable[[str, list, str, str | None], Awaitable[ChatResponse]],
) -> APIRouter:
    router = APIRouter()

    def verify_signature(body: bytes, signature: str, app_secret: str) -> bool:
        """
        驗證 Meta 送來的 X-Hub-Signature-256（格式 "sha256=<hex>"）。
        Facebook 與 Instagram 事件都是同一個 Meta App 送出，共用同一把 App Secret。
        """
        if not app_secret or not signature or not signature.startswith("sha256="):
            return False

        expected = hmac.new(
            app_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature[len("sha256="):])

    def format_chat_response(response: ChatResponse) -> str:
        """
        將 CRM 原本的 ChatResponse 轉換成 Messenger／Instagram 可顯示的純文字。
        """

        if response.type == "order":
            items = response.items or []

            if isinstance(items, list):
                item_text = "\n".join(
                    f"• {item}" if isinstance(item, str) else f"• {str(item)}"
                    for item in items
                )
            else:
                item_text = str(items)

            text = (
                f"訂單編號：{response.code}\n"
                f"目前狀態：{response.status}\n"
                f"預計時間：{response.eta}"
            )

            if item_text:
                text += f"\n商品：\n{item_text}"

            return text

        return response.text or "目前無法取得回覆，請稍後再試。"

    def send_facebook_message(psid: str, message: str, page_access_token: str):
        """
        使用 Facebook Send API 回覆粉專訊息。不需額外安裝 requests/httpx。
        """

        payload = {
            "recipient": {"id": psid},
            "message": {"text": message[:2000]},
        }

        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        req = urllib.request.Request(
            f"{FACEBOOK_SEND_API}?access_token={page_access_token}",
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                print(f"[Facebook Send Success] HTTP {response.status}")

        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            print(f"[Facebook Send API Error] HTTP {e.code}: {detail}")

        except Exception as e:
            print(f"[Facebook Send Error] {e}")

    def send_instagram_message(
        igsid: str, message: str, instagram_business_id: str, instagram_access_token: str
    ):
        """
        使用 Instagram Send API 回覆私訊。不需額外安裝 requests/httpx。
        """

        payload = {
            "recipient": {"id": igsid},
            "message": {"text": message[:1000]},
        }

        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        url = INSTAGRAM_SEND_API_TEMPLATE.format(ig_id=instagram_business_id)

        req = urllib.request.Request(
            f"{url}?access_token={instagram_access_token}",
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                print(f"[Instagram Send Success] HTTP {response.status}")

        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            print(f"[Instagram Send API Error] HTTP {e.code}: {detail}")

        except Exception as e:
            print(f"[Instagram Send Error] {e}")

    async def _answer_and_log(
        user_text: str, chatbot_id: str, channel: str
    ) -> str:
        """
        呼叫共用的 _handle_chat() 取得回覆、寫入 chat_log；Facebook／Instagram 共用同一套邏輯，
        只有 client_ip 標記的管道名稱不同，方便之後在聊天紀錄分辨訊息來源。
        """
        try:
            # 第一版暫時不帶入歷史對話作為上下文，但每次問答仍會寫入既有 chat_log。
            # provider 使用目前 CRM 預設的 Gemini。
            crm_response = await chat_handler(user_text, [], "google", chatbot_id)

            reply_text = format_chat_response(crm_response)

            try:
                log_text = (
                    crm_response.text
                    if crm_response.text is not None
                    else f"[訂單 {crm_response.code}]"
                )

                log_chat(
                    message=user_text,
                    response_type=crm_response.type,
                    response_text=log_text,
                    client_ip=channel,
                    chatbot_id=chatbot_id,
                )
            except Exception as e:
                # 對話紀錄失敗不能影響回覆
                print(f"[{channel} Chat Log Error] {e}")

        except Exception as e:
            print(f"[{channel} Chat Error] {e}")

            reply_text = (
                "系統目前發生錯誤，"
                "請稍後再試或聯繫真人客服（0800-123-456）。"
            )

        return reply_text

    @router.get("/meta/webhook/{chatbot_id}", response_class=PlainTextResponse)
    async def meta_webhook_verify(
        chatbot_id: str,
        hub_mode: str = Query(default="", alias="hub.mode"),
        hub_verify_token: str = Query(default="", alias="hub.verify_token"),
        hub_challenge: str = Query(default="", alias="hub.challenge"),
    ):
        """
        Meta 設定 Webhook 時發出的驗證請求：mode/verify_token 核對成功才回傳 challenge。
        Facebook 與 Instagram 產品共用同一個 App 層級的 Verify Token。
        """
        chatbot = get_chatbot(chatbot_id)
        verify_token = chatbot.get("facebook_verify_token") if chatbot else None

        if (
            not verify_token
            or hub_mode != "subscribe"
            or not hmac.compare_digest(hub_verify_token, verify_token)
        ):
            raise HTTPException(status_code=403, detail="Verification failed")

        return hub_challenge

    @router.post("/meta/webhook/{chatbot_id}")
    async def meta_webhook(chatbot_id: str, request: Request):
        """
        接收 Facebook Messenger 與 Instagram 的訊息事件；依 payload.object 分流。
        """
        chatbot = get_chatbot(chatbot_id)

        if not chatbot:
            raise HTTPException(status_code=404, detail="Chatbot not found")

        body = await request.body()
        signature = request.headers.get("X-Hub-Signature-256", "")

        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON")

        object_type = payload.get("object")
        entries = payload.get("entry", [])

        # Verify Token 是 Meta App 層級、Facebook／Instagram 共用；但簽章用的 App Secret
        # 不是——Meta 用「Instagram API」這個子產品自己的 App Secret（跟主 App 的
        # facebook_app_secret 不同）簽 object=="instagram" 的請求，用主 App 的
        # facebook_app_secret 簽 object=="page" 的請求。用錯密鑰會讓簽章一律驗證失敗，
        # 而且是無聲的（webhook 收到請求但直接被拒絕，機器人永遠不會回覆）。
        app_secret = (
            chatbot.get("instagram_app_secret")
            if object_type == "instagram"
            else chatbot.get("facebook_app_secret")
        )

        if not app_secret:
            raise HTTPException(status_code=500, detail="Meta app secret is not configured")

        if not verify_signature(body, signature, app_secret):
            raise HTTPException(status_code=400, detail="Invalid Meta signature")

        # 實測發現：Facebook Messenger 與 Instagram（含「含 Instagram 登入的 API 設定」
        # 這條新流程）的真實訊息事件格式是同一種 entry[].messaging[]（sender/recipient/
        # message 都在 messaging 事件本身）。Meta 後台「messages 欄位」內建的合成測試
        # 按鈕給的官方範例 payload（entry[].changes[]，value 裡才有 sender/recipient/
        # message）跟真實訊息格式不同，只適用於那顆測試按鈕，拿真實訊息 log 出來比對後才
        # 確認這件事——之前誤信官方範例，導致 Instagram 訊息進來後迴圈完全找不到資料可
        # 處理，收到 200 但沒有任何 log、也不會回覆。
        if object_type in ("page", "instagram"):
            for entry in entries:
                for event in entry.get("messaging", []):
                    message = event.get("message", {})

                    # 機器人自己剛送出去的訊息也會被推播回來（is_echo），必須跳過，
                    # 否則會自問自答造成無窮迴圈。postback 等其他事件類型第一版先不處理。
                    if not message or message.get("is_echo"):
                        continue

                    user_text = (message.get("text") or "").strip()
                    sender_id = (event.get("sender") or {}).get("id")

                    if not user_text or not sender_id:
                        continue

                    if object_type == "page":
                        page_access_token = chatbot.get("facebook_page_access_token")
                        if not page_access_token:
                            print("[Facebook Chat Error] page access token is not configured")
                            continue

                        reply_text = await _answer_and_log(user_text, chatbot_id, "Facebook")
                        send_facebook_message(sender_id, reply_text, page_access_token)

                    else:
                        instagram_business_id = chatbot.get("instagram_business_id")
                        instagram_access_token = chatbot.get("instagram_access_token")
                        if not instagram_business_id or not instagram_access_token:
                            print("[Instagram Chat Error] instagram credentials are not configured")
                            continue

                        reply_text = await _answer_and_log(user_text, chatbot_id, "Instagram")
                        send_instagram_message(
                            sender_id, reply_text, instagram_business_id, instagram_access_token
                        )

        # 其他 object 類型（例如未來的 whatsapp_business_account）先略過，不報錯。

        # Meta 要求 Webhook 在合理時間內回 200，否則會重試；即使沒有可處理的事件也要回 200。
        return {"status": "ok"}

    return router
