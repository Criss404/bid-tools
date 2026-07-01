#!/usr/bin/env python3
"""CebCrawler — 中国招标投标公共服务平台爬虫

数据源: bulletin.cebpubservice.com
方式: 纯 requests，无需 JS 渲染

列表页: /xxfbcmses/search/bulletin.html?dates=300&categoryId=88&page=1
    每页 20 条，纯 HTML table，翻页参数 page=N

详情页: ctbpsp.com SPA (JS 渲染，暂不抓正文)
    但 UUID 可构造链接，用户可在浏览器打开
"""

import re
import time
import random
from urllib.parse import urljoin
from html import unescape

from crawlers.base import BaseCrawler

CEB_LIST = "https://bulletin.cebpubservice.com/xxfbcmses/search/bulletin.html"
CEB_PARAMS = "?dates=300&categoryId=88&showStatus=1&page="


class CebCrawler(BaseCrawler):
    source = "cebpubservice"
    base_url = "https://bulletin.cebpubservice.com/"

    def __init__(self, keyword_filter: str = "", max_pages: int = 30,
                 list_pages: int = 5, **kwargs):
        """
        list_pages: 翻多少页列表（每页 20 条）
        """
        super().__init__(keyword_filter=keyword_filter, max_pages=max_pages, **kwargs)
        self.list_pages = list_pages

    def _fetch_urls(self) -> list[str]:
        """从列表页提取所有 UUID，构造 ctbpsp 链接"""
        all_ids = []

        for page in range(1, self.list_pages + 1):
            url = CEB_LIST + CEB_PARAMS + str(page)
            try:
                resp = self.session.get(url, timeout=20)
                if resp.status_code != 200:
                    self._log(f"  列表页 {page} HTTP {resp.status_code}，跳过后续")
                    break
                resp.encoding = resp.apparent_encoding or "utf-8"
                html = resp.text
            except Exception as e:
                self._log(f"  列表页 {page} 网络错误: {e}")
                break

            # 提取 urlOpen('uuid') 中的 UUID
            uuids = re.findall(r"urlOpen\('([a-f0-9]{32})'\)", html)
            if not uuids:
                self._log(f"  列表页 {page} 没有更多数据，停止翻页")
                break

            all_ids.extend(uuids)
            self._log(f"  列表页 {page}: {len(uuids)} 条 (累计 {len(all_ids)})")
            time.sleep(self.request_interval / 2 + random.random() * 0.5)

        # UUID → 可构造的 ctbpsp URL (浏览器可打开，但正文需 JS 渲染)
        return [
            f"https://ctbpsp.com/#/bulletinDetail?uuid={uid}&dataSource=0"
            for uid in all_ids
        ]

    def _parse_detail(self, html: str, url: str) -> dict | None:
        """解析列表页 HTML table 的每一行，提取公告字段"""
        # 这个 html 是整个列表页（包含 20 条公告的 table）
        # 但 base crawl() 是逐个 URL 调的 — 我们用 uuid url 当作标识
        # 真正的解析在 crawl() 里重写了
        return None

    def crawl(self) -> list[dict]:
        """重写：从列表页直接解析所有行，不走逐条请求模式"""
        results = []
        seen = set()
        count = 0

        for page in range(1, self.list_pages + 1):
            if count >= self.max_pages:
                break

            url = CEB_LIST + CEB_PARAMS + str(page)
            self._log(f"[{self.source}] 列表页 {page}...")

            try:
                resp = self.session.get(url, timeout=20)
                if resp.status_code != 200:
                    self._log(f"  HTTP {resp.status_code}")
                    break
                resp.encoding = resp.apparent_encoding or "utf-8"
                html = resp.text
            except Exception as e:
                self._log(f"  网络错误: {e}")
                break

            # 提取所有行
            rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.DOTALL)

            page_results = 0
            for row in rows:
                if count >= self.max_pages:
                    break

                # 提取 UUID — 只取 32 位 hex（过滤 http:// 这类）
                uuid_match = re.search(r"urlOpen\('([a-f0-9]{32})'\)", row)
                if not uuid_match:
                    continue
                uuid = uuid_match.group(1)

                # 取 <a> 标签的 title 属性（更完整）
                title_match = re.search(r'<a[^>]*title="([^"]+)"', row)
                if title_match:
                    title = unescape(title_match.group(1)).strip()
                else:
                    # 兜底：取 <a> 标签内的文本
                    a_match = re.search(r"<a[^>]*>(.*?)</a>", row, re.DOTALL)
                    if not a_match:
                        continue
                    title = unescape(re.sub(r"<[^>]+>", "", a_match.group(1))).strip()
                    title = re.sub(r"\s+", " ", title)  # 合并换行和空格

                # 跳过表头
                if "公告名称" in title or "所属行业" in title or len(title) < 6:
                    continue

                # 各列数据
                cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
                cells_text = []
                for c in cells:
                    t = unescape(re.sub(r"<[^>]+>", "", c))
                    t = re.sub(r"\s+", " ", t).strip()
                    cells_text.append(t)

                industry = cells_text[1] if len(cells_text) > 1 else ""
                region_raw = cells_text[2] if len(cells_text) > 2 else ""
                region = region_raw.replace("【", "").replace("】", "").strip()
                source_platform = cells_text[3] if len(cells_text) > 3 else ""
                pub_date = cells_text[4] if len(cells_text) > 4 else ""

                # 关键词过滤
                if self.keyword_filter and self.keyword_filter not in title:
                    continue

                # 去重
                if title in seen:
                    continue
                seen.add(title)

                count += 1
                detail_url = f"https://ctbpsp.com/#/bulletinDetail?uuid={uuid}&dataSource=0"

                results.append({
                    "source": self.source,
                    "title": title,
                    "notice_type": "招标公告",
                    "biz_type": industry,
                    "region": region,
                    "publisher": source_platform,
                    "budget": "",
                    "url": detail_url,
                    "content": "",
                    "pub_date": pub_date,
                    "raw_id": uuid,
                })

                page_results += 1
                self._log(f"  [{count}] {title[:55]}")

            self._log(f"  本页: {page_results} 条 (累计 {len(results)})")

            if page_results == 0:
                self._log(f"  无更多数据，停止翻页")
                break

            time.sleep(self.request_interval + random.random() * 1.0)

        self._log(f"\n[{self.source}] 完成：抓取 {len(results)} 条")
        return results
