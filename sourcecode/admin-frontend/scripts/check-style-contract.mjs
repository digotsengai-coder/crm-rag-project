import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = fileURLToPath(new URL("..", import.meta.url));
const sourceRoot = join(projectRoot, "src");
const stylesSource = readFileSync(join(sourceRoot, "styles.css"), "utf8");
const themeSource = readFileSync(
  join(sourceRoot, "theme", "adminTheme.ts"),
  "utf8",
);
const errors = [];

const sharedTokens = [
  ["primary", "--color-admin-primary"],
  ["text", "--color-admin-text"],
  ["heading", "--color-admin-heading"],
  ["textSecondary", "--color-admin-text-secondary"],
  ["muted", "--color-admin-muted"],
  ["canvas", "--color-admin-canvas"],
  ["surface", "--color-admin-surface"],
  ["surfaceSubtle", "--color-admin-surface-subtle"],
  ["border", "--color-admin-border"],
];

for (const [themeKey, cssVariable] of sharedTokens) {
  const themeMatch = themeSource.match(
    new RegExp(`\\b${themeKey}:\\s*"(#[0-9a-fA-F]{6})"`),
  );
  const cssMatch = stylesSource.match(
    new RegExp(`${cssVariable}:\\s*(#[0-9a-fA-F]{6});`),
  );

  if (!themeMatch || !cssMatch) {
    errors.push(`找不到共用 token：${themeKey} / ${cssVariable}`);
  } else if (themeMatch[1].toLowerCase() !== cssMatch[1].toLowerCase()) {
    errors.push(
      `${themeKey} 與 ${cssVariable} 不一致：${themeMatch[1]} / ${cssMatch[1]}`,
    );
  }
}

function collectFiles(directory) {
  return readdirSync(directory).flatMap((entry) => {
    const fullPath = join(directory, entry);
    return statSync(fullPath).isDirectory() ? collectFiles(fullPath) : fullPath;
  });
}

const allowedAntClasses = new Set([
  "ant-design",
  "ant-upload-drag-icon",
  "ant-upload-hint",
  "ant-upload-text",
]);

for (const filePath of collectFiles(sourceRoot).filter((file) =>
  file.endsWith(".tsx"),
)) {
  const source = readFileSync(filePath, "utf8");
  const displayPath = relative(projectRoot, filePath);

  if (displayPath !== "src/main.tsx" && source.includes("ConfigProvider")) {
    errors.push(`${displayPath} 不得建立巢狀 ConfigProvider`);
  }

  if (/theme\s*=\s*\{\{/.test(source)) {
    errors.push(`${displayPath} 不得使用頁面層 theme={{ ... }}`);
  }

  const rawColors = source.match(/#[0-9a-fA-F]{3,8}\b/g) ?? [];
  if (rawColors.length > 0) {
    errors.push(
      `${displayPath} 含 raw 色彩：${[...new Set(rawColors)].join(", ")}`,
    );
  }

  const antClasses = source.match(/ant-[a-z0-9-]+/g) ?? [];
  const unsupportedClasses = antClasses.filter(
    (className) => !allowedAntClasses.has(className),
  );
  if (unsupportedClasses.length > 0) {
    errors.push(
      `${displayPath} 含未核准 Ant class：${[...new Set(unsupportedClasses)].join(", ")}`,
    );
  }
}

if (errors.length > 0) {
  console.error("Admin 樣式契約檢查失敗：");
  errors.forEach((error) => console.error(`- ${error}`));
  process.exitCode = 1;
} else {
  console.log("Admin 樣式契約檢查通過");
}
