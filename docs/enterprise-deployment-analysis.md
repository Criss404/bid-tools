# 企业级本地部署分析

> 2026-06-30 — 假设：公司服务器 + 多张 GPU + 本地大模型 + RAG 知识库
> 
> 回答：当前项目哪些能直接搬过去，哪些必须重写，正确的架构应该是什么样

---

## 一、假设的未来环境

| 资源 | 预估 |
|------|------|
| GPU | 10+ 张 NVIDIA（如 A100/4090），每张 24-48GB 显存 |
| 内存 | 128-512GB |
| 存储 | 10TB+ |
| 模型 | Qwen2.5-72B / DeepSeek-V3-671B / Llama-3-70B 本地部署 |
| 推理框架 | vLLM / Ollama / Text Generation Inference |
| 向量数据库 | Milvus / Qdrant / Chroma |
| 用户 | 公司内部 3-20 人 |

---

## 二、当前项目全景

### 现状一句话

```
bid_tool = 爬虫 + SQLite + tkinter 桌面端 + DeepSeek API 调用
```

### 分层看

| 层 | 现有技术 | 企业部署后 |
|----|---------|-----------|
| **前端** | tkinter 桌面 | **不可用** — 多人用必须 Web |
| **API 入口** | 无（直接 import 函数） | **必须加** — 前端不再直接调 Python 函数 |
| **AI 调用** | `ai.py` → DeepSeek API | **保留但改** — URL 指向本地 vLLM/Ollama |
| **知识库** | `knowledge/` 5 个 yml/md 文件 | **改 RAG** — 向量数据库 + 检索 |
| **搜索** | SQLite FTS5 + jieba | **保留** — 结构化数据搜索不需要 ES |
| **爬虫** | `crawlers/ggzy.py` requests | **保留** — 爬虫逻辑不变 |
| **数据库** | SQLite 单文件 | **升级** — PostgreSQL（多用户并发写） |
| **部署** | `python desktop.py` | Docker Compose / K8s |

---

## 三、什么能直接搬过去

| 模块 | 结论 | 原因 |
|------|------|------|
| `db.py` | 保留，换后端 | SQL → PostgreSQL，但 CRUD 接口不变 |
| `search.py` | 保留 | FTS5 → PostgreSQL `tsvector` 或保持 SQLite 都可以 |
| `tagger.py` | **原样保留** | 纯规则引擎，无外部依赖，放哪都能跑 |
| `extractor.py` | **原样保留** | trafilatura 是库，不依赖平台 |
| `crawlers/ggzy.py` | **原样保留** | 爬虫就是 HTTP 请求，跟部署环境无关 |
| `crawlers/base.py` | **原样保留** | 抽象基类，可复用 |
| `source_manager.py` | **原样保留** | YAML 配置管理 |
| `bid_writer.py` | 保留下半身 | 知识库加载、模板结构保留；AI 调用改走本地 |
| `ai.py` | **核心保留** | 统一入口已做好，只改 `ai.yml` 的 URL |

**结论：12 个模块中，10 个可以直接搬。不用重写。**

---

## 四、什么不能搬，必须重写/新增

### 1. 前端 — tkinter → Web

```
当前: desktop.py (759行 tkinter)
      单人桌面操作，所有功能挤在一个窗口里

企业: Web 前端
      多人同时用，每人自己的浏览器
      需要: Vue3/React + 路由 + 权限
```

**这是最大的改动。** 但注意——`main.py` 里已经有 FastAPI 雏形。正确的做法是 `desktop.py` 保持不变（个人用），新增 `web/` 做企业版。

### 2. 没有 API 层

```
当前架构:
  GUI/CLI → import 模块 → 直接调函数

企业需要:
  浏览器 → HTTP → FastAPI → 调函数
```

当前没有后端服务层。但所有业务函数都已经有干净的接口（`search(kw) → list[dict]`），只需包一层 FastAPI 路由：

```python
@router.get("/api/search")
def api_search(kw: str):
    return search(kw)  # 直接复用现有函数，不改一行
```

### 3. 数据库 — SQLite → PostgreSQL

| 原因 | 说明 |
|------|------|
| 并发写 | 多人同时爬取入库，SQLite 单写锁会卡 |
| 全文搜索 | PostgreSQL `tsvector` + `pg_jieba` 比 FTS5 更工业 |
| 备份 | pg_dump + WAL 归档 |

但接口不变——`get_db()` 改成 `asyncpg` 或 `psycopg2` 连接，其他模块不受影响。

---

## 五、RAG 知识库的正确做法

### 当前问题

```python
# bid_writer.py
knowledge = load_knowledge_context()  # ← 15KB，全部塞进 prompt
```

15KB 够用。但企业部署后知识库会长到：

```
500 份历史标书 × 平均 50KB = 25MB
200 条法规条款
100 篇技术方案
50 个公司资质文件
────────────────────
总计: 50MB+
```

全部塞进 prompt 会超 64K/128K 上下文限制。

### RAG 的正确架构

