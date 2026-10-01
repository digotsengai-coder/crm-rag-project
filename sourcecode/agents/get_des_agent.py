import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

# 載入 .env 檔案中的變數 (GEMINI_API_KEY)
load_dotenv()

def generate_product_description(product_name: str) -> str:
    # 初始化 Gemini 客戶端，會自動讀取環境變數中的 GEMINI_API_KEY
    client = genai.Client()
    
    # 建構 Prompt，明確定義角色、字數、語言與輸出結構
    prompt = f"""
    你是一位資深的產品行銷專家。
    請為商品「{product_name}」撰寫一篇約 800 字的繁體中文產品描述文案。
    
    內容必須結構清楚，且強制包含以下三個段落：
    1. 產品特點 (Product Features)：生動描述產品的核心功能與解決的痛點。
    2. 技術規格 (Technical Specifications)：列出該類型產品合理且詳細的硬體或軟體規格參數。
    3. 競爭優勢 (Competitive Advantages)：說明與市面上其他競品相比，這款產品的獨特價值與購買理由。
    
    請保持專業且具說服力的行銷語氣，排版易於閱讀。
    """
    
    try:
        # 呼叫 Gemini Flash 模型生成內容
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7, # 設定為 0.7 讓生成的文案更具創造力與吸引力
            )
        )
        return response.text
    except Exception as e:
        return f"發生錯誤，無法生成文案：{e}"

if __name__ == "__main__":
    print("=== AI 產品文案生成代理 (Agent) ===")
    user_input = input("請輸入商品名稱 (例如：高階商務筆記型電腦)：")
    
    if user_input.strip():
        print(f"\n正在使用 Gemini Flash 為「{user_input}」生成描述，請稍候...\n")
        print("=" * 60)
        
        result = generate_product_description(user_input)
        print(result)
        
        print("=" * 60)
    else:
        print("未輸入商品名稱，已退出程式。")