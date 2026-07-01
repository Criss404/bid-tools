#!/usr/bin/env python3
"""AI 标讯分析 — 通过 ai.py 统一入口调用 AI"""

import ai
import db


def _notices_to_text(notices: list[dict]) -> str:
    """把标讯列表转为 AI 可读文本"""
    lines = []
    for i, n in enumerate(notices):
        title = (n.get("title") or "").replace(" ", "")
        region = (n.get("region") or "—").replace(" ", "")
        budget = n.get("budget", "—")
        notice_type = n.get("notice_type", "—")
        pub_date = n.get("pub_date", "—")
        score = n.get("score", 0)
        can_bid = "可参与" if n.get("can_bid") else "已结束"
        priority = n.get("priority", "—")
        lines.append(
            f"[{i+1}] {title}\n"
            f"    地区={region} | 类型={notice_type} | 预算={budget}\n"
            f"    日期={pub_date} | 评分={score} | {priority} | {can_bid}"
        )
    return "\n\n".join(lines)


# ── Public API ──

def ask(question: str) -> str:
    """自由提问：AI 查库后回答"""
    notices = db.get_all_notices(limit=50)
    if not notices:
        return "⚠️ 数据库中没有标讯数据，请先运行 seed 或爬取。"

    data_text = _notices_to_text(notices)
    stats = db.get_stats()

    try:
        return ai.chat(
            messages=[
                {"role": "system",
                 "content": f"""你是招投标标讯分析专家，专注于智慧招标领域。

当前数据库概况：总标讯{stats['total']}条，可投标{stats['can_bid']}条，A级{stats['high_priority']}条。

以下是当前数据库中的标讯列表，请基于这些数据回答用户问题：

{data_text}

分析原则：
1. 只基于上述真实数据回答，不要编造任何不存在的信息
2. 用中文回复，简洁实用，条理清晰
3. 涉及"能不能投"的判断时，保留追问空间（如：需要确认你们有没有对应资质）
4. 标注每条建议的理由
5. 如果用户问的是数据范围内的问题但没匹配到，老实说没找到"""},
                {"role": "user", "content": question}
            ],
            temperature=0.3,
            max_tokens=4096
        )
    except RuntimeError as e:
        return f"[X] {e}"
    except Exception as e:
        return f"[X] AI 分析失败：{e}"


def analyze_one(notice_id: int) -> str:
    """深度分析单条标讯"""
    notice = db.get_notice_by_id(notice_id)
    if not notice:
        return f"❌ 标讯 ID={notice_id} 不存在。"

    title = (notice.get("title") or "").replace(" ", "")
    data_text = _notices_to_text([notice])

    try:
        result = ai.chat(
            messages=[
                {"role": "system",
                 "content": """你是招投标分析专家。对单条标讯进行深度评估，输出包含：

1. 项目概况（一句话总结）
2. 投标价值评估（高/中/低 + 理由）
3. 风险点（资质要求、竞对可能性、时间紧迫度）
4. 竞争建议（要不要投、如果要投需要准备什么）
5. 需要进一步确认的信息（人工去核实什么）"""},
                {"role": "user",
                 "content": f"请深度分析这条招标标讯：\n\n{data_text}"}
            ],
            temperature=0.3,
            max_tokens=2048
        )
        return f"## 深度标讯分析\n\n**项目：** {title}\n\n{result}"
    except RuntimeError as e:
        return f"[X] {e}"
    except Exception as e:
        return f"[X] AI 分析失败：{e}"


def rank_opportunities(notice_ids: list[int] | None = None) -> str:
    """批量标讯排名 + 投资建议"""
    if notice_ids:
        notices = [db.get_notice_by_id(nid) for nid in notice_ids]
        notices = [n for n in notices if n]
    else:
        notices = db.get_all_notices(limit=30)

    if not notices:
        return "⚠️ 没有可分析的标讯。"

    data_text = _notices_to_text(notices)

    try:
        return ai.chat(
            messages=[
                {"role": "system",
                 "content": """你是招投标策略分析师。根据标讯列表，输出：

## 推荐投标优先级排名（Top 5）
按"值得投"程度排序，每条说明理由

## 市场洞察
- 区域热度（哪些地区项目密集）
- 项目类型趋势（EPC/施工/监理占比）
- 预算区间分布

## 本周行动建议
- 建议立即跟进的项目
- 建议观望的项目
- 建议放弃的项目"""},
                {"role": "user",
                 "content": f"请分析这批招标标讯并给出排名和建议：\n\n{data_text}"}
            ],
            temperature=0.3,
            max_tokens=4096
        )
    except RuntimeError as e:
        return f"[X] {e}"
    except Exception as e:
        return f"[X] AI 分析失败：{e}"


def weekly_report() -> str:
    """生成本周标讯总结"""
    notices = db.get_all_notices(limit=100)
    stats = db.get_stats()

    data_text = _notices_to_text(notices)

    try:
        return ai.chat(
            messages=[
                {"role": "system",
                 "content": f"""你是招标行业市场分析师。数据库概况：总{stats['total']}条，可投标{stats['can_bid']}条。

请生成一份本周招标标讯周报，包含：

## 本周标讯概览
## 区域热度地图
## 重点项目关注
## 流标/废标分析（如果有）
## 下周行动计划"""},
                {"role": "user",
                 "content": f"请生成本周招标标讯分析周报：\n\n{data_text}"}
            ],
            temperature=0.4,
            max_tokens=4096
        )
    except RuntimeError as e:
        return f"[X] {e}"
    except Exception as e:
        return f"[X] AI 分析失败：{e}"
