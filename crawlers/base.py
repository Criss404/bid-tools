#!/usr/bin/env python3
"""爬虫基类 — 模板方法模式

每个数据源实现两个方法：
    _fetch_urls() → list[str]     取列表页的详情URL
    _parse_detail(html, url) → dict | None   解析详情页

crawl() 模板方法负责：取URL → 逐个解析 → 去重 → 返回
"""

import time
import random
import re
from abc import ABC, abstractmethod
import requests


class BaseCrawler(ABC):
    """爬虫抽象基类"""

    source: str = ""           # 数据源标识: ggzy / ccgp
    base_url: str = ""         # 站点根URL
    request_interval: float = 2.0   # 请求间隔（秒）

    def __init__(self, keyword_filter: str = "", max_pages: int = 30,
                 request_interval: float = 2.0,
                 log_callback=None, cancel_event=None):
        """
        keyword_filter: 只返回标题含该关键词的公告（空=全部）
        max_pages: 最多抓多少条详情
        request_interval: 请求间隔（秒）
        log_callback: 日志回调函数，接收 (msg: str)，用于GUI实时日志
        cancel_event: threading.Event，设了就停止爬取
        """
        self.keyword_filter = keyword_filter
        self.request_interval = request_interval
        self.max_pages = max_pages
        self._log_cb = log_callback
        self._cancel = cancel_event
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })

    @abstractmethod
    def _fetch_urls(self) -> list[str]:
        """从列表页获取详情URL列表"""
        ...

    @abstractmethod
    def _parse_detail(self, html: str, url: str) -> dict | None:
        """解析详情页HTML，返回标准公告dict"""
        ...

    def _log(self, msg: str):
        """输出日志：print + 回调（如有）"""
        print(msg)
        if self._log_cb:
            try:
                self._log_cb(msg)
            except Exception:
                pass

    def crawl(self) -> list[dict]:
        """模板方法：取列表 → 逐个解析详情 → 返回"""
        self._log(f"[{self.source}] 正在抓取列表页...")
        urls = self._fetch_urls()

        self._log(f"[{self.source}] 发现 {len(urls)} 个URL，开始抓取详情（间隔{self.request_interval}s）...")

        results = []
        seen = set()
        count = 0
        fail_streak = 0  # 连续失败计数

        for url in urls:
            # 用户手动停止
            if self._cancel and self._cancel.is_set():
                self._log("[取消] 用户手动停止爬取")
                break

            if count >= self.max_pages:
                break

            if url in seen:
                continue
            seen.add(url)

            count += 1
            success = False
            for attempt in range(1, 4):  # 最多重试 3 次
                try:
                    resp = self.session.get(url, timeout=20)
                    if resp.status_code != 200:
                        if attempt < 3:
                            time.sleep(1.5 * attempt)
                            continue
                        self._log(f"  [{count}] HTTP {resp.status_code} {url[:60]}")
                        break

                    resp.encoding = resp.apparent_encoding or "utf-8"

                    notice = self._parse_detail(resp.text, url)
                    if not notice:
                        if attempt == 3:
                            self._log(f"  [{count}] 解析失败 {url[:60]}")
                        break

                    title = notice.get("title", "")
                    if self.keyword_filter and self.keyword_filter not in title:
                        self._log(f"  [{count}] 跳过(不匹配): {title[:50]}")
                        success = True
                        break

                    results.append(notice)
                    self._log(f"  [{count}] {notice.get('notice_type','?'):8s} {title[:50]}")
                    success = True
                    break

                except requests.RequestException as e:
                    if attempt < 3:
                        self._log(f"  [{count}] 重试 {attempt}/3: {e}")
                        time.sleep(1.5 * attempt)
                        continue
                    self._log(f"  [{count}] 网络错误: {e}")
                    break
                except Exception as e:
                    if attempt < 3:
                        time.sleep(1.5 * attempt)
                        continue
                    self._log(f"  [{count}] 异常: {e}")
                    break

            if success:
                fail_streak = 0
                time.sleep(self.request_interval + random.random() * 1.0)
            else:
                fail_streak += 1
                if fail_streak >= 3:
                    self._log(f"[停止] 连续 {fail_streak} 次失败，自动停止")
                    break

        self._log(f"\n[{self.source}] 完成：抓取 {len(results)}/{count} 条")
        return results
