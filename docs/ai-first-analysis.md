# AI 功能先行 — 独立分析报告

> 2026-06-30 — 回答一个问题：如果先做 AI Key 配置化，到底要改什么

---

## 一、当前 AI 功能的真实处境

### 5 个功能全写好了，但 GUI 用户用不了

```
GUI Tab3「AI 分析」:
  [深度分析]    → ai_analyzer.analyze_one()  → 调用 DeepSeek → ❌ 报错
  [商机排名]    → ai_analyzer.rank_opportunities() → 同上
  [本周周报]    → ai_analyzer.weekly_report() → 同上
  [自由提问]    → ai_analyzer.ask() → 同上

GUI Tab2「标书生成」:
  AI 增强模式    → bid_writer.gen_bid_ai() → 调用 DeepSeek → ❌ 报错
```

**原因**：`config.py` 第 21 行 `DEEPSEEK_API_KEY = "your-api-key-here"`。这不是真实的 Key，DeepSeek 服务器直接拒绝。GUI 用户不知道怎么改，也不会改。

### 现状是"代码能跑，用户不能跑"

```
开发者 (你)  →  改 config.py → 填真实 Key → AI 能用
GUI 用户      →  看到报错 → [X] AI 分析失败 → 困惑 → 弃用
```

---

## 二、要改什么（7个改动点，3个文件）

### 改动 1：新建 `ai.py` — 统一入口（约 35 行）

**做什么**：把两处各自 `new OpenAI()` 收回到一个函数。读配置文件，返回配置好的客户端。

```python
# ai.py — 所有 AI 调用的唯一入口
import yaml, os
from openai import OpenAI

_CFG = None

def _load():
    """从 ai.yml 读配置，带默认值"""
    path = os.path.join(os.path.dirname(__file__), "ai.yml")
    if os.path.exists(path):
        return yaml.safe_load(open(path)) or {}
    return {}

def get_config():
    """返回当前 AI 配置 dict"""
    cfg = _load()
    return {
        "key": cfg.get("key", ""),
        "url": cfg.get("url", "https://api.deepseek.com"),
        "model": cfg.get("model", "deepseek-chat"),
    }

def is_ready():
    """AI 是否可用"""
    return bool(get_config()["key"].strip())

def chat(messages, **kwargs):
    """统一聊天入口。未配置 Key 时抛友好异常"""
    cfg = get_config()
    if not cfg["key"]:
        raise RuntimeError("AI API Key 未配置。请在设置中填入 Key。")
    client = OpenAI(api_key=cfg["key"], base_url=cfg["url"])
    return client.chat.completions.create(
        model=cfg["model"], messages=messages, **kwargs
    )
```

**改了之后**：`ai_analyzer.py` 和 `bid_writer.py` 不再自己 `new OpenAI()`，改用 `ai.chat(messages, ...)`。

### 改动 2：改 `ai_analyzer.py`（5 处替换，每处 3 行变 1 行）

```
现在:
    client = _get_client()
    response = client.chat.completions.create(model=..., messages=..., ...)

改后:
    response = ai.chat(messages=[...], temperature=0.3, max_tokens=4096)
```

model 参数、异常处理全部移到 `ai.py` 里，调用方只管传 messages。5 个函数（`ask` / `analyze_one` / `rank_opportunities` / `weekly_report` / `_get_client`）中的 5 处调用全部替换。

### 改动 3：改 `bid_writer.py`（1 处替换）

```
现在:
    from openai import OpenAI
    client = OpenAI(api_key=..., base_url=...)
    response = client.chat.completions.create(model=..., ...)

改后:
    from ai import chat, is_ready
    if not is_ready():
        return "AI 功能未启用。请在设置中填入 API Key。"
    response = chat(messages=[...], temperature=0.3, max_tokens=8192)
```

### 改动 4：新建 `ai.yml` — 默认配置文件

```yaml
# AI 配置 — 用户填入自己的 Key
key: ""
url: "https://api.deepseek.com"
model: "deepseek-chat"
```

