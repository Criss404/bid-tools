# AI API 接入架构分析

> 2026-06-30 — 讲清楚"AI API 入口"是什么、现在怎么做、可以怎么改进

---

## 一、先讲概念：AI API 是什么

### 用大白话说

你现在想让 AI 帮你写标书、分析商机。AI 模型（DeepSeek）不在你的电脑上——它在云端服务器上。

**API 就是"远程调用的门"**。你发一段文字过去，它算完把结果发回来。

```
你的电脑                     DeepSeek 服务器
   │                              │
   │──→ 发请求: "帮我写标书"  ──→│
   │                              │  GPU 计算
   │←── 返回: "一、项目概述..." ←─│
```

### 什么是"API 入口/配置"

就是你告诉程序三样东西：

| 配置项 | 是什么 | 你现在怎么写的 |
|--------|--------|--------------|
| **API Key**（密钥） | 你的身份凭证，证明你有权调用。像银行卡密码 | `DEEPSEEK_API_KEY = "your-api-key-here"` |
| **Base URL**（地址） | 服务器的网址。像银行的地址 | `https://api.deepseek.com` |
| **Model**（模型名） | 调用哪个版本的 AI。V3便宜/V4聪明 | `deepseek-chat` |

### 为什么需要"入口"

因为这三样东西会变：
- 用户有不同供应商的 Key（DeepSeek / 通义千问 / OpenAI）
- Key 会过期要更新
- 想换更便宜或更强的模型

**如果写死在代码里，换一个就得改代码重新打包。如果做成可配置的，用户在 GUI 里填一下就行。**

---

## 二、你现在是怎么做的

### 调用链路

```
用户在 GUI 点击「商机排名」
        ↓
desktop.py → ai_analyzer.rank_opportunities()
        ↓
ai_analyzer.py:
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    response = client.chat.completions.create(model=DEEPSEEK_MODEL, ...)
        ↓
HTTP 请求 → https://api.deepseek.com → 返回结果
```

### 哪些地方调 AI

```
bid_tool/
├── ai_analyzer.py (4 个函数)
│   ├── ask(question)           → 自由提问
│   ├── analyze_one(notice_id)  → 深度分析
│   ├── rank_opportunities()    → 排名推荐
│   └── weekly_report()         → 周报生成
│
└── bid_writer.py (1 个函数)
    └── gen_bid_ai(notice_id)   → AI 标书生成
```

**5 个 AI 功能，全走 DeepSeek，全用同一套 Key/URL/Model。**

### 问题

```
config.py:
    DEEPSEEK_API_KEY = "your-api-key-here"    ← 用户不知道怎么填
    DEEPSEEK_BASE_URL = "https://api.deepseek.com"  ← 写死了，换不了
    DEEPSEEK_MODEL = "deepseek-chat"                ← 写死了，选不了

ai_analyzer.py:  自己 new OpenAI()
bid_writer.py:   自己也 new OpenAI()            ← 重复代码，两处都要改
```

---

## 三、行业通用做法

### 三层抽象

```
┌──────────────────────────────────┐
│  配置层                           │
│  用户在 GUI 填: Key / URL / Model  │
│  存到 ai_config.yml               │
├──────────────────────────────────┤
│  统一入口层 (AIProvider)           │
│  所有 AI 调用都经过这一个对象      │
│  provider.chat(prompt)            │
│  不管后面是 DeepSeek 还是通义千问  │
├──────────────────────────────────┤
│  调用层 (ai_analyzer / bid_writer) │
│  只管"我要 AI 做什么"，不管"怎么调"│
└──────────────────────────────────┘
```

### 好处

```
现在:
  ai_analyzer.py → OpenAI(key, url) → DeepSeek
  bid_writer.py  → OpenAI(key, url) → DeepSeek
  换供应商要改两个文件

改后:
  ai_analyzer.py → ai.provider.chat()
  bid_writer.py  → ai.provider.chat()
                   ↑
               ai.py (一个地方配置)
                   ↑
            ai_config.yml (用户可编辑)
  
  换供应商只改 ai_config.yml，不改代码
```

---

## 四、对你目前阶段的实际建议

### 不需要做大改

**理由**: 你现在只有一个 AI 供应商（DeepSeek），5 个 AI 调用点。做个抽象层是「为了以后」，不是「现在需要」。

### 应该做的：最小改动

**把 Key 从代码里拿出来，让用户能在 GUI 填写。**

当前：
```python
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "your-api-key-here")
```
用户要改 Key 必须设环境变量或改 config.py——GUI 用户不会。

改为：
```
GUI 设置页 → 填入 Key → 保存到 ~/.bid_tool/ai_config.yml
                             ↓
                        ai.py 启动时读取
                             ↓
                  所有 AI 调用用这份配置
```

### 要改的东西

| 改动 | 做什么 | 工作量 |
|------|--------|--------|
| 1. `ai.py` 新建 | 统一 AI 调用入口，替代两处重复的 `OpenAI(...)` | 30 行 |
| 2. 改 `ai_analyzer.py` | 不再自己 new OpenAI，改用 `ai.chat()` | 5 处改动 |
| 3. 改 `bid_writer.py` | 同上 | 1 处改动 |
| 4. GUI 加设置弹窗 | 填 Key / URL / Model，保存到 yml | 40 行 |
| 5. 去掉 `config.py` 里写死的 Key | 改为 `ai.py` 读 yml | 2 行 |

共约 **80 行改动，1 小时**。

---

## 五、支持多供应商的代价

如果以后想接入通义千问、OpenAI、Claude：

### 好消息

它们都兼容 OpenAI SDK（`client.chat.completions.create()` 调用格式一样）。改 Base URL + Model + Key 就行，**不改代码**。

```
DeepSeek:      base_url="https://api.deepseek.com",       model="deepseek-chat"
通义千问:       base_url="https://dashscope.aliyuncs.com/...", model="qwen-max"
OpenAI:        base_url="https://api.openai.com/v1",       model="gpt-4o"
```

这就是 OpenAI SDK 兼容性的价值——换供应商只改配置，不用改调用代码。

### 坏消息

价格差异大：

| 供应商 | 模型 | 输入价格 | 输出价格 |
|--------|------|---------|---------|
| DeepSeek | deepseek-chat | 1元/百万token | 2元/百万token |
| 通义千问 | qwen-max | 20元/百万token | 60元/百万token |
| OpenAI | gpt-4o | 18元/百万token | 72元/百万token |

---

## 六、总结

### 概念回顾

| 概念 | 一句话 |
|------|--------|
| API | 远程调用的门，发文字过去、拿结果回来 |
| API Key | 身份凭证，证明你有权调用 |
| Base URL | 服务器的网址 |
| Model | 调用哪个版本的 AI |
| OpenAI SDK 兼容 | 不同供应商用同一套代码格式，只改配置就能切换 |

### 你该做什么

**做一个配置入口，让用户在 GUI 里填 Key**。不做多供应商、不做 RAG、不做微调。就是把现在写死在 `config.py` 里的三行拿出来，让用户自己填。

这是最小的改动，最大的收益——从此以后用户不需要打开代码文件就能启用 AI 功能。

### 一句话

**现在你要的不是"大改架构"，是"给 AI 功能加个开关"。**
