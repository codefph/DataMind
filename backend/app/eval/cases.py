CASES = [
    {
        "id": "region_gmv",
        "question": "各区域成交额是多少",
        "expect_columns": ["region", "gmv"],
    },
    {
        "id": "daily_gmv_trend",
        "question": "每日成交额趋势",
        "expect_columns": ["order_date", "gmv"],
    },
    {
        "id": "channel_orders",
        "question": "各渠道订单量排名",
        "expect_columns": ["channel", "order_count"],
    },
]

