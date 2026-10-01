"""
公司最新活動內容，給 MCP tool `get_latest_promotions` 回傳。

要更換活動只需要改下面的 PROMOTIONS（backend 聊天端會在每次 @mcp 對話時重新讀取 tools 與回傳內容，
不需要動 backend）。內容是給顧客看的公開資訊，不要放任何內部或個資。
"""

PROMOTIONS: list[dict] = [
    {
        "title": "全館 9 折",
        "description": "目前全館商品享 9 折優惠。",
    },
]
