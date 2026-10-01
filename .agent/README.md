# 跨 Agent 共用規格

此目錄存放 ChatGPT／Codex、Claude 與 Gemini 共用的專案規格。三家 Agent 的根目錄指令檔只作為入口，業務規則與驗收條件集中維護於此。

## 維護方式

- 專案共同規則放在 `instructions/project-rules.md`。
- 可重複使用的任務流程放在 `skills/<skill-name>/SKILL.md`。
- 詳細契約與情境放在 Skill 的 `references/`，由 `SKILL.md` 說明何時讀取。
- 新增或修改行為時，同步更新程式、契約及相關驗收案例。
- 平台專屬指令只寫在根目錄對應入口，不複製共用業務規則。

## Agent 入口

| Agent | 入口檔案 |
|---|---|
| ChatGPT／Codex | `AGENTS.md` |
| Claude Code | `CLAUDE.md` |
| Gemini CLI | `GEMINI.md` |
