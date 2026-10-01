# Codex 專案指令

處理此專案前，先讀取並遵循下列共用文件：

1. `.agent/instructions/project-rules.md`
2. 任務涉及 CRM 前後端、RAG、LLM provider、訂單或產品文案時，讀取 `.agent/skills/crm-development/SKILL.md`
3. 任務涉及 React 前端開發、審查、重構或效能優化時，載入全域 `vercel-react-best-practices` Skill；目前專案使用 React 18，只套用 React 18 相容規則，排除 React 19、React Compiler、Server Components 與 Next.js 專屬規則。
4. 任務涉及前端樣式時，必須遵循 `.agent/instructions/project-rules.md` 的「前端 Tailwind CSS v4 架構」。

共用文件是跨 Agent 的唯一規格來源。若本檔與共用文件牴觸，以共用文件為準；Codex 平台本身的安全與權限限制除外。