```
┌────────────────────────────────────────────┐
│              文档入库流程 (离线)              │
│                                            │
│  ① 文档切块: 500字一块，保留上下文           │
│  ② Embedding: 用本地模型转成 1024维向量     │
│  ③ 存向量库: Milvus / Qdrant               │
│                                            │
│  示例: "电子与智能化工程专业承包壹级"        │
│    → 向量 [0.23, -0.45, 0.87, ...]        │
│    → 存入 Milvus collection                │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│              查询流程 (在线)                 │
│                                            │
│  用户问: "我们有建筑智能化一级资质吗"        │
│     ↓                                      │
│  ① 问题转向量 → [0.21, -0.43, 0.85, ...]  │
│  ② Milvus 检索 → 返回最相关 5 个文档块      │
│     ↓                                      │
│  ③ 拼进 prompt:                            │
│     "基于以下公司资质信息回答:               │
│      [检索到的资质文档块1-5]                 │
│      用户问题: 我们有建筑智能化...?"          │
│     ↓                                      │
│  ④ 本地 LLM 生成回答                        │
└────────────────────────────────────────────┘
```

### 对你当前代码的影响

```python
# 现在: bid_writer.py
knowledge = load_knowledge_context()              # 15KB 全塞

# 以后:
def load_knowledge_context(query: str = ""):
    knowledge = _load_local_files()               # 15KB 基础知识（文件小，全塞没问题）
    if query:                                      # 如果有具体问题
        rag_docs = _search_rag(query)              # 从向量库搜相关文档
        knowledge += "\n\n--- 检索到的相关文档 ---\n" + rag_docs
    return knowledge
```

**知识库变大后不需要重写 bid_writer，只需要在 `load_knowledge_context` 里加一个 RAG 检索步骤。**

---

## 六、企业版完整架构

```
┌──────────────────────────────────────────────────────────┐
│                     前端 (Web)                            │
│  Vue3 + 商机看板 + AI聊天 + 标书编辑器 + 知识库管理        │
└──────────────────────────────────────────────────────────┘
                         │ HTTP
                         ▼
┌──────────────────────────────────────────────────────────┐
│                  API 层 (FastAPI)                          │
│  /api/search   /api/bid   /api/crawl   /api/chat          │
│  全部复用现有函数: search(), gen_bid(), crawl_all()        │
└──────────────────────────────────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
┌──────────────┐ ┌────────────┐ ┌──────────────┐
│  业务层       │ │  AI 推理层   │ │  数据层       │
│  tagger      │ │  ai.py      │ │  PostgreSQL  │
│  extractor   │ │  vLLM/Ollama│ │  Milvus      │
│  bid_writer  │ │  RAG 检索   │ │  爬虫调度     │
│  (保留)      │ │  (新增)     │ │  (升级)      │
└──────────────┘ └────────────┘ └──────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│                     本地 GPU 集群                         │
│  10+ GPU → vLLM 推理服务 → OpenAI 兼容端点                │
│  ai.yml: url: "http://gpu-server:8000/v1"                 │
│          model: "qwen2.5-72b"                             │
└──────────────────────────────────────────────────────────┘
```

---

## 七、跟当前项目的对照

| 层 | 现在的代码 | 企业版要动什么 | 动多少 |
|----|-----------|--------------|--------|
| 前端 | `desktop.py` (tkinter) | **新增 Web 前端** | 全部新写 |
| API | 无 (直接 import) | **新增 FastAPI 路由** | 包一层，不改业务代码 |
| 业务层 | 9 个模块 | **保留** | 0 |
| AI 调用 | `ai.py` | 改配置 | 改 2 行 yml |
| 知识库 | `load_knowledge_context()` | 加 RAG 检索步骤 | 改 5 行 |
| 数据库 | SQLite | PostgreSQL | 改 `get_db()` 连接 |
| 爬虫 | `crawlers/` | **保留** | 0 |
| 部署 | 手动 `python` | Docker | 新写 Dockerfile |
| RAG 向量库 | 无 | Milvus/Qdrant | 新增 ~100 行 |
| Embedding | 无 | 本地 bge-large-zh | 新增 ~50 行 |

**结论: 70% 的代码可以原地搬。** 业务逻辑、标签引擎、爬虫、搜索核心——这些才是项目的核心价值，它们跑在云端还是本地没有区别。

---

## 八、正确的开发顺序

### 第一阶段: 现在 (这台测试 VM)

```
1. 继续完善爬虫 + 数据管理
2. knowledge/ 扩充 — 积累招投标专业文档
3. ai.py 保持云端 DeepSeek

你的角色: 搭基建，存数据
```

### 第二阶段: 有实体机后

```
1. 装 Ollama → 下载 qwen2.5:14b → 改 ai.yml url → 本地跑
2. 装 Qdrant → 把 knowledge/ 文档向量化 → RAG 检索
3. 加 FastAPI 后端 → Web 前端替换 tkinter

你的角色: 从桌面工具升级为个人全栈应用
```

### 第三阶段: 公司 GPU 服务器

```
1. 部署 vLLM + qwen2.5-72b → 多用户并发
2. PostgreSQL + Milvus 替换 SQLite
3. Docker Compose 一键部署
4. 多人 Web 前端 + 权限管理

你的角色: 产品化部署
```

---

## 九、一句话总结

**你现在的项目不是一个"要丢弃的原型"，而是一个"正确的核心"。** 

爬虫、标签引擎、标书生成逻辑、搜索——这些 10 个模块都是可复用的。到了企业级，它们不需要重写，只需要换壳——换前端（Web）、换数据库（PostgreSQL）、换 AI 后端（本地 LLM）、换知识库（RAG）。

**你现在做的事情，每一步都在为将来的企业版打地基。**
