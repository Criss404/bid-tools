#!/usr/bin/env python3
"""招投标信息工具 — Web 版
启动: python3 web_app.py  →  http://localhost:8000
"""

import os, sys, io, csv
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
import uvicorn

app = FastAPI(title="招投标信息工具", version="1.0")

# ── HTML ──

HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>招投标信息工具</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Noto Sans CJK SC',sans-serif;background:#f5f7fa;color:#333;line-height:1.6}
.hd{background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;padding:14px 20px;font-size:18px;font-weight:600}
.hd span{opacity:.6;font-size:12px;margin-left:10px}
.stats{display:flex;gap:12px;padding:16px 20px;flex-wrap:wrap}
.stats div{background:#fff;border-radius:8px;padding:16px 24px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.stats .n{font-size:26px;font-weight:700;color:#1a73e8}
.stats .l{font-size:12px;color:#888}
.card{background:#fff;border-radius:8px;padding:16px;margin:0 20px 12px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:8px}
.row input,.row select,.row button{font-size:13px;padding:7px 10px;border:1px solid #ddd;border-radius:6px;outline:none;font-family:inherit}
.row input:focus,.row select:focus{border-color:#1a73e8}
.row button{cursor:pointer;font-weight:600;border:none;background:#1a73e8;color:#fff;transition:.2s}
.row button:hover{opacity:.85}
.row button.red{background:#e53935}
.row button.gray{background:#555}
.row input[type=text]{flex:1;min-width:150px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:7px 8px;text-align:left;border-bottom:1px solid #eee;white-space:nowrap}
th{background:#fafafa;color:#888;font-weight:600;cursor:pointer}
th:hover{color:#1a73e8}
tr:hover{background:#f8f9ff}
.bg-A{display:inline-block;padding:1px 6px;border-radius:3px;font-size:11px;font-weight:600;background:#fde8e8;color:#c0392b}
.bg-B{display:inline-block;padding:1px 6px;border-radius:3px;font-size:11px;font-weight:600;background:#fef3e2;color:#e67e22}
.bg-C{display:inline-block;padding:1px 6px;border-radius:3px;font-size:11px;font-weight:600;background:#f0f0f0;color:#999}
.bg-bid{display:inline-block;padding:1px 6px;border-radius:3px;font-size:11px;font-weight:600;background:#d5f5e3;color:#27ae60}
.prewrap{background:#1e1e1e;color:#e0e0e0;font-family:monospace;font-size:12px;padding:12px;border-radius:8px;max-height:300px;overflow-y:auto;white-space:pre-wrap}
.preview{background:#fff;border:1px solid #ddd;border-radius:8px;padding:16px;max-height:400px;overflow-y:auto;font-size:13px;white-space:pre-wrap;font-family:monospace}
.empty{text-align:center;padding:30px;color:#999}
.toast{position:fixed;top:10px;right:10px;background:#333;color:#fff;padding:8px 16px;border-radius:6px;font-size:13px;z-index:999;display:none}
.btn-sm{font-size:11px!important;padding:2px 6px!important;border-radius:3px!important}
@media(max-width:700px){.row{flex-direction:column}.row input{width:100%}}
</style>
</head>
<body>

<div class="hd">招投标信息工具 <span>实时标讯监控</span></div>

<div class="stats" id="stats">
  <div><div class="n" id="st-total">-</div><div class="l">总标讯</div></div>
  <div><div class="n" id="st-bid" style="color:#27ae60">-</div><div class="l">可参与</div></div>
  <div><div class="n" id="st-high" style="color:#e53935">-</div><div class="l">A级</div></div>
</div>

<!-- 搜索筛选 -->
<div class="card">
  <div class="row">
    <input type="text" id="kw" placeholder="搜索关键词...">
    <select id="f-reg"></select>
    <select id="f-type"></select>
    <select id="f-pri"></select>
    <label style="font-size:13px;white-space:nowrap"><input type="checkbox" id="f-bid"> 可参与</label>
    <input type="date" id="f-from" style="width:120px">
    <input type="date" id="f-to" style="width:120px">
    <button onclick="doSearch()">搜索</button>
    <button onclick="resetAll()" class="gray">重置</button>
    <button onclick="doExport()" class="gray">导出CSV</button>
  </div>
  <div style="overflow-x:auto">
    <table><thead><tr>
      <th onclick="doSort('id')">ID</th><th onclick="doSort('title')">标题</th>
      <th onclick="doSort('notice_type')">类型</th><th onclick="doSort('region')">地区</th>
      <th onclick="doSort('pub_date')">日期</th><th onclick="doSort('priority')">级别</th>
      <th onclick="doSort('score')">评分</th><th>操作</th>
    </tr></thead><tbody id="tbl"><tr><td colspan="8" class="empty">加载中...</td></tr></tbody></table>
  </div>
</div>

<!-- 标书 -->
<div class="card">
  <div style="font-weight:600;margin-bottom:8px">标书生成</div>
  <div class="row">
    <span style="font-size:13px">ID:</span><input type="text" id="bid-id" style="width:60px" placeholder="如 7">
    <span style="font-size:13px">标题:</span><input type="text" id="bid-title" style="flex:1" readonly>
    <select id="bid-mode"><option value="template">模板</option><option value="ai">AI</option></select>
    <button onclick="doGenBid()">生成标书</button>
    <button onclick="doExportBid()" class="gray">导出.md</button>
  </div>
  <div class="preview" id="bid-preview">选中一行点「生成标书」后填入ID和标题</div>
</div>

<!-- AI -->
<div class="card">
  <div style="font-weight:600;margin-bottom:8px">AI 分析</div>
  <div class="row">
    <button onclick="doAiAnalyze()">深度分析</button>
    <button onclick="doAiRank()">排名推荐</button>
    <button onclick="doAiWeekly()">生成周报</button>
    <input type="text" id="ai-id" style="width:80px" placeholder="标讯ID">
    <input type="text" id="ai-q" style="flex:1" placeholder="自由提问...">
    <button onclick="doAiAsk()">提问</button>
  </div>
  <div class="prewrap" id="ai-out">结果将显示在这里</div>
</div>

<!-- 爬取 -->
<div class="card">
  <div style="font-weight:600;margin-bottom:8px">爬取管理</div>
  <div class="row">
    <button onclick="doCrawl()">爬取最新</button>
    <input type="text" id="sn" placeholder="源名称" style="width:150px">
    <input type="text" id="su" placeholder="URL (https://)" style="flex:1">
    <select id="st"><option value="ggzy">ggzy</option><option value="cebpubservice">cebpub</option><option value="single">单页</option></select>
    <button onclick="doAddSrc()">添加源</button>
  </div>
  <div class="prewrap" id="clog">点击「爬取最新」开始</div>
  <div id="slist" style="margin-top:8px;font-size:12px"></div>
</div>

<div class="toast" id="toast"></div>

<script>
var sortCol='score',sortRev=true,allData=[];

function G(id){return document.getElementById(id)}
function toast(msg){var t=G('toast');t.textContent=msg;t.style.display='block';setTimeout(function(){t.style.display='none'},2500)}

// ── 搜索 ──
function doSearch(){
  var p=[],kw=G('kw').value.trim(),rg=G('f-reg').value,tp=G('f-type').value,pr=G('f-pri').value;
  if(kw)p.push('kw='+encodeURIComponent(kw));
  if(rg)p.push('region='+encodeURIComponent(rg));
  if(tp)p.push('type='+encodeURIComponent(tp));
  if(pr)p.push('priority='+encodeURIComponent(pr));
  if(G('f-bid').checked)p.push('bid_only=1');
  if(G('f-from').value)p.push('date_from='+G('f-from').value);
  if(G('f-to').value)p.push('date_to='+G('f-to').value);
  var qs=p.length?'?'+p.join('&'):'';
  fetch('/api/search'+qs).then(function(r){return r.json()}).then(function(rows){
    allData=rows; doRender();
  }).catch(function(e){console.error(e);toast('搜索失败')});
}

function doRender(){
  var pc={'A级':'A','B级':'B','C级':'C'};
  var hk={id:'id',title:'title',notice_type:'notice_type',region:'region',pub_date:'pub_date',priority:'priority',score:'score'};
  var k=hk[sortCol]||sortCol;
  allData.sort(function(a,b){
    var va=(a[k]||''),vb=(b[k]||'');
    if(k=='score'){va=+a.score||0;vb=+b.score||0}
    if(k=='id'){va=+a.id||0;vb=+b.id||0}
    return (va<vb?1:va>vb?-1:0)*(sortRev?1:-1);
  });
  var h='';
  for(var i=0;i<allData.length;i++){
    var r=allData[i],pcls=pc[r.priority]||'C';
    var t=(r.title||'').replace(/ /g,''),rg=(r.region||'').replace(/ /g,'');
    var btag=r.can_bid?'<span class="bg-bid">可参与</span>':'';
    h+='<tr><td>'+r.id+'</td><td style="max-width:260px;overflow:hidden;text-overflow:ellipsis">'+t+'</td><td>'+(r.notice_type||'')+'</td><td>'+rg+'</td><td>'+(r.pub_date||'')+'</td><td><span class="bg-'+pcls+'">'+(r.priority||'')+'</span></td><td>'+Math.round(r.score||0)+'</td><td>'+btag+' <button class="btn-sm" style="background:#1a73e8;color:#fff;border:none" onclick="doPick('+r.id+',\''+t.replace(/'/g,"\\'")+'\')">标书</button> <button class="btn-sm" style="background:#e53935;color:#fff;border:none" onclick="doDel('+r.id+')">删</button></td></tr>';
  }
  G('tbl').innerHTML=h||'<tr><td colspan="8" class="empty">无结果</td></tr>';
}

function doSort(col){if(sortCol==col)sortRev=!sortRev;else{sortCol=col;sortRev=false}doRender()}
function resetAll(){['kw','f-reg','f-type','f-pri','f-from','f-to'].forEach(function(id){G(id).value=''});G('f-bid').checked=false;doSearch()}
function doExport(){window.open('/api/export?kw='+encodeURIComponent(G('kw').value),'_blank')}
function doDel(id){if(!confirm('删除 ID='+id+'?'))return;fetch('/api/notices/'+id,{method:'DELETE'}).then(function(){doSearch();doStats()})}

// ── 标书 ──
function doPick(id,title){G('bid-id').value=id;G('bid-title').value=title;G('bid-preview').scrollIntoView({behavior:'smooth'})}
function doGenBid(){
  var id=G('bid-id').value.trim();if(!id)return toast('请先选标讯');
  G('bid-preview').textContent='生成中...';
  fetch('/api/bid/'+id+'?mode='+G('bid-mode').value).then(function(r){return r.text()}).then(function(t){G('bid-preview').textContent=t}).catch(function(e){G('bid-preview').textContent='失败: '+e});
}
function doExportBid(){
  var t=G('bid-preview').textContent;if(!t)return;
  var a=document.createElement('a');a.href=URL.createObjectURL(new Blob([t]));a.download='标书_'+new Date().toISOString().slice(0,10)+'.md';a.click();
}

// ── AI ──
function doAiAnalyze(){var id=G('ai-id').value.trim();if(!id)return toast('请输入标讯ID');G('ai-out').textContent='分析中...';fetch('/api/ai/analyze/'+id).then(function(r){return r.text()}).then(function(t){G('ai-out').textContent=t}).catch(function(e){G('ai-out').textContent='失败: '+e})}
function doAiRank(){G('ai-out').textContent='排名中...';fetch('/api/ai/rank').then(function(r){return r.text()}).then(function(t){G('ai-out').textContent=t}).catch(function(e){G('ai-out').textContent='失败: '+e})}
function doAiWeekly(){G('ai-out').textContent='生成中...';fetch('/api/ai/weekly').then(function(r){return r.text()}).then(function(t){G('ai-out').textContent=t}).catch(function(e){G('ai-out').textContent='失败: '+e})}
function doAiAsk(){var q=G('ai-q').value.trim();if(!q)return toast('请输入问题');G('ai-out').textContent='思考中...';fetch('/api/ai/ask?q='+encodeURIComponent(q)).then(function(r){return r.text()}).then(function(t){G('ai-out').textContent=t}).catch(function(e){G('ai-out').textContent='失败: '+e})}

// ── 爬取 ──
function doCrawl(){var l=G('clog');l.textContent='爬取中...\n';fetch('/api/crawl',{method:'POST'}).then(function(r){return r.json()}).then(function(d){var s='';Object.keys(d.results||{}).forEach(function(k){s+='  '+k+': '+d.results[k]+' 条\n'});l.textContent+=s+'\n完成';doStats();doSearch()}).catch(function(e){l.textContent+='失败: '+e})}
function doLoadSrcs(){fetch('/api/sources').then(function(r){return r.json()}).then(function(s){var h='';s.forEach(function(x){h+='<div style="padding:4px 0;border-bottom:1px solid #eee;font-size:12px"><span onclick="doToggleSrc(\''+x.url+'\')" style="cursor:pointer;padding:0 4px">'+(x.enabled?'[x]':'[ ]')+'</span> '+x.name+' <code>'+x.url+'</code> <span class="bg-C">'+x.type+'</span> <span onclick="doDelSrc(\''+x.url+'\')" style="color:#e53935;cursor:pointer">删</span></div>'});G('slist').innerHTML=h})}
function doAddSrc(){var n=G('sn').value.trim(),u=G('su').value.trim(),t=G('st').value;if(!n||!u)return toast('名称和URL必填');fetch('/api/sources',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n,url:u,type:t})}).then(function(){G('sn').value='';G('su').value='';doLoadSrcs();toast('已添加')})}
function doToggleSrc(url){fetch('/api/sources/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:url})}).then(doLoadSrcs)}
function doDelSrc(url){if(!confirm('删除?'))return;fetch('/api/sources',{method:'DELETE',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:url})}).then(doLoadSrcs)}

// ── 启动 ──
function doStats(){
  fetch('/api/stats').then(function(r){return r.json()}).then(function(d){
    G('st-total').textContent=d.total;G('st-bid').textContent=d.can_bid;G('st-high').textContent=d.high_priority;
  });
}
fetch('/api/filters').then(function(r){return r.json()}).then(function(f){
  [{id:'f-reg',k:'region',l:'地区'},{id:'f-type',k:'type',l:'类型'},{id:'f-pri',k:'priority',l:'级别'}].forEach(function(x){
    var s=G(x.id);s.innerHTML='<option value="">全部'+x.l+'</option>';
    (f[x.k]||[]).forEach(function(v){s.innerHTML+='<option>'+v+'</option>'});
  });
});
doStats();doSearch();doLoadSrcs();
</script>
</body></html>"""

# ── API ──

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(content=HTML)

@app.get("/api/stats")
async def api_stats():
    from db import get_stats
    return get_stats()

@app.get("/api/filters")
async def api_filters():
    from db import get_db
    conn = get_db()
    regions = [r[0].replace(" ","") for r in conn.execute(
        "SELECT DISTINCT region FROM notices WHERE region NOT IN ('','—','-') ORDER BY region").fetchall()]
    types = [t[0] for t in conn.execute(
        "SELECT DISTINCT notice_type FROM notices WHERE notice_type != '' ORDER BY notice_type").fetchall()]
    priorities = [p[0] for p in conn.execute(
        "SELECT DISTINCT priority FROM notices ORDER BY priority").fetchall()]
    conn.close()
    return {"region": sorted(set(regions)), "type": types, "priority": priorities}

@app.get("/api/search")
async def api_search(kw: str = "", region: str = "", type: str = "",
                      priority: str = "", bid_only: str = "",
                      date_from: str = "", date_to: str = ""):
    from db import get_all_notices
    from search import search_filtered
    rows = search_filtered(kw, region=region, notice_type=type) if kw else get_all_notices()
    filtered = []
    for r in [dict(x) for x in rows]:
        if type and r.get("notice_type","") != type: continue
        if priority and r.get("priority","") != priority: continue
        if bid_only == "1" and not r.get("can_bid"): continue
        pd = r.get("pub_date","") or ""
        if date_from and pd < date_from: continue
        if date_to and pd > date_to: continue
        filtered.append(r)
    return filtered

@app.get("/api/export")
async def api_export(kw: str = "", region: str = "", type: str = "",
                     priority: str = "", bid_only: str = "",
                     date_from: str = "", date_to: str = ""):
    data = await api_search(kw, region, type, priority, bid_only, date_from, date_to)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["ID","标题","类型","地区","日期","级别","评分","可参与"])
    for r in data:
        w.writerow([r.get("id"),(r.get("title","") or "").replace(" ",""),
                     r.get("notice_type",""),(r.get("region","") or "").replace(" ",""),
                     r.get("pub_date",""),r.get("priority",""),
                     f"{r.get('score',0):.0f}","Y" if r.get("can_bid") else ""])
    out.seek(0)
    return StreamingResponse(out, media_type="text/csv",
        headers={"Content-Disposition": f"attachment;filename=export_{datetime.now().strftime('%Y%m%d')}.csv"})

@app.get("/api/bid/{nid}")
async def api_bid(nid: int, mode: str = "template"):
    if mode == "ai":
        from bid_writer import gen_bid_ai
        return HTMLResponse(f"<pre style='white-space:pre-wrap;font:13px monospace'>{gen_bid_ai(nid)}</pre>")
    from bid_writer import gen_bid_template
    return HTMLResponse(f"<pre style='white-space:pre-wrap;font:13px monospace'>{gen_bid_template(nid)}</pre>")

@app.get("/api/ai/analyze/{nid}")
async def api_ai_analyze(nid: int):
    from ai_analyzer import analyze_one
    return HTMLResponse(analyze_one(nid))

@app.get("/api/ai/rank")
async def api_ai_rank():
    from ai_analyzer import rank_opportunities
    return HTMLResponse(rank_opportunities())

@app.get("/api/ai/weekly")
async def api_ai_weekly():
    from ai_analyzer import weekly_report
    return HTMLResponse(weekly_report())

@app.get("/api/ai/ask")
async def api_ai_ask(q: str = ""):
    if not q: return HTMLResponse("问题不能为空", status_code=400)
    from ai_analyzer import ask
    return HTMLResponse(ask(q))

@app.post("/api/crawl")
async def api_crawl():
    from source_manager import crawl_all_enabled
    return {"results": crawl_all_enabled()}

@app.get("/api/sources")
async def api_list_sources():
    from source_manager import list_sources, get_enabled_sources
    enabled_urls = {s['url'] for s in get_enabled_sources()}
    return [{**s, "enabled": s.get("url") in enabled_urls} for s in list_sources()]

@app.post("/api/sources")
async def api_add_source(req: Request):
    body = await req.json()
    from source_manager import add_source
    return {"ok": add_source(body.get("name",""), body.get("url",""), body.get("type","single"))}

@app.delete("/api/sources")
async def api_del_source(req: Request):
    body = await req.json()
    from source_manager import remove_source
    return {"ok": remove_source(body.get("url",""))}

@app.post("/api/sources/toggle")
async def api_toggle_source(req: Request):
    body = await req.json()
    from source_manager import toggle_source
    return {"enabled": toggle_source(body.get("url",""))}

@app.delete("/api/notices/{nid}")
async def api_delete_notice(nid: int):
    from db import delete_notice
    return {"ok": delete_notice(nid)}

if __name__ == "__main__":
    from config import DB_PATH, USER_DIR
    import shutil
    os.makedirs(os.path.join(USER_DIR, "data"), exist_ok=True)
    if not os.path.exists(DB_PATH):
        print("首次运行，正在初始化数据库...")
        from db import init_database, seed_data
        init_database(); seed_data()
    print("招投标信息工具 - Web版")
    print("本地: http://localhost:8000")
    print("内网: http://192.168.88.222:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
