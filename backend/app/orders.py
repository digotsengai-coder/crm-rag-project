"""
模擬訂單資料庫（對應提案 #2「顧客查詢訂單」的資料來源）。
之後要接真實系統，把 MOCK_ORDERS 換成呼叫真正的訂單資料庫 / ERP API 即可，
main.py 呼叫 get_order() 的介面不需要改。

status 對應前端時間軸的階段索引：
  0 = 已下單, 1 = 備貨出貨, 2 = 配送中, 3 = 已送達
"""

MOCK_ORDERS = {
    "A12345": {"status": 2, "eta": "8月28日", "items": "智慧掃地機器人 R5 Pro ×1"},
    "B98231": {"status": 0, "eta": "9月5日", "items": "智慧冷氣 A8（1.5噸）×1"},
    "C55210": {"status": 3, "eta": "已送達", "items": "智慧電視 V6 55吋 ×1"},
}


def get_order(code: str):
    return MOCK_ORDERS.get(code.upper())
