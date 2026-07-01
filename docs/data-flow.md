# 项目数据流拆解

> 2026-06-20 — 把整个 bid_tool 从头到尾拆开讲明白

---

## 总览：三条数据流

```
① 数据怎么进来
   ggzy爬虫 / 手动URL抓取 / 种子数据
         ↓
② 数据怎么存、怎么加工
   SQLite + FTS5 全文索引 + tagger 自动标签
         ↓
③ 数据怎么用
   tkinter桌面 / CLI命令行 / FastAPI网页

同一堆数据，三个出口。没有服务器，没有网络协议 — 全部是本机 Python 函数调用。
```

---

## 一、数据入口：三条管道

### 管道A — ggzy 爬虫自动采集

```
用户操作                       代码路径                         数据形态
─────────────────────────────────────────────────────────────────────
桌面点「爬取最新」    →  desktop._do_crawl()              →  线程启动
                         → source_manager.crawl_all_enabled()
                         → crawlers.ggzy.GgzyCrawler.crawl()
                            ├── requests.get(ggzy首页)         →  首页HTML
                            ├── 正则提取24个 a 链接           →  list[URL]
                            ├── 逐个请求 a 页                  →  详情页HTML
                            ├── _parse_detail 提取字段          →  dict
                            └── _log() 写入实时日志窗口
                         → db.insert_notice(dict, auto_tag=True)
                            └── tagger.tag_and_merge()          →  打标签
                            └── INSERT INTO notices             →  SQLite行
```

**每一个环节都是函数调用，不是网络请求。爬虫就是 Python 发 HTTP 请求，拿到 HTML 用正则提取字段。**

### 管道B — 手动URL抓取 (trafilatura)

```
桌面输入URL后回车   →  desktop._do_fetch_url()               →  线程启动
                      → extractor.ingest_url(url)
                         ├── trafilatura.fetch_url(url)        →  HTML
                         ├── trafilatura.bare_extraction()     →  纯文本
                         ├── 正则提取标题/日期/站点
                         └── 构造成 notice dict
                      → db.insert_notice(dict, auto_tag=True)
                         └── tagger.tag_and_merge()            →  打标签
                         └── INSERT INTO notices               →  SQLite行
```

**trafilatura 是通用网页正文提取库，不需要针对网站写规则。一个函数调用抠出正文。**

### 管道C — 种子数据（硬编码在 db.py 里）

```
python main.py seed  →  db.seed_data()
                         └── 10条写死的 SEED_NOTICES 列表
                         └── jieba 分词后 INSERT
```

**跟爬虫回来的数据走到同一个数据库、同样的表结构。没有区别对待。**

---

## 二、数据存储：SQLite 就是一切

### 一张表、一个虚拟表

```
notices (主表, 16列)
┌────┬──────┬──────────┬──────┬────────────┬─────┬────────┐
│ id │source│  title   │region│notice_type │score│content │
├────┼──────┼──────────┼──────┼────────────┼─────┼────────┤
│  1 │ ggzy │ 绵阳城市..│ 四川 │ 招标公告   │ 100 │ EPC总.. │
│  2 │ ggzy │ 首都医科..│ 北京 │ 招标公告   │  95 │ 施工翻.. │
└────┴──────┴──────────┴──────┴────────────┴─────┴────────┘

notices_fts (虚拟表, FTS5全文索引)
  自动从 notices 同步 title/content/publisher/region/biz_type
  触发器负责同步: INSERT/UPDATE/DELETE on notices → 自动更新 fts
```

### 连接方式

```
db.get_db()  →  sqlite3.connect("data/bid.db")
                  └── row_factory = sqlite3.Row  (返回类dict对象)
                  └── journal_mode = WAL         (读写不互斥)
                  └── foreign_keys = ON
```

**整个项目只有一个数据库文件 `data/bid.db`。所有模块都通过 `db.get_db()` 获取连接。**

