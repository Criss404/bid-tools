#!/usr/bin/env python3
"""bid_tool — 停车商机雷达 + AI投标书 统一入口

命令:
    initdb              初始化数据库
    seed                写入内置商机数据（10条）
    search <关键词>     全文搜索
    report              商机分析报告
    bid <ID> [--ai]     生成投标书（默认模板，--ai 用 DeepSeek）
    ask <问题>          AI 自由提问
    analyze <ID>        AI 深度分析单条商机
    rank                AI 商机排名推荐
    weekly              AI 生成本周周报
    crawl [关键词]      从所有启用的源爬取（见 sources.yml）
    sources             列出爬虫源
    source-add <名> <URL> [type] [kw]  添加爬虫源
    url <URL>           抓取URL正文 → 自动标签 → 入库
    web                 启动 Web 看板 (http://localhost:8000)
    gui                 启动桌面端
"""

import sys
import os

# 确保能 import 同目录模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DB_PATH


def cmd_initdb():
    from db import init_database
    init_database()
    print("提示: 运行 'python main.py seed' 写入示例数据")


def cmd_seed():
    from db import seed_data
    seed_data()


def cmd_search(args: list[str]):
    from search import search
    kw = args[0] if args else "停车"
    results = search(kw)
    if not results:
        print(f"未找到与「{kw}」相关的结果")
        return
    print(f"\n搜索「{kw}」共 {len(results)} 条结果：\n")
    for r in results:
        title = (r.get("title") or "").replace(" ", "")
        region = (r.get("region") or "").replace(" ", "")
        notice_type = r.get("notice_type", "—")
        pub_date = r.get("pub_date", "—") or "—"
        priority = r.get("priority", "—")
        score = r.get("score", 0)
        can_bid = " [可投]" if r.get("can_bid") else ""
        print(f"  [{priority}] {title}")
        print(f"    {region}  {notice_type}  {pub_date}  {score:.0f}分{can_bid}")
        print()


def cmd_report():
    from report import gen_report
    print(gen_report())


def cmd_bid(args: list[str]):
    from bid_writer import gen_bid_template, gen_bid_ai

    use_ai = "--ai" in args
    clean_args = [a for a in args if a != "--ai"]
    if not clean_args:
        print("用法: python main.py bid <商机ID> [--ai]")
        return

    nid = int(clean_args[0])
    if use_ai:
        print("正在调用 DeepSeek AI 生成标书，请稍候...\n")
        result = gen_bid_ai(nid)
    else:
        result = gen_bid_template(nid)
    print(result)


def cmd_ask(args: list[str]):
    from ai_analyzer import ask
    question = " ".join(args) if args else input("请输入问题: ")
    if not question.strip():
        print("请输入问题")
        return
    print("AI 思考中...\n")
    print(ask(question))


def cmd_analyze(args: list[str]):
    from ai_analyzer import analyze_one
    if not args:
        print("用法: python main.py analyze <商机ID>")
        return
    nid = int(args[0])
    print("AI 分析中...\n")
    print(analyze_one(nid))


def cmd_rank():
    from ai_analyzer import rank_opportunities
    print("AI 排名中...\n")
    print(rank_opportunities())


def cmd_weekly():
    from ai_analyzer import weekly_report
    print("AI 生成周报中...\n")
    print(weekly_report())


def cmd_url(args: list[str]):
    from extractor import ingest_url
    if not args:
        print("用法: python main.py url <URL>")
        return
    url = args[0]
    print(f"正在抓取: {url}\n")
    ok = ingest_url(url)
    if ok:
        print("已入库（自动标签）")
    else:
        print("抓取失败：请确认已安装 trafilatura（pip3 install trafilatura），且 URL 可访问")


def cmd_crawl(args: list[str]):
    from source_manager import list_sources, get_enabled_sources, crawl_all_enabled

    if args and args[0] == "--sources":
        # 列出源
        print("爬虫源清单：\n")
        for s in list_sources():
            status = "[x]" if s.get("enabled", True) else "[ ]"
            print(f"  {status} {s['name']:30s}  {s['type']:12s}  {s['url']}")
        return

    sources = get_enabled_sources()
    if not sources:
        print("没有启用的爬虫源。请先运行 'python main.py sources' 查看，或添加源。")
        return

    print(f"将爬取 {len(sources)} 个源...\n")
    results = crawl_all_enabled()
    for name, n in results.items():
        print(f"  {name}: {'新增 ' + str(n) + ' 条' if n else '无新公告'}")


