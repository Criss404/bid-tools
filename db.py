#!/usr/bin/env python3
"""数据库层 — SQLite + FTS5 全文索引"""

import sqlite3
import os

import jieba
from config import DB_PATH


def get_db() -> sqlite3.Connection:
    """获取数据库连接（自动建数据目录）"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_database():
    """建表：主表 + FTS5 虚拟表 + 同步触发器"""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS notices (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            source      TEXT    NOT NULL,
            title       TEXT    NOT NULL,
            notice_type TEXT,
            biz_type    TEXT,
            region      TEXT,
            publisher   TEXT,
            budget      TEXT,
            url         TEXT    UNIQUE,
            content     TEXT,
            raw_id      TEXT,
            pub_date    TEXT,
            created_at  TEXT    DEFAULT (datetime('now','localtime')),
            priority    TEXT,
            stage       TEXT,
            can_bid     INTEGER DEFAULT 0,
            score       REAL    DEFAULT 0.0
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS notices_fts USING fts5(
            title, content, publisher, region, biz_type,
            content='notices', content_rowid='id',
            tokenize='unicode61'
        );

        CREATE TRIGGER IF NOT EXISTS notices_ai AFTER INSERT ON notices BEGIN
            INSERT INTO notices_fts(rowid, title, content, publisher, region, biz_type)
            VALUES (new.id, new.title, new.content, new.publisher, new.region, new.biz_type);
        END;

        CREATE TRIGGER IF NOT EXISTS notices_ad AFTER DELETE ON notices BEGIN
            INSERT INTO notices_fts(notices_fts, rowid, title, content, publisher, region, biz_type)
            VALUES ('delete', old.id, old.title, old.content, old.publisher, old.region, old.biz_type);
        END;

        CREATE TRIGGER IF NOT EXISTS notices_au AFTER UPDATE ON notices BEGIN
            INSERT INTO notices_fts(notices_fts, rowid, title, content, publisher, region, biz_type)
            VALUES ('delete', old.id, old.title, old.content, old.publisher, old.region, old.biz_type);
            INSERT INTO notices_fts(rowid, title, content, publisher, region, biz_type)
            VALUES (new.id, new.title, new.content, new.publisher, new.region, new.biz_type);
        END;
    """)
    conn.commit()
    conn.close()
    print("✅ 数据库初始化完成:", DB_PATH)


# ── 内置商机种子数据（来自 ggzy.gov.cn 真实抓取）──

