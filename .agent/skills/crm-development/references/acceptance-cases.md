# CRM 驗收案例

依變更範圍選擇案例；涉及契約或分流時至少涵蓋正常、邊界與失敗情境。

## 聊天分流

| 輸入 | 預期行為 |
|---|---|
| `無線滑鼠支援多少 DPI？` | 回傳 `type: product`，包含文字回答與可用的來源資訊 |
| `查詢訂單 A12345`（沒有 `@mcp`） | 走 RAG + LLM，不會查訂單；回傳 `type: product` 或 `text` |
| `@mcp 幫我查 SKU-9 的庫存`（公司有設定 `mcp_url`、provider 為 Gemini 或 local） | LLM 透過公司 MCP server 的 tools 回答，回傳 `type: text`；呼叫過的 tool 記錄在 `mcp_tool_log` |
| `@mcp`（後面沒有問題） | 回傳 `type: text`，提示要在 `@MCP`（該公司設定的名稱）後面輸入問題 |
| 公司把「MCP 機器人名稱」設成 `阿柴`，訊息為 `@阿柴 查庫存` | 走 MCP 路徑；`@mcp 查庫存` 不再觸發，改走 RAG + LLM |
| `@mcp ...` 但公司沒有 `mcp_url`，或 `X-Client-ID` 對不到公司 | 回傳 `type: text`，說明尚未開啟 MCP 功能 |
| `@mcp ...` 但 provider 不支援 tool calling（例如 `openai`） | 回傳 `type: text`，提示改用 Gemini 或本地模型 |
| `@mcp 查訂單 ORD-1`（缺少 tool 的必填參數，例如電話） | 不會用空值呼叫 MCP server；模型改為向顧客詢問缺少的資訊 |
| `@mcp ...` 但公司的 MCP server 連不上或金鑰無效 | 回傳 `type: text` 的友善訊息，不退回 RAG，不回 HTTP 5xx |
| `請幫我 @mcp 查`（`@mcp` 不在開頭） | 一般問題，走 RAG + LLM |
| 公司的 MCP server 新增 tool | backend 不需修改；下一次 `@mcp` 對話 LLM 即可使用該 tool |

## 請求驗證

- `/api/chat`、`/api/providers` 與 `/api/widget/config` 缺少或傳入超過 128 字元的 `X-Client-ID` 時應回傳 HTTP 422。
- 空白或超過 500 字元的 `message` 應受到 API schema 或既有空白處理限制。
- 無效的 `provider`、`history.role` 或超過上限的歷史紀錄應回傳驗證錯誤。
- 同一來源超過既有速率限制時應回傳 HTTP 429。

## Provider 與 RAG

- `GET /api/providers` 的設定狀態應與本機 key 設定一致，且不得洩漏 key。
- 未設定或呼叫失敗的線上 provider 應產生可理解的回應，聊天端點不能因供應商錯誤直接中斷。
- 產品與政策問題應使用共用文件切分結果；切換 RAG engine 後回應結構維持一致。

## 前端

- `product`、`order` 與 `text` 三種回應都能顯示正確元件（後端目前只會產生 `product` 與 `text`，`order` 為保留的相容型別）。
- 訂單卡片不加入送給 LLM 的文字歷史；產品與一般文字回覆可保留上下文。
- 後端錯誤時顯示可理解的錯誤狀態，送出流程不應永久卡住。