def cmd_sources(args: list[str]):
    from source_manager import list_sources
    for s in list_sources():
        status = "[x]" if s.get("enabled", True) else "[ ]"
        kw = s.get("keyword", "") or ""
        kw_str = f" (kw={kw})" if kw else ""
        print(f"  {status} {s['name']:30s}  {s['type']:12s}  {s['url']}{kw_str}")


def cmd_source_add(args: list[str]):
    from source_manager import add_source
    if len(args) < 2:
        print("用法: python main.py source-add <名称> <URL> [type:generic/ggzy] [关键词]")
        return
    name = args[0]
    url = args[1]
    stype = args[2] if len(args) > 2 else "generic"
    kw = args[3] if len(args) > 3 else ""
    ok = add_source(name, url, stype, kw)
    print(f"{'已添加' if ok else '已存在或失败'}: {name} ({url})")


def cmd_web():
    from fastapi import FastAPI, Query
    from fastapi.responses import HTMLResponse

    app = FastAPI(title="停车商机雷达", version="0.1.0")

    HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>停车商机雷达</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f5f5;color:#333;line-height:1.6}
.header{background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;padding:24px;text-align:center}
.header h1{font-size:24px;margin-bottom:4px}
.header p{opacity:.7;font-size:14px}
.container{max-width:900px;margin:24px auto;padding:0 16px}
.search-box{display:flex;gap:8px;margin-bottom:20px}
.search-box input{flex:1;padding:12px 16px;border:2px solid #ddd;border-radius:8px;font-size:16px;outline:none}
.search-box input:focus{border-color:#16213e}
.btn{padding:12px 24px;border:none;border-radius:8px;font-size:16px;cursor:pointer;font-weight:600;transition:opacity .2s}
.btn:hover{opacity:.8}
.btn-dark{background:#16213e;color:#fff}
.btn-bid{background:#2c3e50;color:#fff;font-size:13px;padding:6px 14px;border-radius:6px;border:none;cursor:pointer;white-space:nowrap}
.card{background:#fff;border-radius:10px;padding:16px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,0.08);border-left:4px solid #ddd}
.card.high{border-left-color:#e74c3c}
.card.mid{border-left-color:#f39c12}
.card.ref{border-left-color:#95a5a6}
.card-title{font-size:16px;font-weight:600;color:#2c3e50;margin-bottom:6px}
.card-meta{display:flex;gap:12px;flex-wrap:wrap;align-items:center;font-size:13px;color:#666}
.tag{display:inline-block;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600}
.tag-high{background:#fde8e8;color:#c0392b}
.tag-mid{background:#fef3e2;color:#e67e22}
.tag-ref{background:#f0f0f0;color:#7f8c8d}
.tag-bid{background:#d5f5e3;color:#27ae60}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:12px;margin-bottom:20px}
.stat{background:#fff;border-radius:10px;padding:16px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.08)}
.stat-num{font-size:28px;font-weight:700;color:#16213e}
.stat-label{font-size:12px;color:#999;margin-top:2px}
.empty{text-align:center;padding:40px;color:#999}
.modal-overlay{display:none;position:fixed;z-index:1000;left:0;top:0;width:100%;height:100%;background:rgba(0,0,0,.5);overflow-y:auto}
.modal-overlay.show{display:flex;align-items:flex-start;justify-content:center;padding:40px 16px}
.modal{background:#fff;border-radius:12px;max-width:800px;width:100%;padding:32px;box-shadow:0 8px 32px rgba(0,0,0,.2);position:relative}
.modal-close{position:absolute;top:16px;right:20px;font-size:24px;cursor:pointer;color:#999;background:none;border:none}
.modal-close:hover{color:#333}
.modal h1{font-size:20px;margin-bottom:12px}
.modal h2{font-size:16px;color:#16213e;margin:16px 0 8px;padding-bottom:6px;border-bottom:1px solid #eee}
.modal .meta{display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:14px;color:#666;margin-bottom:16px;padding:12px;background:#f8f9fa;border-radius:8px}
.modal .desc{color:#666;font-size:14px;margin:4px 0 8px;padding-left:12px;border-left:3px solid #ddd}
.modal .placeholder-text{color:#b0b0b0;font-size:13px;font-style:italic;margin-bottom:12px}
.modal .warn{background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:12px 16px;font-size:13px;color:#856404;margin:16px 0}
.modal table{width:100%;border-collapse:collapse;font-size:14px;margin:12px 0}
.modal td,.modal th{padding:8px 12px;border:1px solid #e0e0e0;text-align:left}
.modal th{background:#f5f5f5;color:#666}
</style>
</head>
<body>
<div class="header"><h1>停车商机雷达</h1><p>全国公共资源交易平台 · 实时停车项目监控</p></div>
<div class="container">
<div class="search-box">
  <input type="text" id="kw" placeholder="搜索关键词，如：停车、智慧、EPC..." onkeydown="if(event.key==='Enter')doSearch()">
  <button class="btn btn-dark" onclick="doSearch()">搜索</button>
</div>
<div class="stats" id="stats"></div>
<div id="results"><p class="empty">输入关键词开始搜索</p></div>
</div>
<div class="modal-overlay" id="modalOverlay" onclick="if(event.target==this)closeModal()">
<div class="modal" id="modalContent"></div>
</div>
<script>
async function load(){const r=await fetch('/api/stats');const d=await r.json();
document.getElementById('stats').innerHTML=
  '<div class="stat"><div class="stat-num">'+d.total+'</div><div class="stat-label">总商机</div></div>'+
  '<div class="stat"><div class="stat-num" style="color:#27ae60">'+d.can_bid+'</div><div class="stat-label">可投标</div></div>'+
  '<div class="stat"><div class="stat-num" style="color:#e74c3c">'+d.high_priority+'</div><div class="stat-label">高优</div></div>'}
function openBid(id,t){
document.getElementById('modalOverlay').classList.add('show');
document.getElementById('modalContent').innerHTML='<p style="text-align:center;padding:40px;">正在生成标书骨架...</p>';
fetch('/api/bid/'+id).then(r=>r.text()).then(h=>{document.getElementById('modalContent').innerHTML=h})}
function closeModal(){document.getElementById('modalOverlay').classList.remove('show')}
async function doSearch(){
  const kw=document.getElementById('kw').value||'停车';
  const r=await fetch('/api/search?kw='+encodeURIComponent(kw));
  const items=await r.json();
  const div=document.getElementById('results');
  if(!items.length){div.innerHTML='<p class="empty">没有匹配结果</p>';return}
  div.innerHTML=items.map(i=>{
    const pc=i.priority==='高优'?'high':i.priority==='中优'?'mid':'ref';
    const bt=i.can_bid?' <span class="tag tag-bid">可投</span>':'';
    const t=i.title.replace(/ /g,'').replace(/'/g,"\\'");
    const r=(i.region||'').replace(/ /g,'');
    return '<div class="card '+pc+'">'+
      '<div class="card-title">'+i.title.replace(/ /g,'')+'</div>'+
      '<div class="card-meta">'+
        '<span class="tag tag-'+pc+'">'+i.priority+'</span>'+bt+
        '<span> '+r+'</span><span> '+i.notice_type+'</span>'+
        '<span> '+i.pub_date+'</span><span> '+i.score+'分</span>'+
        '<button class="btn btn-bid" onclick="openBid('+i.id+',\''+t+'\')">生成标书</button>'+
      '</div></div>'
  }).join('')}
load();doSearch();
</script>
</body></html>"""

    from db import get_db, search as db_search
    from bid_writer import BID_TEMPLATE
    from datetime import datetime

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return HTML

    @app.get("/api/stats")
    async def api_stats():
        from db import get_stats
        return get_stats()

    @app.get("/api/search")
    async def api_search(kw: str = Query(default="停车")):
        from search import search as do_search
        return do_search(kw)

    @app.get("/api/bid/{nid}")
    async def api_bid(nid: int):
        from db import get_notice_by_id
        from bid_writer import BID_TEMPLATE
        row = get_notice_by_id(nid)
        if not row:
            return HTMLResponse("<h2>商机不存在</h2>", status_code=404)

        r = dict(row)
        title = (r.get("title") or "").replace(" ", "")
        budget = r.get("budget", "—") or "—"
        region = (r.get("region") or "—").replace(" ", "")
        pub_date = r.get("pub_date", "—") or "—"
        notice_type = r.get("notice_type", "—") or "—"

        chapters_html = ""
        for num, ctitle, desc in BID_TEMPLATE:
            if "项目概述" in ctitle:
                desc_text = f"{title}，位于{region}地区，{'预算' + budget if budget != '—' else '预算待核实'}。本期招标类型为{notice_type}。"
            elif "技术方案" in ctitle:
                desc_text = f"针对{title}的技术需求，本章详细阐述各子系统设计方案及技术指标。[实际方案需根据招标文件技术要求填写]"
            elif "施工" in ctitle:
                desc_text = "本项目施工总体部署及分阶段计划。[实际施工方案需根据现场踏勘及工程量清单编制]"
            elif "团队" in ctitle:
                desc_text = "本项目拟投入的组织架构及关键岗位人员配置。[实际人员信息、资质证书编号需人工填写]"
            else:
                desc_text = "[本章内容需根据招标文件具体要求及企业实际情况填写]"

            chapters_html += f"""
            <h2>{num}、{ctitle}</h2>
            <p class="desc">{desc_text}</p>
            <p class="placeholder-text">[本章内容省略，实际编写时需展开]</p>
            <hr style="border:none;border-top:1px solid #eee;margin:12px 0">"""

        now = datetime.now().strftime('%Y-%m-%d %H:%M')

        html = f"""<button class="modal-close" onclick="closeModal()">&times;</button>
<h1>投标文件（技术标）</h1>
<div class="meta">
  <div><strong>项目名称：</strong>{title}</div>
  <div><strong>招标类型：</strong>{notice_type}</div>
  <div><strong>项目地区：</strong>{region}</div>
  <div><strong>预算金额：</strong>{budget}</div>
  <div><strong>发布日期：</strong>{pub_date}</div>
  <div><strong>生成时间：</strong>{now}</div>
</div>
<div class="warn">本文件为 AI 初稿骨架，<b>黑色标注内容必须人工核实</b>。报价、签章、资质原件必须人工提供。</div>
{chapters_html}
<h2>审核清单（提交前必须完成）</h2>
<table>
<tr><th>#</th><th>检查项</th><th>状态</th></tr>
<tr><td>1</td><td>投标函/法人授权书已签章</td><td> </td></tr>
<tr><td>2</td><td>营业执照/资质证书扫描件已附</td><td> </td></tr>
<tr><td>3</td><td>业绩证明材料已核实</td><td> </td></tr>
<tr><td>4</td><td>投标报价已人工填写</td><td> </td></tr>
<tr><td>5</td><td>关键技术人员资质证书已验证</td><td> </td></tr>
<tr><td>6</td><td>技术参数/指标已核实无AI幻觉</td><td> </td></tr>
<tr><td>7</td><td>页码/目录/密封符合招标文件要求</td><td> </td></tr>
<tr><td>8</td><td>投标保证金/保函已办理</td><td> </td></tr>
</table>
<div class="warn"><b>法律风险提示：</b>《招标投标法》第54条——虚构投标材料属违法行为。本初稿仅供内部起草参考，终稿须经人工逐项审核。</div>
"""
        return HTMLResponse(html)

    import uvicorn
    print("商机看板: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


def cmd_gui():
    from desktop import main as desktop_main
    desktop_main()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]
    args = sys.argv[2:]

    # 首次运行自动建库（如果还没建）
    cmd_needs_db = cmd in ("search", "report", "bid", "ask", "analyze", "rank", "weekly", "web", "gui", "crawl")
    if cmd_needs_db and not os.path.exists(DB_PATH):
        print("首次运行，正在初始化数据库...")
        from db import init_database, seed_data
        init_database()
        seed_data()

    routes = {
        "initdb": cmd_initdb,
        "seed": cmd_seed,
        "search": lambda: cmd_search(args),
        "report": cmd_report,
        "bid": lambda: cmd_bid(args),
        "ask": lambda: cmd_ask(args),
        "analyze": lambda: cmd_analyze(args),
        "crawl": lambda: cmd_crawl(args),
        "sources": lambda: cmd_sources(args),
        "source-add": lambda: cmd_source_add(args),
        "url": lambda: cmd_url(args),
        "rank": cmd_rank,
        "weekly": cmd_weekly,
        "web": cmd_web,
        "gui": cmd_gui,
    }

    if cmd in routes:
        routes[cmd]()
    else:
        print(f"未知命令: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