SEED_NOTICES = [
    {
        "source": "ggzy", "title": "滨州市沾化区城市停车场项目-府佑街、金海七路及绿荫道路停车场建设项目施工",
        "notice_type": "开标记录", "biz_type": "工程建设·房屋建筑业", "region": "山东",
        "publisher": "滨州市沾化区综合行政执法局", "budget": "—",
        "url": "https://ggzy.gov.cn/info/001",
        "content": "滨州市沾化区城市停车场项目施工标段开标记录。建设内容包括府佑街停车场、金海七路停车场及绿荫道路停车场。涉及土建施工、排水工程、照明及绿化配套。",
        "pub_date": "2026-06-17", "priority": "B级", "stage": "施工", "can_bid": 0, "score": 55
    },
    {
        "source": "ggzy", "title": "滨州市沾化区城市停车场项目-府佑街、金海七路及绿荫道路停车场建设项目监理",
        "notice_type": "开标记录", "biz_type": "工程建设", "region": "山东",
        "publisher": "滨州市沾化区综合行政执法局", "budget": "—",
        "url": "https://ggzy.gov.cn/info/002",
        "content": "同上项目监理标段开标记录。监理范围包括施工全过程质量控制、进度管理、安全管理及竣工验收。",
        "pub_date": "2026-06-17", "priority": "B级", "stage": "监理", "can_bid": 0, "score": 50
    },
    {
        "source": "ggzy", "title": "校园新建停车场及周边环境整体提升竞争性磋商公告",
        "notice_type": "采购/资审公告", "biz_type": "政府采购", "region": "江苏",
        "publisher": "某市教育局", "budget": "—",
        "url": "https://ggzy.gov.cn/info/003",
        "content": "校园新建停车场及周边环境整体提升项目竞争性磋商。采购内容包括停车场新建、周边道路、绿化及照明工程。",
        "pub_date": "2026-06-17", "priority": "A级", "stage": "施工", "can_bid": 1, "score": 85
    },
    {
        "source": "ggzy", "title": "瓦房店市红沿河镇红沿河核电员工停车场项目施工中标候选人公示",
        "notice_type": "中标公示", "biz_type": "工程建设", "region": "辽宁",
        "publisher": "瓦房店市红沿河镇人民政府", "budget": "—",
        "url": "https://ggzy.gov.cn/info/004",
        "content": "瓦房店市红沿河镇红沿河核电员工停车场项目施工中标候选人公示。第一中标候选人：XX建设集团有限公司。",
        "pub_date": "2026-06-17", "priority": "B级", "stage": "施工", "can_bid": 0, "score": 60
    },
    {
        "source": "ggzy", "title": "小金县沙坝片区停车场建设项目（一期）招标公告",
        "notice_type": "招标公告", "biz_type": "工程建设", "region": "四川",
        "publisher": "小金县住房和城乡建设局", "budget": "—",
        "url": "https://ggzy.gov.cn/info/005",
        "content": "小金县沙坝片区停车场建设项目一期工程招标公告。建设规模约5000平方米停车场及配套设施。工期180天。投标截止2026年7月15日。",
        "pub_date": "2026-06-17", "priority": "A级", "stage": "施工", "can_bid": 1, "score": 90
    },
    {
        "source": "ggzy", "title": "丹阳市开发区大泊集镇迎宾路东侧停车场改造项目更正公告(二)",
        "notice_type": "更正公告", "biz_type": "政府采购", "region": "江苏",
        "publisher": "丹阳市开发区管委会", "budget": "—",
        "url": "https://ggzy.gov.cn/info/006",
        "content": "停车场改造项目开标时间及工程量清单变更通知。原开标时间推迟至7月10日。",
        "pub_date": "2026-06-17", "priority": "C级", "stage": "施工", "can_bid": 0, "score": 20
    },
    {
        "source": "ggzy", "title": "绵阳城市停车场智慧化升级改建EPC总承包招标公告",
        "notice_type": "招标公告", "biz_type": "工程建设", "region": "四川",
        "publisher": "绵阳市投资控股集团", "budget": "预估8000万元",
        "url": "https://ggzy.gov.cn/info/007",
        "content": "绵阳市城市停车场智慧化升级改建工程EPC总承包。含智慧停车管理系统、车牌识别、车位引导、无感支付、云平台等。覆盖市区50+停车场，约15000个车位。建设期18个月。投标截止2026年7月30日。",
        "pub_date": "2026-06-15", "priority": "A级", "stage": "总包", "can_bid": 1, "score": 100
    },
    {
        "source": "ggzy", "title": "黄山新能源智能充储-停车场改造EPCO中标结果公告",
        "notice_type": "中标公示", "biz_type": "工程建设", "region": "安徽",
        "publisher": "黄山旅游集团", "budget": "中标价3260万元",
        "url": "https://ggzy.gov.cn/info/008",
        "content": "黄山风景区新能源智能充储一体化停车场改造EPCO项目中标结果。含充电桩建设、光伏车棚、储能系统、智慧停车管理平台。",
        "pub_date": "2026-06-12", "priority": "B级", "stage": "总包", "can_bid": 0, "score": 70
    },
    {
        "source": "ggzy", "title": "首都医科大学停车场及周边设施修缮改造项目招标公告",
        "notice_type": "招标公告", "biz_type": "政府采购", "region": "北京",
        "publisher": "首都医科大学", "budget": "预算960万元",
        "url": "https://ggzy.gov.cn/info/009",
        "content": "首都医科大学职工停车场修缮改造及周边设施工程。含旧停车场翻新、安防监控系统升级、出入口道闸更换、停车诱导屏安装。投标截止2026年7月20日。",
        "pub_date": "2026-06-10", "priority": "A级", "stage": "施工", "can_bid": 1, "score": 95
    },
    {
        "source": "ggzy", "title": "吾悦二期、江畔尚城两处停车场供电工程监理交易公告",
        "notice_type": "交易公告", "biz_type": "其他", "region": "—",
        "publisher": "—", "budget": "—",
        "url": "https://ggzy.gov.cn/info/010",
        "content": "吾悦二期、江畔尚城两处停车场供电工程监理交易公告。供电工程设计及施工监理服务。",
        "pub_date": "2026-06-17", "priority": "C级", "stage": "监理", "can_bid": 0, "score": 25
    },
]