项目根目录下，跟 `sources.yml` 同层。

### 改动 5：GUI 加设置入口（约 50 行）

在 AI 分析 Tab 左侧按钮区域最上方加一个入口：

```
[ AI 设置 ]  ← 点击弹出窗口

┌──────────────────────────┐
│  AI 配置                  │
│                           │
│  API Key:  [____________] │  ← 填入真实 Key，显示为 ●●●●
│  Base URL: [____________] │  ← 预填 https://api.deepseek.com
│  Model:    [____________] │  ← 预填 deepseek-chat
│                           │
│  [测试连接]  [保存]        │
│                           │
│  当前状态: 未配置 / 已配置 / 连接失败 │
└──────────────────────────┘
```

「测试连接」按钮发一次短请求验证 Key 是否有效，返回结果在弹窗里显示。

### 改动 6：桌面端 AI tab 按钮加状态感知

现在 4 个按钮永远可点，点了才报错。改后：

```
Key 未配置时:  按钮变灰 (state=DISABLED)，旁边显示"请先配置 API Key"
Key 已配置时:  按钮恢复，可正常使用
```

### 改动 7：CLI 命令也走 `ai.py`

`main.py` 的 `cmd_ask` / `cmd_analyze` / `cmd_rank` / `cmd_weekly` 调用 `ai_analyzer.py`，自动跟着受益。不需要改 `main.py`。

---

## 三、改动量汇总

| # | 文件 | 操作 | 行数 |
|---|------|------|------|
| 1 | `ai.py` | 新建 | 35 |
| 2 | `ai_analyzer.py` | 替换 5 处调用 | -10/+5 |
| 3 | `bid_writer.py` | 替换 1 处调用 | -5/+5 |
| 4 | `ai.yml` | 新建 | 4 |
| 5 | `desktop.py` | 加设置弹窗 | 50 |
| 6 | `desktop.py` | 按钮状态感知 | 15 |
| 7 | `config.py` | 删掉写死的 Key | -3 |

**总计：约 110 行改动。净增 3 个文件（ai.py / ai.yml / 弹窗片段）。**

不含路径改造，不含打包，不含爬虫。就是纯 AI 配置化。

---

## 四、做完后的用户体验变化

```
之前:
  点「商机排名」 → "❌ AI 分析失败...请确认 API_KEY" → 用户懵了

之后:
  点「AI 设置」 → 粘贴 Key → 保存
  点「商机排名」 → AI 返回结果 → 5 秒出排名
```

从"AI 功能是尸体"变成"AI 功能能用"。

---

## 五、跟路径改造/打包的关系

AI 配置化和路径改造是**独立正交的**，不存在谁阻塞谁：

```
AI 配置化 → ai.yml 在项目根 → 现在就能用，不用改路径
路径改造 → ~/.bid_tool/ai.yml → 打包前置，现在不做也能开发
```

先做 AI 配置化，不影响后面做路径改造。唯一的影响是：路径改造时要把 `ai.yml` 也移到 `~/.bid_tool/`。

---

## 六、不值得到处做的

| 不做 | 原因 |
|------|------|
| 多供应商切换下拉 | 不到 1 个用户，DeepSeek 最便宜够用 |
| 抽象 AIProvider 基类 | 一个供应商不需要抽象层 |
| 流式输出（打字效果） | tkinter 做流式渲染很复杂，当前一次性返回够用 |
| 用量统计/费用显示 | 个人用不需要 |
| 暗文显示 Key（●●●●）| tkinter Entry 的 `show="*"` 一行搞定，做了 |

---

## 七、开发顺序建议

```
1. ai.yml + ai.py (15min)
2. 改 ai_analyzer.py 5处 + bid_writer.py 1处 (10min)
3. GUI 设置弹窗 + 按钮状态感知 (40min)
4. 测试：填假Key → 友好报错 → 填真Key → 功能正常 (10min)
```

**总计约 1.5 小时。** 做完后 AI 功能从"代码里有但用户不能用"变成"填 Key 就能用"。