### 为什么不用 MySQL/PostgreSQL/Elasticsearch？

- 这是个人桌面工具，不部署服务器
- SQLite 零配置、零运维，一个文件就是全部数据
- FTS5 全文索引对几千条数据足够快，jieba 分词补上中文搜索
- 商业产品用 ES 是因为百万级数据量，个人工具不需要

---

## 三、数据加工：tagger 自动标签

### 触发点

**任何数据入库都走 `insert_notice(dict, auto_tag=True)`。默认自动打标签。**

```
insert_notice(notice) 
    │
    ├── auto_tag=True ─→ tagger.tag_and_merge(notice)
    │                       ├── auto_tag()  提取优先级/可投/阶段/评分
    │                       └── _normalize_region()  规范地区名
    │
    ├── jieba.cut(title/content/publisher/...)  中文分词
    │
    └── INSERT INTO notices → FTS5触发器自动同步
```

### 标签规则（纯Python，不调AI）

```
notice_type = "招标公告"  →  priority="高优"  can_bid=1
notice_type = "中标公示"  →  priority="中优"  can_bid=0
notice_type = "更正公告"  →  priority="参考"  can_bid=0

标题含 "EPC"或"总承包"  →  stage="总包"  评分+15
标题含 "监理"           →  stage="监理"
标题含 "施工/建设/改造"  →  stage="施工"

预算 > 5000万  →  评分+10
预算 > 1000万  →  评分+7
```

**没有 AI 调用。规则引擎，毫秒出结果。**

---

## 四、数据出口：三个前端共一个后端

### 出口A — tkinter 桌面端

```
desktop.py (759行, 45个方法)
    │
    ├─ Tab1 商机看板
    │   ├── refresh_data() → search_filtered() 或 get_all_notices()
    │   │                     → 内存过滤(地区/类型/优先级/日期/可投)
    │   │                     → 内存排序(点列头)
    │   │                     → populate_tree() 渲染到 Treeview
    │   ├── 爬取最新 → source_manager.crawl_all_enabled()
    │   ├── 抓取URL → extractor.ingest_url()
    │   └── 管理源 → source_manager 增删查
    │
    ├─ Tab2 标书生成
    │   ├── 模板模式 → bid_writer.gen_bid_template(id) → Markdown
    │   └── AI模式   → bid_writer.gen_bid_ai(id)       → DeepSeek API
    │
    ├─ Tab3 AI分析
    │   ├── 深度分析 → ai_analyzer.analyze_one(id)
    │   ├── 排名     → ai_analyzer.rank_opportunities()
    │   ├── 周报     → ai_analyzer.weekly_report()
    │   └── 自由提问 → ai_analyzer.ask(question)
    │
    └─ 状态栏 → db.get_stats()
```

**desktop.py 只是壳。它自己不写任何业务逻辑。所有操作都是调后端函数。**

### 出口B — CLI 命令行

```
main.py (416行)
    │
    ├── python main.py search 停车 → search.search("停车") → print
    ├── python main.py bid 7       → bid_writer.gen_bid_template(7) → print
    ├── python main.py report      → report.gen_report() → print
    ├── python main.py crawl       → source_manager.crawl_all_enabled()
    ├── python main.py sources     → source_manager.list_sources()
    ├── python main.py url <URL>   → extractor.ingest_url(URL)
    ├── python main.py ask "..."   → ai_analyzer.ask("...")
    ├── python main.py gui         → desktop.main()
    └── python main.py web         → FastAPI+uvicorn → 浏览器
```

**main.py 是选择器。根据命令分发到对应函数。不写业务。**

### 出口C — FastAPI 网页（临时验证用）

```
main.py cmd_web()  → 内嵌在文件里，约150行
    │
    ├── HTML 页面（内联CSS/JS，单文件）
    ├── GET  /       → 返回 HTML
    ├── GET  /api/stats   → db.get_stats()
    ├── GET  /api/search?kw=  → search.search(kw)
    └── GET  /api/bid/<id>    → 生成标书HTML
```

