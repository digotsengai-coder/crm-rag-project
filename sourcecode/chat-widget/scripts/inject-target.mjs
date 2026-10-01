import { access, copyFile, mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadEnv } from "vite";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const projectDirectory = path.resolve(scriptDirectory, "..");
const env = loadEnv("development", projectDirectory, "");
const targetDirectory = path.resolve(
  projectDirectory,
  env.CHAT_WIDGET_INJECT_TARGET_DIR || "../corp-frontend",
);
const bundlePath = path.join(projectDirectory, "dist", "chat-widget.js");
const targetAssetDirectory = path.join(targetDirectory, "public", "src");
const targetAssetPath = path.join(targetAssetDirectory, "chat-widget.js");
const targetIndexPath = path.join(targetDirectory, "index.html");
const widgetScript =
  '    <script src="__CHAT_WIDGET_URL__" data-client-id="__CHAT_WIDGET_CLIENT_ID__" defer></script>';

await access(targetIndexPath).catch(() => {
  throw new Error(`找不到注入目標：${targetIndexPath}`);
});
await access(bundlePath).catch(() => {
  throw new Error(
    `找不到 Widget 建置檔案，請先執行 npm run build：${bundlePath}`,
  );
});

await mkdir(targetAssetDirectory, { recursive: true });
await copyFile(bundlePath, targetAssetPath);
console.info(`Widget 建置檔案已複製：${targetAssetPath}`);

const html = await readFile(targetIndexPath, "utf8");

if (html.includes("__CHAT_WIDGET_URL__") || html.includes("data-client-id=")) {
  console.info(`Widget 注入標籤已存在：${targetIndexPath}`);
  process.exit(0);
}

if (!html.includes("</body>")) {
  throw new Error(`注入目標缺少 </body>：${targetIndexPath}`);
}

const updatedHtml = html.replace("</body>", `${widgetScript}\n  </body>`);
await writeFile(targetIndexPath, updatedHtml, "utf8");
console.info(`Widget 已注入：${targetIndexPath}`);
