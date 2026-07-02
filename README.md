# 招投标信息工具

从 ggzy.gov.cn 和 bulletin.cebpubservice.com 采集招标公告，SQLite 存储，FTS5 全文搜索，tkinter 桌面端，支持 DeepSeek/通义千问/GPT 等大模型 API 辅助分析。

## 功能

- 爬取 ggzy.gov.cn 首页公告 + cebpubservice.com 翻页列表，自动去重入库
- 自动打标签（优先级/项目形态/可参与/评分），地区名规范化
- 全文搜索 + 地区/类型/日期/优先级筛选 + 8 列表头排序
- 批量删除（Ctrl/Shift 多选）、CSV 导出
- 标书生成：模板模式（纯本地）、AI 增强模式（需 API Key），支持导出 Word
- AI 分析：深度分析、排名推荐、周报、自由提问对话
- 知识库：内置法规、废标风险清单、暗标规范、评分标准、行业指标，支持导入 pdf/docx/md
- 爬虫源管理：sources.yml 配置，可增删开关
- 桌面端 (tkinter) 和 Web 版 (FastAPI) 两个入口

## 下载

从 [Releases](https://github.com/Criss404/bid-tools/releases) 下载对应系统版本（Windows/Linux/macOS），双击运行。

首次运行自动在 `~/.bid_tool/` 创建数据和知识库。AI 功能需在设置弹窗中填入 API Key。

## 运行

```bash
pip install jieba openai trafilatura lxml lxml_html_clean pyyaml requests pdfplumber python-docx
python3 desktop.py       # 桌面端
python3 web_app.py       # Web 端，浏览器访问 http://localhost:8000
```

## 打包

```bash
pyinstaller --onefile --windowed --add-data "knowledge:knowledge" --add-data "sources.yml:." desktop.py
```

`--windowed` 在 Windows 上隐藏控制台窗口，调试时可以先去掉。

## 技术栈

Python / tkinter / SQLite FTS5 / jieba / trafilatura / FastAPI / openai

## License

MIT

## 免责声明

- 本工具仅供学习、研究和个人工作辅助使用。
- 使用本工具生成投标书（技术标）的，生成结果仅供内部起草参考，终稿必须经人工逐项审校。
- 使用者须确保在所在地区遵守适用的网络法规、目标网站服务条款及 robots.txt 要求。
- 因使用本工具所产生的任何直接或间接后果由使用者自行承担。
