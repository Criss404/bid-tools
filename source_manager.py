#!/usr/bin/env python3
"""爬虫源管理 — 读写 sources.yml，增删改查"""

import yaml
import os

CFG = os.path.join(os.path.expanduser("~"), ".bid_tool", "sources.yml")


def _load_cfg() -> dict:
    if not os.path.exists(CFG):
        return {"sources": []}
    with open(CFG, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {"sources": []}


def _save_cfg(cfg: dict):
    with open(CFG, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False)


def list_sources() -> list[dict]:
    """返回所有源（不含内部字段）"""
    cfg = _load_cfg()
    return cfg.get("sources", [])


def get_enabled_sources() -> list[dict]:
    """返回已启用的源"""
    return [s for s in list_sources() if s.get("enabled", True)]


def add_source(name: str, url: str, source_type: str = "single",
               keyword: str = "", enabled: bool = True) -> bool:
    """添加一个新源，返回 True 成功（不重复添加）"""
    # 规范化类型名（GUI下拉可能带说明）
    if "ggzy" in source_type:
        source_type = "ggzy"
    elif "cebpub" in source_type:
        source_type = "cebpubservice"
    elif "single" in source_type or "generic" in source_type:
        source_type = "single"

    cfg = _load_cfg()
    for s in cfg.get("sources", []):
        if s.get("url") == url:
            return False  # 已存在
    cfg.setdefault("sources", []).append({
        "name": name,
        "type": source_type,
        "url": url,
        "keyword": keyword,
        "enabled": enabled,
    })
    _save_cfg(cfg)
    return True


def remove_source(url: str) -> bool:
    """按 URL 删除源"""
    cfg = _load_cfg()
    before = len(cfg.get("sources", []))
    cfg["sources"] = [s for s in cfg.get("sources", []) if s.get("url") != url]
    _save_cfg(cfg)
    return len(cfg["sources"]) < before


def toggle_source(url: str) -> bool | None:
    """切换启用/禁用，返回新状态（None=未找到）"""
    cfg = _load_cfg()
    for s in cfg.get("sources", []):
        if s.get("url") == url:
            s["enabled"] = not s.get("enabled", True)
            _save_cfg(cfg)
            return s["enabled"]
    return None


def crawl_all_enabled(*, log_callback=None, override_keyword: str = "",
                      cancel_event=None) -> dict[str, int]:
    """遍历所有启用的源，执行爬取 → 自动入库。

    override_keyword: GUI 输入的关键词，覆盖 sources.yml 里的 keyword
    cancel_event: threading.Event，设了就停止
    返回 {"source_name": 新条数}
    """
    from db import insert_notice
    results = {}

    for src in get_enabled_sources():
        if cancel_event and cancel_event.is_set():
            if log_callback:
                log_callback("\n[取消] 用户手动停止")
            break

        stype = src.get("type", "generic")
        name = src.get("name", stype)
        url = src.get("url", "")
        keyword = override_keyword or src.get("keyword", "")

        if log_callback:
            log_callback(f"\n── [{name}] ──")

        try:
            if stype == "ggzy":
                from crawlers.ggzy import GgzyCrawler
                c = GgzyCrawler(keyword_filter=keyword, max_pages=20,
                                request_interval=1.5, log_callback=log_callback,
                                cancel_event=cancel_event)
                items = c.crawl()
                new = sum(1 for it in items if insert_notice(it, auto_tag=True))
                results[name] = new

            elif stype == "cebpubservice":
                from crawlers.cebpubservice import CebCrawler
                c = CebCrawler(keyword_filter=keyword, max_pages=20, list_pages=10,
                               request_interval=1.5, log_callback=log_callback,
                               cancel_event=cancel_event)
                items = c.crawl()
                new = sum(1 for it in items if insert_notice(it, auto_tag=True))
                results[name] = new

            elif stype in ("generic", "single"):
                if log_callback:
                    log_callback(f"  [单页抓取] trafilatura: {url}")
                from extractor import ingest_url
                ok = ingest_url(url)
                results[name] = 1 if ok else 0

        except Exception as e:
            if log_callback:
                log_callback(f"  [X] 错误: {e}")
            results[name] = 0

    return results
