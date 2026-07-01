#!/usr/bin/env python3
"""投标书生成 — 模板 + AI 增强"""

from datetime import datetime
import re
from db import get_notice_by_id
from config import KNOWLEDGE_DIR

# ── 8 章技术标模板（兜底用）──

BID_TEMPLATE = [
    ("一", "项目概述",
     "基于招标文件的核心信息：项目名称、建设地点、建设规模、投资额、工期要求"),
    ("二", "系统总体方案",
     "整体技术架构设计（云-边-端三层），含智慧停车管理平台、前端感知设备、网络传输"),
    ("三", "技术方案详解",
     "车牌识别系统、车位引导系统、无感支付系统、安防监控、诱导屏等子系统详细设计"),
    ("四", "施工组织设计",
     "施工总体部署、分阶段施工计划、资源配置、工期保障措施"),
    ("五", "质量保障体系",
     "质量管理组织架构、质量标准、过程控制、验收程序"),
    ("六", "安全管理措施",
     "安全管理制度、危险源识别、应急预案、文明施工"),
    ("七", "项目团队配置",
     "项目组织架构、关键岗位人员资质、劳动力计划"),
    ("八", "售后服务与运维方案",
     "质保期服务承诺、运维响应机制、培训计划、备品备件"),
]

CHECKLIST = [
    "投标函/法人授权书已签章",
    "营业执照/资质证书扫描件已附",
    "业绩证明材料已核实",
    "投标报价已人工填写",
    "关键技术人员资质证书已验证",
    "技术参数/指标已核实无AI幻觉",
    "页码/目录/密封符合招标文件要求",
    "投标保证金/保函已办理",
]


# ── 纯模板模式（离线，不调 AI）──

def gen_bid_template(notice_id: int) -> str:
    """基于商机数据 + 8 章模板生成标书骨架（无 AI）"""
    row = get_notice_by_id(notice_id)
    if not row:
        return f"❌ 商机 ID={notice_id} 不存在。"

    title = (row.get("title") or "").replace(" ", "")
    budget = row.get("budget", "—") or "—"
    region = (row.get("region") or "—").replace(" ", "")
    pub_date = row.get("pub_date", "—") or "—"
    notice_type = row.get("notice_type", "—") or "—"

    output = f"""投标文件（技术标）
{'='*50}

项目名称：{title}
招标类型：{notice_type}
项目地区：{region}
预算金额：{budget}
发布日期：{pub_date}
生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}

[!] 本文件为 AI 初稿骨架，黑色标注内容必须人工核实。
    报价、签章、资质原件必须人工提供。

{'='*50}

"""
    for num, chapter_title, _ in BID_TEMPLATE:
        if "项目概述" in chapter_title:
            desc = f"{title}，位于{region}地区，{'预算' + budget if budget != '—' else '预算待核实'}。本期招标类型为{notice_type}。"
        elif "技术方案" in chapter_title:
            desc = f"针对{title}的技术需求，本章详细阐述各子系统设计方案及技术指标。[实际方案需根据招标文件技术要求填写]"
        elif "施工" in chapter_title:
            desc = "本项目施工总体部署及分阶段计划。[实际施工方案需根据现场踏勘及工程量清单编制]"
        elif "团队" in chapter_title:
            desc = "本项目拟投入的组织架构及关键岗位人员配置。[实际人员信息、资质证书编号需人工填写]"
        else:
            desc = "[本章内容需根据招标文件具体要求及企业实际情况填写]"

        output += f"{num}、{chapter_title}\n"
        output += f"{'-'*40}\n"
        output += f"  {desc}\n"
        output += f"  [本章内容省略，实际编写时需展开]\n\n"

    output += _checklist_section()
    return output


def _checklist_section() -> str:
    lines = ["审核清单（提交前必须完成）", "="*30, ""]
    for i, c in enumerate(CHECKLIST):
        lines.append(f"  [{i+1}] {c}  [  ]")
    lines.append("")
    lines.append("[!] 法律风险提示：《招标投标法》第54条——虚构投标材料属违法行为。")
    lines.append("    本初稿仅供内部起草参考，终稿须经人工逐项审核。")
    return "\n".join(lines)


# ── 知识库加载 ──

