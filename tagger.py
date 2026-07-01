#!/usr/bin/env python3
"""商机自动打标签 — 纯规则引擎

从 config.PRIORITY_RULES 驱动，给每条公告自动标注：
- priority（高优/中优/参考）
- can_bid（可投/不可投）
- stage（项目形态：施工/监理/设备/设计/总包）
- score（0-100 综合评分）
"""

import re
from config import PRIORITY_RULES


# ── 项目形态关键词（从标题/正文提取 stage）──

STAGE_PATTERNS = [
    ("总包", ["总承包", "EPC", "EPCO", "epc", "epco", "总包", "设计施工"]),
    ("设计", ["设计(?!施工)", "勘察设计", "方案设计"]),
    ("设备", ["设备采购", "设备安装", "道闸", "车牌识别", "摄像机", "诱导屏"]),
    ("监理", ["监理"]),
    ("施工", ["施工", "建设", "改造", "修缮", "新建", "安装", "土建"]),
]

# 评分相关
BUDGET_PATTERN = re.compile(r"(\d+)\s*万", re.IGNORECASE)


def _match_stage(title: str, content: str) -> str:
    """从标题+正文提取项目形态"""
    text = f"{title} {content}"
    for stage, patterns in STAGE_PATTERNS:
        for p in patterns:
            if re.search(p, text):
                return stage
    return "施工"  # 默认


def _extract_budget_amount(budget_str: str) -> int | None:
    """从预算字符串提取金额（万元）"""
    if not budget_str or budget_str in ("—", "", "未知"):
        return None
    m = BUDGET_PATTERN.search(str(budget_str))
    if m:
        return int(m.group(1))
    # 尝试直接数字（可能是纯数字）
    try:
        return int(float(budget_str))
    except (ValueError, TypeError):
        return None


def _calc_score(priority: str, stage: str, budget_str: str) -> float:
    """综合评分 0-100"""
    base = {"A级": 75, "B级": 45, "C级": 15}
    score = base.get(priority, 40)

    # 总包/EPC 加分
    if stage == "总包":
        score += 15
    elif stage == "设计":
        score += 5

    # 预算越大分数越高
    amount = _extract_budget_amount(budget_str)
    if amount:
        if amount > 5000:
            score += 10
        elif amount > 1000:
            score += 7
        elif amount > 100:
            score += 4
        else:
            score += 2

    return min(score, 100)


def auto_tag(notice: dict) -> dict:
    """
    输入原始公告字段，返回完整的标签字段 dict。
    如果 notice 里已有 priority/can_bid/stage/score 则保留不覆盖。

    返回示例：
        {"priority": "A级", "can_bid": 1, "stage": "总包", "score": 95.0}
    """
    title = notice.get("title", "")
    content = notice.get("content", "")
    notice_type = notice.get("notice_type", "") or ""
    budget = notice.get("budget", "") or ""

    # ── 优先级 ──
    priority = "C级"  # 默认
    for pname, rules in PRIORITY_RULES.items():
        if notice_type in rules.get("notice_type", []):
            priority = pname
            break

    # ── 可投 ──
    can_bid = 1 if PRIORITY_RULES.get(priority, {}).get("can_bid", False) else 0

    # ── 项目形态 ──
    stage = _match_stage(title, content)

    # ── 评分 ──
    score = _calc_score(priority, stage, budget)

    return {
        "priority": priority,
        "can_bid": can_bid,
        "stage": stage,
        "score": score,
    }


def tag_and_merge(notice: dict) -> dict:
    """
    给一条公告打标签 + 规范化地区，只填写缺失字段（不覆盖已有值）。
    返回打了标签后的完整 dict。
    """
    tags = auto_tag(notice)
    merged = dict(notice)

    for key in ("priority", "can_bid", "stage", "score"):
        if not merged.get(key) or merged[key] in (0, 0.0, ""):
            merged[key] = tags[key]

    # 地区规范化
    region = merged.get("region", "")
    if region:
        merged["region"] = _normalize_region(region.replace(" ", ""))

    return merged


# ── 地区规范化（权威定义在 tagger）──

REGION_NORMALIZE = {
    "云南省": "云南", "四川省": "四川", "山东省": "山东", "江苏省": "江苏",
    "辽宁省": "辽宁", "安徽省": "安徽", "浙江省": "浙江", "河北省": "河北",
    "河南省": "河南", "湖北省": "湖北", "湖南省": "湖南", "广东省": "广东",
    "福建省": "福建", "江西省": "江西", "贵州省": "贵州", "山西省": "山西",
    "陕西省": "陕西", "甘肃省": "甘肃", "青海省": "青海", "吉林省": "吉林",
    "黑龙江省": "黑龙江", "海南省": "海南", "台湾省": "台湾",
    "北京市": "北京", "天津市": "天津", "上海市": "上海", "重庆市": "重庆",
    "广西壮族自治区": "广西", "内蒙古自治区": "内蒙古",
    "宁夏回族自治区": "宁夏", "新疆维吾尔自治区": "新疆", "西藏自治区": "西藏",
    "九江": "江西", "绍兴": "浙江", "丽水": "浙江", "嘉兴": "浙江", "杭州": "浙江",
    "青岛": "山东", "石家庄": "河北", "石家": "河北", "登封": "河南",
    "诸暨": "浙江", "桐乡": "浙江", "景宁": "浙江", "文山": "云南",
    "广元": "四川", "乐山": "四川", "绵阳": "四川", "烟台": "山东",
    "海阳": "山东", "阳谷": "山东", "扬州": "江苏", "藁城": "河北",
    "抚州": "江西", "山东产权交易中心综合交易系统": "山东",
}


def _normalize_region(raw: str) -> str:
    """规范化地区名：省→短省名，城市→省"""
    if not raw:
        return ""
    raw = raw.strip()
    if raw in REGION_NORMALIZE:
        return REGION_NORMALIZE[raw]
    for k, v in REGION_NORMALIZE.items():
        if k in raw or raw in k:
            return v
    return raw
