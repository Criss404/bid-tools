#!/usr/bin/env python3
"""GgzyCrawler — 全国公共资源交易平台爬虫

两层结构:
    ① a 页 = 项目总览（首页链接指向的），含标题/地区/项目编号/各阶段 b 链接
    ② b 页 = 具体阶段详情（招标公告/开标记录/中标公示），含正文内容

策略: 取首页 a 链接 → 解析 a 页(取元数据+b链接) → 抓第一个 b 页(取正文)
"""

import re
import time
import random
from urllib.parse import urljoin

from crawlers.base import BaseCrawler

GGZY_HOME = "https://www.ggzy.gov.cn/"
GGZY_BASE = "https://www.ggzy.gov.cn"

# URL 里的 infoType → notice_type
INFO_TYPE_MAP = {
    "0101": "招标公告",
    "0102": "开标记录",
    "0104": "中标公示",
    "0105": "更正公告",
    "0201": "招标公告",
    "0202": "中标公示",
    "2201": "交易公告",
    "9001": "交易公告",
}


class GgzyCrawler(BaseCrawler):
    """全国公共资源交易平台爬虫"""

    source = "ggzy"
    base_url = GGZY_HOME

    def _fetch_urls(self) -> list[str]:
        """从首页提取 a 类型详情链接"""
        try:
            resp = self.session.get(GGZY_HOME, timeout=20)
        except Exception:
            return []

        # 从首页 HTML 提取所有 /information/deal/html/a/ 链接
        urls = re.findall(
            r'/information/deal/html/a/\d+/\d+/\d+/[a-f0-9]+\.html',
            resp.text
        )
        # 去重 + 补全
        seen = set()
        full_urls = []
        for path in urls:
            if path not in seen:
                seen.add(path)
                full_urls.append(GGZY_BASE + path)
        return full_urls

    def _parse_detail(self, html: str, url: str) -> dict | None:
        """解析 a 页 → 取元数据 → 抓 b 页正文"""
        # ── 基本信息 ──
        title = _extract_title(html) or _url_title(url)
        if not title:
            return None

        region = _extract_region(html) or ""
        project_no = _extract_project_no(html) or ""

        # infoType 从 URL 取
        info_type = _info_type_from_url(url)
        notice_type = INFO_TYPE_MAP.get(info_type, "交易公告")

        # 面包屑 → biz_type
        biz_type = _extract_biz_type(html) or ""

        # 日期 → 优先URL，否则页面
        pub_date = _date_from_url(url) or _extract_pub_date(html) or ""

        # ── 提取 b 链接（onclick showDetail）──
        b_urls = re.findall(
            r"showDetail\([^,]+,\s*'(\d+)',\s*'([^']+)'\)",
            html
        )

        # 优先取与 a 页同 infoType 的 b 页
        b_url = None
        for itype, path in b_urls:
            url_b = GGZY_BASE + path
            if itype == info_type:
                b_url = url_b
                break
        if not b_url and b_urls:
            b_url = GGZY_BASE + b_urls[0][1]

        # ── 正文内容 ──
        content = ""
        if b_url:
            content = _fetch_content(self.session, b_url)
            time.sleep(self.request_interval / 2 + random.random() * 0.5)

        # ── 预算提取 ──
        budget = _extract_budget(content) or ""

        return {
            "source": self.source,
            "title": title.strip(),
            "notice_type": notice_type,
            "biz_type": biz_type,
            "region": region.replace(" ", ""),
            "publisher": "",
            "budget": budget,
            "url": url,
            "content": content.strip()[:8000],
            "pub_date": pub_date,
            "raw_id": project_no,
        }


# ── 辅助函数 ──

def _extract_title(html: str) -> str:
    """提取标题：h4_o 优先，其次 title"""
    m = re.search(r'<h4 class="h4_o"[^>]*>(.*?)</h4>', html, re.DOTALL)
    if m:
        title = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        if len(title) > 4:
            return title
    m = re.search(r'<title>(.*?)(?:_交易公开|_国家公共资源)', html)
    if m:
        return m.group(1).strip()
    return ""


def _url_title(url: str) -> str:
    """从URL hash猜一个备用标题"""
    parts = url.rstrip(".html").split("/")
    return parts[-1][:40] if parts else ""


def _extract_region(html: str) -> str:
    """提取区域：信息来源：XX"""
    from tagger import _normalize_region
    raw = _extract_raw_region(html)
    return _normalize_region(raw)


def _extract_raw_region(html: str) -> str:
    """从页面提取原始区域文本"""
    # 优先取 label#platformName（更精确）
    m = re.search(r'id="platformName"[^>]*>\s*([^\s<]+)', html)
    if m:
        region = m.group(1).strip()
        if len(region) <= 20:
            return region
        if re.match(r'([一-鿿]{2})(?:省|市|自治区)', region):
            return re.match(r'([一-鿿]{2})', region).group(1)
        return region[:4] if len(region) > 2 else region
    m = re.search(r'信息来源[：:].*?</span>', html, re.DOTALL)
    if m:
        text = re.sub(r'<[^>]+>', '', m.group(0))
        text = re.sub(r'信息来源[：:]', '', text).strip()
        if len(text) <= 20:
            return text
    return ""


def _extract_project_no(html: str) -> str:
    """提取项目编号"""
    m = re.search(r'(?:招标项目|项目)编号[：:]\s*([^\s<,，]+)', html)
    if m:
        return m.group(1).strip()
    return ""


def _info_type_from_url(url: str) -> str:
    """从URL路径提取 infoType"""
    m = re.search(r'/html/[ab]/\d+/(\d+)/', url)
    return m.group(1) if m else ""


def _date_from_url(url: str) -> str:
    """从URL提取日期"""
    m = re.search(r'/html/[ab]/\d+/\d+/(\d{8})/', url)
    if m:
        d = m.group(1)
        return f"{d[:4]}-{d[4:6]}-{d[6:8]}"
    return ""


def _extract_pub_date(html: str) -> str:
    """从页面提取发布时间"""
    m = re.search(r'发布时间[：:]\s*(\d{4}-\d{2}-\d{2})', html)
    return m.group(1) if m else ""


def _extract_biz_type(html: str) -> str:
    """从面包屑或表头提取业务类型"""
    from html import unescape
    m = re.search(r'交易公开\s*>&nbsp;>\s*(\S+)', html)
    if m:
        return unescape(m.group(1).strip())
    return "工程建设"


def _extract_budget(content: str) -> str:
    """从正文提取预算/金额"""
    from html import unescape
    content = unescape(content)
    patterns = [
        r'(?:预算金额|合同估算价|建设资金|项目总投资|总投资|投资)[：:]\s*(\d+\.?\d*\s*[万亿]元)',
        r'(?:预算|招标控制价|控制价)[：:]\s*(\d+\.?\d*\s*[万亿]元)',
    ]
    for pat in patterns:
        m = re.search(pat, content)
        if m:
            val = m.group(1).strip()
            # 截断到常见分隔符
            val = re.split(r'[；;。\n]', val)[0].strip()
            return val[:50]
    return ""


def _fetch_content(session, b_url: str) -> str:
    """请求 b 页并取纯文本"""
    try:
        resp = session.get(b_url, timeout=20)
        if resp.status_code != 200:
            return ""
        resp.encoding = resp.apparent_encoding or "utf-8"
        html = resp.text
    except Exception:
        return ""

    # 去 script/style → 纯文本
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text
