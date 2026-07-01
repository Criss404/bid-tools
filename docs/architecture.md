# bid_tool 架构梳理

> 2026-06-20 — 基于实际代码分析

---

## 一、当前目录结构

```
bid_tool/                         (项目根)
├── 入口层
│   ├── main.py          416行  CLI入口 + 内嵌FastAPI Web (耦合过重)
│   └── desktop.py       759行  tkinter桌面  (45个方法，太胖)
│
├── 业务层
│   ├── search.py         57行  FTS5全文搜索
│   ├── bid_writer.py    243行  标书生成 (模板+AI)
│   ├── ai_analyzer.py   186行  AI分析 (提问/深度/排名/周报)
│   └── report.py         78行  分析报告
│
├── 数据层
│   ├── db.py            256行  SQLite + FTS5 + CRUD
│   ├── tagger.py        167行  自动标签 + 地区规范化
│   ├── extractor.py     135行  trafilatura 网页正文提取
│   └── source_manager.py 114行  爬虫源配置管理
│
├── 配置
│   ├── config.py         30行  全局配置
│   └── sources.yml       10行  爬虫源清单
│
├── 爬虫
│   ├── crawlers/base.py 116行  爬虫抽象基类
│   └── crawlers/ggzy.py 241行  ggzy.gov.cn 爬虫
│
├── 知识库 (独立于代码)
│   ├── company.yml / projects.yml / team.yml / terms.json
│   └── solutions/*.md
│
└── 文档
    ├── docs/optimization-log.md
    ├── docs/market-research.md
    └── docs/architecture.md  ← 本文件
```

总代码量：2918 行 Python

---

## 二、依赖关系图

```
config.py ──────────────────────────────────────────────────────────────┐
    │                                                                   │
    ├──→ db.py ──→ search.py ──→ report.py                              │
    │       │         │           │                                      │
    │       │         │           └─→ desktop.py (入口)                  │
    │       │         │                                                 │
    │       │         ├──→ bid_writer.py ──→ desktop.py (入口)          │
    │       │         │                                                 │
    │       │         ├──→ ai_analyzer.py ──→ desktop.py (入口)         │
    │       │         │                                                 │
    │       │         └──→ tagger.py ←── crawlers/ggzy.py               │
    │       │              (地区规范化)                                   │
    │       │                                                           │
    │       ├──→ source_manager.py ──→ crawlers/ggzy.py                 │
    │       │                       ──→ extractor.py                    │
    │       │                       ──→ main.py / desktop.py (入口)     │
    │                                                                   │
    └──→ extractor.py ──→ db.py ──→ tagger.py                          │
                                 (双重调用链: insert_notice→tag_and_merge)│
```

**设计原则**：
- 底层模块 (db/search/tagger) 单向依赖 config，不依赖上层
- 入口 (desktop/main) 依赖所有业务模块，这是合理的
- 爬虫 (crawlers) 独立包，通过 BaseCrawler 抽象

---

## 三、当前问题

### 1. desktop.py 太胖 (759行)
- 45 个方法，三个 Tab + 源管理 + 爬取 + URL抓取全挤在一个类里
- 直接 import 6+ 后端模块，耦合面大
- **建议**：拆成 desktop/tab_opportunity.py / tab_bid.py / tab_ai.py

### 2. main.py 里嵌了 FastAPI Web 应用 (200行)
- `cmd_web()` 函数里有 150 行 HTML + FastAPI 路由定义
- 应该抽到 `web/app.py`

### 3. source_manager.py 引用了不存在的 cebpubservice
- 代码里 `elif stype == "cebpubservice":` 但爬虫还没写
- 等爬虫写好后接入即可，临时跳过

### 4. extractor.py 双重打标签
- `ingest_url()` → `insert_notice(auto_tag=True)` → `tag_and_merge()`
- 但 extractor 顶部也 import 了 `tag_and_merge`（没用上）
- 无 bug，但代码混淆

### 5. 没有 tests 目录
- 所有验证靠 `python3 << 'PYEOF'` 临时脚本
- 积累多了应该抽到 `tests/` 下

### 6. 入口分散
- `desktop.py` 和 `main.py gui` 都能启动 GUI
- `main.py web` 启动 Web
- 没有统一的 `__init__.py` 或 package 化

---

## 四、好的一面

- **单向依赖**：底层不依赖上层，没有循环引用
- **抽象基类**：BaseCrawler 让新增爬虫只需实现两个方法
- **配置外置**：sources.yml / config.py / knowledge/ 全是独立数据
- **接口一致**：所有模块返回 dict/str，前端零适配
- **GitHub 对比**：比所有公开招投标爬虫项目都完整

---

## 五、建议重构顺序

| 优先级 | 改动 | 工作量 | 收益 |
|--------|------|--------|------|
| P0 | main.py 拆出 web/app.py | 20分钟 | 清理200行 |
| P0 | extractor.py 去掉无用的 tag_and_merge import | 1分钟 | 消除混淆 |
| P1 | desktop.py 拆成 3 个 tab 文件 | 1小时 | 可维护性 |
| P1 | source_manager 去掉 cebpubservice 未实现引用 | 直接删 | 干净 |
| P2 | 加 tests/ 目录 | 后续积累 | — |
| P2 | package 化 (加 `__init__.py`) | 10分钟 | 标准化 |
