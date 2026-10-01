"""
LINE Messaging API Webhook。

LINE 僅作為 CRM 的另一個聊天入口。
實際問題處理由 main.py 的 _handle_chat() 負責，
避免重複實作訂單查詢、RAG、LLM 等邏輯。
"""

import base64
import hashlib
import hmac
import json
import os
import urllib.error
import urllib.request
from typing import Awaitable, Callable

from fastapi import APIRouter, HTTPException, Request

from app.schemas import ChatResponse
from app.accounts_store import get_chatbot
from app.chat_log import log_chat


LINE_REPLY_API = "https://api.line.me/v2/bot/message/reply"


def create_line_router(
    chat_handler: Callable[[str, list, str, str | None], Awaitable[ChatResponse]],
) -> APIRouter:
    router = APIRouter()

    channel_secret = os.getenv("LINE_CHANNEL_SECRET", "")
    channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

    def verify_signature(body: bytes, signature: str, secret: str) -> bool:
        """
        驗證 LINE Webhook 的 X-Line-Signature。
        """
        if not secret or not signature:
            return False

        digest = hmac.new(
            secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).digest()

        expected = base64.b64encode(digest).decode("utf-8")
        return hmac.compare_digest(expected, signature)

    def format_chat_response(response: ChatResponse) -> str:
        """
        將 CRM 原本的 ChatResponse 轉換成 LINE 可顯示的純文字。
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

    def reply_line(reply_token: str, message: str, access_token: str):
        """
        使用 LINE Reply API 回覆使用者。
        不需額外安裝 requests/httpx。
        """

        payload = {
            "replyToken": reply_token,
            "messages": [
                {
                    "type": "text",
                    "text": message[:5000],
                }
            ],
        }

        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        req = urllib.request.Request(
            LINE_REPLY_API,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                print(f"[LINE Reply Success] HTTP {response.status}")
                

        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            print(f"[LINE Reply API Error] HTTP {e.code}: {detail}")

        except Exception as e:
            print(f"[LINE Reply Error] {e}")

    @router.post("/line/webhook")
    async def line_webhook(request: Request):
        """
        接收 LINE Messaging API Webhook。
        """

        if not channel_secret:
            raise HTTPException(
                status_code=500,
                detail="LINE_CHANNEL_SECRET 尚未設定",
            )

        if not channel_access_token:
            raise HTTPException(
                status_code=500,
                detail="LINE_CHANNEL_ACCESS_TOKEN 尚未設定",
            )

        body = await request.body()

        signature = request.headers.get("X-Line-Signature", "")

        if not verify_signature(body, signature, channel_secret):
            raise HTTPException(
                status_code=400,
                detail="Invalid LINE signature",
            )

        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Invalid JSON",
            )

        events = payload.get("events", [])

        for event in events:

            # 目前只處理「文字訊息」
            if event.get("type") != "message":
                continue

            message = event.get("message", {})

            if message.get("type") != "text":
                continue

            reply_token = event.get("replyToken")

            if not reply_token:
                continue

            user_text = message.get("text", "").strip()

            if not user_text:
                continue

            try:
                # 第一版 LINE 暫時不帶入歷史對話作為上下文，
                # 但每次問答仍會寫入既有 chat_log。
                # provider 使用目前 CRM 預設的 Gemini。
                crm_response = await chat_handler(
                    user_text,
                    [],
                    "google",
                )

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
                        client_ip="LINE",
                    )
                except Exception as e:
                    # 對話紀錄失敗不能影響 LINE 回覆
                    print(f"[LINE Chat Log Error] {e}")

            except Exception as e:
                print(f"[LINE Chat Error] {e}")

                reply_text = (
                    "系統暫時發生錯誤，"
                    "請稍後再試或聯繫真人客服（0800-123-456）。"
                )

            reply_line(reply_token, reply_text, channel_access_token)

        # LINE Webhook 驗證時也可能送 events=[]，
        # 因此仍需正常回傳 200。
        return {"status": "ok"}

    @router.post("/line/webhook/{chatbot_id}")
    async def line_webhook_by_chatbot(chatbot_id: str, request: Request):
        """
        依 chatbot_id 處理對應 LINE Bot 的 Webhook。
        LINE Channel Secret / Access Token 直接從 chatbots 取得。
        """
        chatbot = get_chatbot(chatbot_id)

        if not chatbot:
            raise HTTPException(
                status_code=404,
                detail="Chatbot not found",
            )

        line_channel_secret = chatbot.get("line_channel_secret")
        line_channel_access_token = chatbot.get("line_channel_access_token")

        if not line_channel_secret:
            raise HTTPException(
                status_code=500,
                detail="LINE channel secret is not configured",
            )

        if not line_channel_access_token:
            raise HTTPException(
                status_code=500,
                detail="LINE channel access token is not configured",
            )

        body = await request.body()
        signature = request.headers.get("X-Line-Signature", "")

        if not verify_signature(
            body,
            signature,
            line_channel_secret,
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid LINE signature",
            )

        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Invalid JSON",
            )

        events = payload.get("events", [])

        for event in events:
            if event.get("type") != "message":
                continue

            message = event.get("message", {})

            if message.get("type") != "text":
                continue

            reply_token = event.get("replyToken")

            if not reply_token:
                continue

            user_text = message.get("text", "").strip()

            if not user_text:
                continue

            try:
                crm_response = await chat_handler(
                    user_text,
                    [],
                    "google",
                    chatbot_id,
                )

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
                        client_ip="LINE",
                        chatbot_id=chatbot_id,
                    )
                except Exception as e:
                    print(f"[LINE Chat Log Error] {e}")

            except Exception as e:
                print(f"[LINE Chat Error] {e}")

                reply_text = (
                    "系統目前發生錯誤，"
                    "請稍後再試或聯繫真人客服（0800-123-456）。"
                )

            reply_line(
                reply_token,
                reply_text,
                line_channel_access_token,
            )

        return {"status": "ok"}

    return router
