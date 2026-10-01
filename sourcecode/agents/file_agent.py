import os
# 匯入你在 agent.py 中寫好的生成函式
from get_des_agent import generate_product_description 

def save_to_text_file(product_name: str, content: str, folder_name: str = "data"):
    # 將生成的內容儲存到指定的資料夾中
    
    # 檢查並自動建立 data 資料夾
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        print(f"已建立資料夾：{folder_name}/")
        
    # 清理檔名中的特殊字元，避免存檔錯誤 (替換空格與斜線)
    safe_filename = product_name.replace(" ", "_").replace("/", "_")
    file_path = os.path.join(folder_name, f"{safe_filename}.txt")
    
    try:
        # 使用 utf-8 編碼寫入檔案
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path
    except Exception as e:
        return f"寫入檔案時發生錯誤: {e}"

if __name__ == "__main__":
    print("=== 商品文案自動生成與儲存 Agent ===")
    user_input = input("請輸入商品名稱：")
    
    if user_input.strip():
        print(f"\n[1/2] 正在呼叫 Gemini 生成「{user_input}」的描述...")
        # 呼叫 agent.py 的功能
        description = generate_product_description(user_input)
        
        # 簡單檢查是否生成失敗 (依照 agent.py 的錯誤提示)
        if description.startswith("發生錯誤"):
            print(description)
        else:
            user_confirm = input("確認生成文字存至文字檔? [y/n]")
            if (user_confirm.lower == 'y'):
                print(f"[2/2] 正在將結果儲存至文字檔...")
                saved_path = save_to_text_file(user_input, description)
                
                if "發生錯誤" not in saved_path:
                    print(f"\n✅ 任務完成！檔案已成功儲存於：{saved_path}")
                else:
                    print(f"\n❌ {saved_path}")
    else:
        print("未輸入商品名稱，已退出程式。")