#!/usr/bin/env python3
"""bid_tool 全局配置"""

import os

# ── 路径 ──────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
USER_DIR    = os.path.join(os.path.expanduser("~"), ".bid_tool")
DB_PATH     = os.path.join(USER_DIR, "data", "bid.db")
KNOWLEDGE_DIR = os.path.join(USER_DIR, "knowledge")

# ── 数据源 ────────────────────────────
SEARCH_KEYWORDS = ["停车场", "智慧停车", "停车系统", "车位引导", "道闸", "充电桩+停车"]

# ── 爬虫 ──────────────────────────────
CRAWL_INTERVAL_SECONDS = 3        # 请求间隔
CRAWL_TIMES_PER_DAY    = 3        # 每日定时次数
CRAWL_TIMEOUT_MS       = 30000    # 单页超时

# ── AI API（DeepSeek，兼容 OpenAI SDK）─
# 注册获取 key: https://platform.deepseek.com/
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "your-api-key-here")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"  # V4 最新版

# ── 商机标签 ──────────────────────────
PRIORITY_RULES = {
    "A级": {"notice_type": ["招标公告", "竞争性磋商", "采购公告"], "can_bid": True},
    "B级": {"notice_type": ["中标公示", "开标记录", "交易公告"]},
    "C级": {"notice_type": ["更正公告", "废标公告"]},
}
