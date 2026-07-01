# 招投标信息工具

> 全国公共资源交易平台 + 招标投标公共服务平台 — 实时采集、智能筛选、AI 标书生成

## 功能

- **双源采集** — ggzy.gov.cn + cebpubservice.com，每次 60+ 条最新公告
- **智能标签** — 自动标注 A/B/C 级优先级、可参与状态、项目形态、综合评分
- **全文搜索** — SQLite FTS5 + jieba 中文分词，8 列排序，多条件筛选
- **AI 分析** — 接入 DeepSeek/通义千问/GPT，深度分析、排名推荐、周报生成
- **标书生成** — 模板模式或 AI 增强模式，含知识库（法规/废标/暗标/评分标准）
- **知识库** — 内置招投标法规、废标风险清单、暗标规范、行业技术指标，支持 PDF/Word 导入
- **批量操作** — Ctrl/Shift 多选删除，CSV 导出

## 快速开始

从 [Releases](https://github.com/Criss404/bid-tools/releases) 下载对应系统版本，双击运行。

首次运行自动在 `~/.bid_tool/` 创建数据和知识库。

## 开发

```bash
pip install jieba openai trafilatura lxml lxml_html_clean pyyaml requests pdfplumber python-docx
python3 desktop.py       # 桌面版 (tkinter)
python3 web_app.py       # Web 版 (浏览器 :8000)
```

## 技术栈

Python / tkinter / SQLite FTS5 / FastAPI / trafilatura / jieba / OpenAI SDK

## License

MIT
