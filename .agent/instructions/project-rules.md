# CRM Squad 共用專案規則

## 專案邊界

- 可執行專案位於 `sourcecode/`；後端位於 `sourcecode/backend/` 與 `sourcecode/corp-backend/`，前端分別位於 `sourcecode/corp-frontend/`、`sourcecode/admin-frontend/` 與 `sourcecode/chat-widget/`。
- 修改前先讀取相關入口、型別、設定與呼叫端，維持既有資料流與專案慣例。
- 採最小可行修改，處理根因；不要順帶重構、重新命名或調整無關檔案。
- 保留團隊現有變更。發現不相關的未提交內容時，不覆蓋、不還原。

## 程式與文件

- 變數與函式名稱使用英文；註解使用繁體中文，說明設計原因或限制。
- Python 沿用現有 FastAPI、Pydantic 與模組分工；React 沿用現有函式元件與 hooks 寫法。
- API 欄位或回應型別變更時，同步檢查 Pydantic schema、route、前端呼叫端與文件。
- 不在程式碼、文件、測試輸出或提交內容中放入 API key、token、`.env` 或真實顧客資料。

## 前端 Tailwind CSS v4 架構

- `corp-frontend`、`admin-frontend`、`chat-widget` 是三個獨立 package，各自維護 `package.json`、lockfile、Vite 與 Prettier 設定；不得建立共用 root package、workspace 或跨 App 樣式 import。
- 三個 App 統一使用 `tailwindcss@4` 與 `@tailwindcss/vite@4`。Tailwind 入口分別為 `corp-frontend/src/index.css`、`admin-frontend/src/styles.css`、`chat-widget/src/widget.css`。
- 不載入 Preflight。入口 CSS 只保留 Tailwind theme／utilities imports、`@theme` token、字型與共用 keyframes；不得新增專案自訂 selector class 或將元件樣式搬回傳統 CSS。
- 元件樣式使用完整、可靜態掃描的 utility 字串。需要組合 class 時使用各 App 的 `tw()` helper；不得動態拼接 utility 名稱。
- 可重複的顏色、字級、圓角、陰影與動畫必須定義為 `@theme` token。`clamp()`、複合 grid、動態 viewport 計算與一次性圖片漸層才可使用 arbitrary value。
- Tailwind spacing 基準為 4px：9px、10px、13px、21px 的間距或定位分別使用 `2.25`、`2.5`、`3.25`、`5.25`。字級不得使用 spacing utility；13px、21px 等非預設字級使用語意化 `--text-*` token。9px、10px、13px 圓角使用語意化 `--radius-*` token。
- 靜態 inline style 必須改為 utility；只有 API runtime theme、自動高度、動態圖片 URL 等執行期值可以保留 inline style。
- Admin 保留 Ant Design。優先使用 `className`、`rootClassName`、`classNames` 與 arbitrary descendant variants；只有已確認被 Ant 未分層樣式或同屬性 utility 覆蓋時，才對必要 utility 加 `!`。
- 使用單邊框 `border-t`、`border-r`、`border-b`、`border-l` 時，不得再搭配會設定四邊樣式的 `border-solid`，避免其他三邊產生瀏覽器預設寬度。
- Widget 的 `widget.css?inline` 必須持續注入 Shadow DOM，並保留 `config.ts` 的 runtime CSS variables；狀態 class 使用完整靜態 mapping。
- 各 App 的 `prettier.config.mjs` 必須設定 `tailwindFunctions: ["tw"]` 與正確的 `tailwindStylesheet`；`prettier-plugin-tailwindcss` 必須是 plugins 最後一項，由它統一 className 排序。
- 前端樣式修改至少執行該 App 的 `npm run format`、`npm run format:check`、`npm run build`。Widget 變更另執行 `npm run inject:target`，並以瀏覽器 computed style 檢查受影響狀態與斷點。

## 驗證與交付

- 依變更範圍執行必要的後端檢查或前端 `npm run build`；不要以未執行的測試宣稱通過。
- 完成後回報修改檔案、關鍵行號、驗證結果與已知限制。
- Commit message 使用 Conventional Commits，描述使用繁體中文，例如 `docs: 新增跨 Agent 共用規格`。
