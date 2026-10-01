# CRM Chat Widget

獨立 React 18 聊天元件，建置後只需部署 `dist/chat-widget.js`。

## 樣式架構

- 使用 Tailwind CSS v4 與 `@tailwindcss/vite`，入口為 `src/widget.css`。
- 不載入 Preflight；`src/entry.tsx` 以 `widget.css?inline` 將完整樣式注入 Shadow DOM。
- 元件 utility mapping 集中於 `src/widgetStyles.ts`，透過 `tw()` 組合完整靜態 class 字串，不動態拼接 utility 名稱。
- 顏色、字級、圓角、陰影與動畫集中於 `widget.css` 的 `@theme`；品牌色、表面色、文字色與 panel 圓角仍由 `config.ts` 提供 runtime CSS variables。
- textarea 自動高度及 API runtime theme 可使用 inline style，其餘靜態樣式使用 utility。
- 單邊分隔線只使用 `border-t` 或 `border-b`，不可再搭配 `border-solid`，避免 Shadow DOM 內其他邊產生預設框線。
- `prettier-plugin-tailwindcss` 會依官方順序整理 `className` 與 `tw()` 內容。

## 建置

```bash
npm install
cp .env.example .env
npm run preview
```

`npm run preview` 會依序完成建置、注入目標專案，再於 `http://localhost:5175` 啟動預覽服務。開啟此網址即可直接查看 Chat Widget 介面；`http://localhost:5175/chat-widget.js` 則保留給其他網站嵌入。

## 開發環境注入

`.env` 的 `CHAT_WIDGET_INJECT_TARGET_DIR` 用來指定開發階段的目標前端專案，預設為同層的 `../corp-frontend`：

```env
CHAT_WIDGET_INJECT_TARGET_DIR=../corp-frontend
```

`npm run preview` 會自動將建置結果複製至目標專案的 `public/src/chat-widget.js`，並確認 `index.html` 已有注入標籤。Corp Frontend 開發環境會透過 `/src/chat-widget.js` 載入此檔案。

若只需複製與注入而不啟動預覽，可執行：

```bash
npm run inject:target
```

修改樣式後應依序執行 `npm run format`、`npm run format:check`、`npm run build` 與 `npm run inject:target`，並在目標頁面的 Shadow DOM 中檢查一般、hover、focus、disabled 與 480px 響應式狀態。

此設定只供本機開發工具讀取，不會打包至 `chat-widget.js`。正式提供客戶使用時，不需要設定目標目錄，直接提供下方嵌入程式碼即可。

## 嵌入

```html
<script
  src="https://<widget-service>/chat-widget.js"
  data-client-id="<assigned-client-id>"
  defer
></script>
```

`data-client-id` 是公開的企業客戶識別碼，不是登入或授權憑證。此值現在對應後端 `chatbots` 表的
chatbot_id（透過 `/api/admin/chatbots` 建立/查詢），沒有對應 chatbot 時聊天功能仍可用，但 `@mcp` 查詢／RAG
檢索會查不到任何資料。正式資料隔離仍須由後端驗證客戶狀態並限制資料範圍。
