#!/usr/bin/env python3
"""搜索层 — FTS5 全文搜索 + jieba 分词"""

import jieba
from db import get_db


def search(keyword: str, limit: int = 50) -> list[dict]:
    """FTS5 全文搜索，返回商机列表"""
    conn = get_db()
    kw_seg = " ".join(jieba.cut(keyword))
    rows = conn.execute("""
        SELECT n.id, n.title, n.notice_type, n.biz_type, n.region,
               n.pub_date, n.priority, n.stage, n.can_bid, n.score, n.url,
               snippet(notices_fts, 2, '<mark>', '</mark>', '...', 32) AS snippet
        FROM notices_fts f
        JOIN notices n ON n.id = f.rowid
        WHERE notices_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """, (kw_seg, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_filtered(keyword: str, region: str = "", notice_type: str = "",
                    can_bid_only: bool = False, limit: int = 50) -> list[dict]:
    """带过滤条件的全文搜索"""
    conn = get_db()
    kw_seg = " ".join(jieba.cut(keyword))

    sql = """
        SELECT n.id, n.title, n.notice_type, n.biz_type, n.region,
               n.pub_date, n.priority, n.stage, n.can_bid, n.score, n.url,
               snippet(notices_fts, 2, '<mark>', '</mark>', '...', 32) AS snippet
        FROM notices_fts f
        JOIN notices n ON n.id = f.rowid
        WHERE notices_fts MATCH ?
    """
    params = [kw_seg]

    if region:
        region_seg = " ".join(jieba.cut(region))
        sql += " AND n.region LIKE ?"
        params.append(f"%{region_seg}%")
    if notice_type:
        sql += " AND n.notice_type LIKE ?"
        params.append(f"%{notice_type}%")
    if can_bid_only:
        sql += " AND n.can_bid = 1"

    sql += " ORDER BY rank LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]
