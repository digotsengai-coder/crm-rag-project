import concurrent.futures
import json
import os
import urllib.parse
import urllib.request

JSON_PATH = r"C:\Source Code\crm_squard\sourcecode\data\tk3c_all_clean\products.json"
OUTPUT_DIR = r"C:\Source Code\crm_squard\sourcecode\data\product_image"


def download_image(item, output_dir):
    image_url = item.get("image_url")
    product_id = item.get("source_product_id", "")
    
    if not image_url:
        return False, "No URL"

    # 解析 URL 取得副檔名或檔名
    parsed = urllib.parse.urlparse(image_url)
    filename = os.path.basename(parsed.path)
    
    if not filename:
        filename = f"{product_id}.jpg"
    elif product_id and not filename.startswith(str(product_id)):
        ext = os.path.splitext(filename)[1] or ".jpg"
        filename = f"{product_id}_{filename}"

    save_path = os.path.join(output_dir, filename)

    # 若檔案已存在且不為 0 byte 則跳過
    if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
        return True, f"Skipped (already exists): {filename}"

    req = urllib.request.Request(
        image_url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response, open(save_path, "wb") as f:
            f.write(response.read())
        return True, f"Downloaded: {filename}"
    except Exception as e:
        return False, f"Failed ({image_url}): {e}"


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        products = json.load(f)

    print(f"共讀取到 {len(products)} 筆產品資料，開始下載圖片至 '{OUTPUT_DIR}'...")

    success_count = 0
    fail_count = 0

    # 使用 ThreadPoolExecutor 並列下載
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(download_image, item, OUTPUT_DIR) for item in products]
        for future in concurrent.futures.as_completed(futures):
            ok, msg = future.result()
            if ok:
                success_count += 1
            else:
                fail_count += 1
                print(msg)

    print(f"\n下載完成！成功: {success_count} 筆，失敗: {fail_count} 筆。")
    print(f"圖片儲存資料夾: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