**这个是当时验证用的，现在还嵌在 main.py 里。架构上应该拆到 web/ 目录。**

---

## 五、AI 调用链路

### DeepSeek（兼容 OpenAI SDK）

```
ai_analyzer.ask(question)
    │
    ├── db.get_all_notices(50)                  → 取全部商机
    ├── _notices_to_text(notices)               → 转成AI可读文本
    ├── db.get_stats()                          → 统计信息
    │
    └── openai.OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com"
        ).chat.completions.create(
            model="deepseek-chat",
            messages=[system_prompt, user_question],
            max_tokens=4096
        )
        → 返回 AI 生成的文本
        → 直接显示在 GUI 输出区／CLI 终端
```

### 标书 AI 模式

```
bid_writer.gen_bid_ai(notice_id)
    │
    ├── db.get_notice_by_id(id)                 → 取单条商机
    ├── load_knowledge_context()                → 读取 knowledge/ 所有文件
    │   ├── company.yml → yaml.safe_load()
    │   ├── projects.yml → yaml.safe_load()
    │   ├── team.yml → yaml.safe_load()
    │   ├── terms.json → json.load()
    │   └── solutions/*.md → open().read()
    │
    └── DeepSeek API(
            system_prompt = 知识库内容 + 8章模板要求,
            user_prompt   = 商机具体信息,
            max_tokens    = 8192
        )
        → 返回完整标书 Markdown
```

**AI 不存数据库，每次调用都是实时请求。需要 DeepSeek API Key。**

---

## 六、不涉及的东西

| 没有的 | 原因 |
|--------|------|
| 后端服务器 | 不需要。纯桌面客户端，所有逻辑在进程内完成 |
| HTTP API | 除了 FastAPI Web 验证端口外，模块之间不走 HTTP |
| 数据库连接池 | SQLite 单连接够用 |
| 消息队列 | 单机、单用户，不需要 |
| 缓存层 | 数据量小，每次 SQL 查询已经够快 |
| 前后端分离 | tkinter 就是前端，它直接调 Python 函数 |

---

## 七、一个请求的全链路

```
用户双击表格行"绵阳EPC项目" → 跳标书Tab → 点生成标书
    │
    ├─ desktop._on_tree_double_click()
    │   └─ notebook.select(1) 切Tab
    │
    ├─ desktop._gen_bid()
    │   └─ thread → bid_writer.gen_bid_template(7)
    │       ├─ db.get_notice_by_id(7) 
    │       │   └─ sqlite3 → "SELECT * FROM notices WHERE id=7"
    │       │   → dict{title, region, budget, ...}
    │       │
    │       ├─ 填充 BID_TEMPLATE (8 章)
    │       │   ├─ 第1章：用真实 title/region/budget
    │       │   └─ 第2-8章：占位符文本
    │       │
    │       └─ return Markdown 字符串
    │
    ├─ root.after(0, callback)  →  切回主线程
    │   └─ bid_preview.insert(END, markdown_text)
    │
    └─ 用户看到标书，点「导出.md」→ 写文件
```

**从头到尾：一次 SQL 查询 + 一个字符串拼接。没有网络请求。**

AI 模式的话跟上面一样，只是中间加一步 DeepSeek HTTP 调用。模板模式完全是本地毫秒完成。

---

## 八、架构一句话

```
三个入口（GUI/CLI/Web）
    ↓ 纯 Python 函数调用
九个模块（db/search/tagger/extractor/bid_writer/ai_analyzer/report/source_manager/crawlers）
    ↓ sqlite3.connect
一个数据库文件 data/bid.db
```

**没有中间件、没有消息队列、没有 API 网关、没有序列化/反序列化。所有数据传输都是直接的 Python dict/str 传递。**
