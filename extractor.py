#!/usr/bin/env python3
"""网页正文提取 — trafilatura 通用抓取 + 自动称入库

设计：不掉落细节 = doc 级原文；自动化 = 标题-来源-日期 从页面抽，不用手填
"""

import sys
import os
import re
from datetime import datetime
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import insert_notice, get_db
from tagger import tag_and_merge


def extract_from_url(url: str) -> dict | None:
    """
    从 URL 抓取正文。
    返回 {"title": ..., "content": ..., "date": ..., "site": ...} 或 None。
    """
    try:
        import trafilatura
    except ImportError:
        return None

    # 下载（带 UA，避免被拒）
    downloaded = trafilatura.fetch_url(url)

    if not downloaded:
        return None

    # 提取正文 + 元数据
    result = trafilatura.bare_extraction(
        downloaded,
        include_formatting=False,
        include_links=False,
        include_images=False,
        include_tables=False,
    )

    if not result:
        return None

    text = result.text or ""
    if not text or len(text) < 50:
        return None

    # 取标题
    title = (
        result.title or
        _extract_title_from_html(downloaded) or
        _url_to_title(url)
    )

    # 取日期
    date = result.date or _guess_date_from_url(url)

    # 取站点
    domain = urlparse(url).netloc.replace("www.", "")

    return {
        "title": title.strip(),
        "content": text.strip(),
        "date": date,
        "site": domain,
        "url": url,
    }


def ingest_url(url: str) -> bool:
    """
    抓取 URL 正文 → 自动打标签 → 写入数据库。
    返回 True=入库成功 或 已存在，False=失败。
    """
    doc = extract_from_url(url)
    if not doc:
        return False

    # 转为 notice 格式
    notice = {
        "source": "web",
        "title": doc["title"],
        "notice_type": "网页",
        "biz_type": "通用",
        "region": "",
        "publisher": "",
        "budget": "",
        "url": doc["url"],
        "content": doc["content"][:10000],  # 截断保护
        "pub_date": doc["date"],
        "priority": "",   # 留给 tagger 自动填
        "stage": "",
        "can_bid": 0,
        "score": 0.0,
    }

    return insert_notice(notice, auto_tag=True)


# ── 内部辅助 ──

def _extract_title_from_html(html: str) -> str:
    """从 HTML 取 <title>"""
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if m:
        title = re.sub(r"<[^>]+>", "", m.group(1))
        title = title.replace("\n", " ").strip()
        if len(title) > 10:
            return title
    return ""


def _url_to_title(url: str) -> str:
    """从 URL 路径猜标题"""
    path = urlparse(url).path
    parts = [p for p in path.split("/") if p and not p.isdigit()]
    if parts:
        last = parts[-1]
        # 去扩展名
        last = re.sub(r"\.[a-z]{2,6}$", "", last, flags=re.IGNORECASE)
        # 分隔符转空格
        last = re.sub(r"[-_]+", " ", last)
        return last
    return url


def _guess_date_from_url(url: str) -> str:
    """从 URL 路径里猜日期"""
    m = re.search(r"/(20\d{2})[/-](\d{2})[/-](\d{2})", url)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return datetime.now().strftime("%Y-%m-%d")
