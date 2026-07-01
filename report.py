#!/usr/bin/env python3
"""标讯分析报告"""

from db import get_db


def gen_report() -> str:
    """生成标讯分析报告（返回文本）"""
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM notices").fetchone()[0]
    can_bid = conn.execute("SELECT COUNT(*) FROM notices WHERE can_bid=1").fetchone()[0]
    regions = conn.execute(
        "SELECT region, COUNT(*) as cnt FROM notices GROUP BY region ORDER BY cnt DESC"
    ).fetchall()
    stages = conn.execute(
        "SELECT stage, COUNT(*) as cnt FROM notices GROUP BY stage ORDER BY cnt DESC"
    ).fetchall()
    priorities = conn.execute(
        "SELECT priority, COUNT(*) as cnt FROM notices GROUP BY priority ORDER BY cnt DESC"
    ).fetchall()
    top = conn.execute("""
        SELECT id, title, score, priority, stage, region, pub_date
        FROM notices WHERE can_bid=1 ORDER BY score DESC LIMIT 5
    """).fetchall()
    conn.close()

    report = f"""
╔══════════════════════════════════════════╗
║       🎯 招投标信息工具 · 分析报告        ║
╚══════════════════════════════════════════╝

📊 总标讯：{total} 条
🎯 可投标（招标中）：{can_bid} 条

📍 地区分布：
"""
    for r, c in regions:
        region_clean = (r or "—").replace(" ", "")
        report += f"   {region_clean:<12s} {c} 条\n"

    report += "\n📋 信息阶段分布：\n"
    for s, c in stages:
        report += f"   {(s or '未知'):<12s} {c} 条\n"

    report += "\n🔴 优先级分布：\n"
    for p, c in priorities:
        report += f"   {p:<12s} {c} 条\n"

    report += "\n💎 重点可投标讯（Top 5）：\n"
    report += f"   {'ID':<4} {'评分':<6} {'类型':<8} {'阶段':<8} {'地区':<8} 标题\n"
    report += "   " + "-" * 68 + "\n"
    for t in top:
        title_clean = (t["title"] or "").replace(" ", "")
        report += (f"   {t['id']:<4} {t['score']:<6.0f} {t['priority']:<8} "
                   f"{t['stage']:<8} {(t['region'] or '—').replace(' ', ''):<8} {title_clean}\n")

    return report


def report_dict() -> dict:
    """生成标讯分析报告（返回字典，供 GUI 用）"""
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM notices").fetchone()[0]
    can_bid = conn.execute("SELECT COUNT(*) FROM notices WHERE can_bid=1").fetchone()[0]
    regions = [dict(r) for r in conn.execute(
        "SELECT region, COUNT(*) as cnt FROM notices GROUP BY region ORDER BY cnt DESC"
    ).fetchall()]
    top = [dict(r) for r in conn.execute(
        "SELECT id, title, score, priority, stage, region, pub_date "
        "FROM notices ORDER BY score DESC LIMIT 10"
    ).fetchall()]
    conn.close()
    return {
        "total": total,
        "can_bid": can_bid,
        "regions": regions,
        "top": top,
    }