def load_knowledge_context() -> str:
    """读取知识库目录下的文件，拼成 AI 上下文"""
    import os
    import yaml

    ctx_parts = []
    kb = KNOWLEDGE_DIR

    # 公司资质
    company_file = os.path.join(kb, "company.yml")
    if os.path.exists(company_file):
        try:
            company = yaml.safe_load(open(company_file))
            ctx_parts.append(f"【公司资质】\n{yaml.dump(company, allow_unicode=True)}")
        except Exception:
            pass

    # 项目业绩
    projects_file = os.path.join(kb, "projects.yml")
    if os.path.exists(projects_file):
        try:
            projects = yaml.safe_load(open(projects_file))
            ctx_parts.append(f"【历史项目业绩】\n{yaml.dump(projects, allow_unicode=True)}")
        except Exception:
            pass

    # 团队成员
    team_file = os.path.join(kb, "team.yml")
    if os.path.exists(team_file):
        try:
            team = yaml.safe_load(open(team_file))
            ctx_parts.append(f"【团队成员资质】\n{yaml.dump(team, allow_unicode=True)}")
        except Exception:
            pass

    # 技术方案模板
    sol_dir = os.path.join(kb, "solutions")
    if os.path.exists(sol_dir):
        for fname in sorted(os.listdir(sol_dir)):
            if fname.endswith(".md"):
                content = open(os.path.join(sol_dir, fname)).read()
                ctx_parts.append(f"【标准方案：{fname}】\n{content}")

    # 所有子目录下的 md 文件（laws/rules/industry/templates 等）
    for sub in ["laws", "rules", "industry", "templates", "imported"]:
        sub_dir = os.path.join(kb, sub)
        if os.path.exists(sub_dir):
            for fname in sorted(os.listdir(sub_dir)):
                if fname.endswith((".md", ".yml", ".yaml", ".json", ".txt")):
                    content = open(os.path.join(sub_dir, fname)).read()
                    ctx_parts.append(f"【{sub}/{fname}】\n{content}")

    # 术语表
    terms_file = os.path.join(kb, "terms.json")
    if os.path.exists(terms_file):
        try:
            import json
            terms = json.load(open(terms_file))
            ctx_parts.append(f"【行业术语】\n{json.dumps(terms, ensure_ascii=False, indent=2)}")
        except Exception:
            pass

    # 占位符校验
    placeholder_count = len(re.findall(r'XXXX+', "\n".join(ctx_parts), re.IGNORECASE))
    if placeholder_count > 0:
        ctx_parts.append(
            f"【警告】知识库中有 {placeholder_count} 处 'XXXXXX' 占位符。"
            "这些不是真实数据，你绝对不要把它们当作真实资质编号/证书编号写入标书。"
            "遇到占位符请标注【待人工填写】，不得编造。"
        )

    return "\n\n".join(ctx_parts)


# ── AI 模式（需要 DeepSeek API）──

def gen_bid_ai(notice_id: int) -> str:
    """AI 增强标书生成：知识库 + LLM 填充正文"""
    import ai

    if not ai.is_ready():
        return ("AI 功能未启用。\n"
                "请在桌面端 AI 分析页面点击「AI 设置」填入 API Key。\n"
                "注册获取: https://platform.deepseek.com/")

    row = get_notice_by_id(notice_id)
    if not row:
        return f"❌ 商机 ID={notice_id} 不存在。"

    r = dict(row)
    title = (r.get("title") or "").replace(" ", "")
    budget = r.get("budget", "—") or "—"
    region = (r.get("region") or "—").replace(" ", "")
    pub_date = r.get("pub_date", "—") or "—"
    notice_type = r.get("notice_type", "—") or "—"

    knowledge = load_knowledge_context()
    has_knowledge = bool(knowledge.strip())
    kb_note = "以下为公司真实信息，只可引用不得编造：\n" + knowledge if has_knowledge else "（无知识库，仅基于项目信息生成通用框架，不确定处标注【待人工确认】）"

    chapters_text = "\n".join(f"{num}、{ctitle}" for num, ctitle, _ in BID_TEMPLATE)

    system_prompt = f"""你是招投标文件撰写专家，专业编写智慧停车领域技术标。

{kb_note}

请严格按照以下章节结构生成技术标正文：

{chapters_text}

写作要求：
1. 资质编号、业绩金额、人员姓名必须来自上述知识库，不得编造
2. 技术方案可基于标准方案展开，但不得编造不存在的功能和指标
3. 不确定的内容标注【待人工确认】
4. 每章至少200字，技术方案章节至少400字
5. 专业术语准确，语气正式
6. 末尾附审核清单"""

    user_prompt = f"""请为以下项目生成技术标投标书：

项目名称：{title}
招标类型：{notice_type}
项目地区：{region}
预算金额：{budget}
发布日期：{pub_date}

按{len(BID_TEMPLATE)}章结构逐章撰写，输出完整标书正文。"""

    try:
        body = ai.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=8192
        )
    except RuntimeError as e:
        return f"❌ {e}"
    except Exception as e:
        return f"❌ AI 生成失败：{e}"

    header = f"""# 投标文件（技术标）

**项目名称：** {title}
**招标类型：** {notice_type}
**项目地区：** {region}
**预算金额：** {budget}
**发布日期：** {pub_date}
**生成时间：** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**生成方式：** AI 增强（DeepSeek）{' + 知识库' if has_knowledge else ''}

> ⚠️ 本文件为 AI 初稿，**黑色标注内容必须人工核实**。报价、签章、资质原件必须人工提供。

---

"""
    return header + body + "\n\n" + _checklist_section()