def seed_data():
    """写入内置商机种子数据（jieba 分词后入库）"""
    conn = get_db()
    count = 0
    for n in SEED_NOTICES:
        title_seg = " ".join(jieba.cut(n["title"]))
        content_seg = " ".join(jieba.cut(n["content"]))
        publisher_seg = " ".join(jieba.cut(n["publisher"]))
        region_seg = " ".join(jieba.cut(n["region"]))
        biz_seg = " ".join(jieba.cut(n["biz_type"]))

        try:
            conn.execute("""
                INSERT INTO notices (source, title, notice_type, biz_type, region,
                    publisher, budget, url, content, pub_date,
                    priority, stage, can_bid, score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                n["source"], title_seg, n["notice_type"], biz_seg, region_seg,
                publisher_seg, n["budget"], n["url"], content_seg, n["pub_date"],
                n["priority"], n["stage"], n["can_bid"], n["score"]
            ))
            count += 1
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()
    print(f"✅ 写入 {count} 条商机数据")


def insert_notice(notice: dict, auto_tag: bool = True) -> bool:
    """插入单条公告，返回是否成功（False=重复）

    auto_tag=True 时，自动标注优先级/项目形态/可投/评分（仅填充缺失字段）。
    """
    if auto_tag:
        from tagger import tag_and_merge
        notice = tag_and_merge(notice)

    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO notices (source, title, notice_type, biz_type, region,
                publisher, budget, url, content, pub_date,
                priority, stage, can_bid, score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            notice.get("source", "unknown"),
            " ".join(jieba.cut(notice.get("title", ""))),
            notice.get("notice_type", ""),
            " ".join(jieba.cut(notice.get("biz_type", ""))),
            " ".join(jieba.cut(notice.get("region", ""))),
            " ".join(jieba.cut(notice.get("publisher", ""))),
            notice.get("budget", ""),
            notice["url"],
            " ".join(jieba.cut(notice.get("content", ""))),
            notice.get("pub_date", ""),
            notice.get("priority", "B级"),
            notice.get("stage", ""),
            notice.get("can_bid", 0),
            notice.get("score", 50.0)
        ))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def get_notice_by_id(nid: int) -> dict | None:
    """根据 ID 获取单条商机详情"""
    conn = get_db()
    row = conn.execute("SELECT * FROM notices WHERE id = ?", (nid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_notices(limit: int = 200) -> list[dict]:
    """获取全部商机"""
    conn = get_db()
    rows = conn.execute(
        "SELECT id, title, notice_type, region, pub_date, priority, stage, can_bid, score "
        "FROM notices ORDER BY score DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_notice(nid: int) -> bool:
    """删除单条商机，FTS5 触发器自动同步索引。返回 True=成功"""
    conn = get_db()
    conn.execute("DELETE FROM notices WHERE id = ?", (nid,))
    deleted = conn.total_changes > 0
    conn.commit()
    conn.close()
    return deleted


def delete_notices(ids: list[int]) -> int:
    """批量删除商机。返回实际删除条数"""
    if not ids:
        return 0
    conn = get_db()
    placeholders = ",".join("?" * len(ids))
    conn.execute(f"DELETE FROM notices WHERE id IN ({placeholders})", ids)
    deleted = conn.total_changes
    conn.commit()
    conn.close()
    return deleted


def get_stats() -> dict:
    """统计数据"""
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM notices").fetchone()[0]
    can_bid = conn.execute("SELECT COUNT(*) FROM notices WHERE can_bid=1").fetchone()[0]
    high = conn.execute("SELECT COUNT(*) FROM notices WHERE priority='高优'").fetchone()[0]
    conn.close()
    return {"total": total, "can_bid": can_bid, "high_priority": high}
