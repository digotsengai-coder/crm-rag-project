---
name: crm-development
description: 維護 CRM Squad 的 FastAPI、React 聊天介面、RAG、LLM provider、訂單查詢與產品文案流程時使用。
---

# CRM Development

先讀取 `../../instructions/project-rules.md`，再依任務檢查 `sourcecode/` 中實際實作。文件與程式不一致時，以目前程式行為為調查依據，並將文件同步列入修改範圍。

## 工作流程

1. 從實際呼叫鏈定位影響範圍：React 呼叫端、FastAPI route、Pydantic schema、agent/provider、資料來源或 RAG engine。
2. 保持 `/api/chat` 的單一聊天入口與 `type` 判別契約，除非需求明確要求介面變更。
3. 修改 API、資料欄位或分流行為前，讀取 [介面契約](references/contracts.md)。
4. 修改完成後，使用 [驗收案例](references/acceptance-cases.md) 選擇與變更相關的情境驗證。

## 不變條件

- `sourcecode/backend/app/schemas.py` 是聊天 API 型別來源；前端依回應 `type` 決定顯示方式。
- 訂單訊息由後端規則分流；一般產品與政策問題才進入 RAG 與 LLM。
- 線上 provider 未設定或呼叫失敗時，應回傳可理解的結果，不能讓整個聊天服務中斷。
- RAG 的兩種 engine 共用文件切分結果，但各自保有索引目錄與距離門檻。
- `.env`、`llm_keys.json`、SQLite 資料庫、模型快取與向量索引皆視為本機執行資料，不提交至 Git。

## 平台相容性

- 使用 Markdown 描述決策與流程，以程式型別、OpenAPI 輸出和可執行檢查作為契約證據。
- 平台專屬工具無法使用時，改用等價的檔案搜尋、命令或人工檢查，並如實回報未能完成的驗證。
- 不在共用 Skill 中依賴特定模型名稱、聊天室記憶或單一供應商的私有工具語法。
