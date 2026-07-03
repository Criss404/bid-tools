# 优化记录

> 每次修改记录于此，方便追溯。

---

## 真实待做清单（2026-07-03 更新）

### 遗留

| # | 问题 | 状态 |
|---|------|------|
| 5 | main.py Web 拆分(200行HTML内嵌) | 待做 |
| 7 | ggzy Playwright 关键词搜索 | 待做(已装Chromium) |
| 8 | knowledge/ 继续扩充 | 持续积累 |
| 9 | company.yml 填真实资质 | 有真实数据后填 |

### 已完成（全部扫清）

| # | 问题 | 状态 |
|---|------|------|
| 1 | 标书导出对话框 | ✅ |
| 2 | 近7天按钮 | ✅ |
| 3 | 爬虫重试 | ✅ |
| 4 | AI 追加不覆盖 | ✅ 7/3 对话区独立+彩显 |
| 6 | cebpubservice 翻10页 | ✅ |
| - | 标书导出 Word | ✅ 7/2 |
| - | AI Tab 左右分栏 | ✅ 7/3 |
| - | AI 输出纯文本 | ✅ 7/3 |
| - | GitHub 开源就绪 | ✅ 7/3 |

### 已完成(从旧记录中清出来)

| 删除 | CSV | 占位符校验 | 爬虫状态 | 详情可复制 | 原文链接 | cebpubservice | 关键词框 | 批量操作 | 源管理 | 知识库导入 |
|------|-----|----------|---------|-----------|---------|--------------|---------|---------|--------|----------|
| ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### 不做(不变)

ES/知识图谱/ML预测/GIS/Qt重写/Docker/国际化/统计图表/通用爬虫/右键菜单/筛选持久化

---

## 修改记录

### 2026-06-20

| # | 改动 | 说明 |
|---|------|------|
| - | 市场调研 | `docs/market-research.md` — 商业产品5层架构、GitHub开源项目对比、差距分析 |

### 2026-06-19

#### 上午：体验优化
| # | 改动 | 说明 |
|---|------|------|
| 1 | 状态栏显示条数 | 筛选后显示「显示:9/35条」，不再永远显示总数 |
| 2 | Enter键搜索 | 搜索框绑Return，敲回车即搜索 |
| 3 | 右键菜单 | 砍掉，体验差且Wayland下无法关闭 |
| 4 | 标书Tab按钮 | 「从看板选取」→「去看板双击选商机」 |
| 5 | 地区名规范化 | 爬虫层加 REGION_NORMALIZE 映射表，城市→省 |
| 6 | 清空筛选按钮 | 「重置全部筛选」一键恢复搜索框+下拉+日期 |
| 8 | 爬虫关键词 | 爬取按钮旁加关键词输入框，空=全量 |
| 9 | 同上[6] | — |

#### 凌晨：排序/筛选
| # | 改动 | 说明 |
|---|------|------|
| - | 列头排序 | 8列表头点击升/降序，带^/v标记，修复了列名→dict key映射bug |
| - | 日期范围筛选 | 起止输入框 + [今天][本周][清除日期]快捷按钮 |
| - | 动态下拉框 | 地区/类型/优先级从DB自动获取，不硬编码 |
| - | 优先级筛选 | 新增优先级下拉框（高优/中优/参考） |
| - | 爬取实时日志 | 点「爬取最新」弹出滚动日志窗口，逐条显示进度 |
| - | base.py日志回调 | `_log()`取代`print()`，支持`log_callback`参数供GUI接入 |

### 2026-06-18

| # | 改动 | 说明 |
|---|------|------|
| - | 项目初始化 | db.py / search.py / bid_writer.py / ai_analyzer.py / report.py / config.py |
| - | 知识库 | knowledge/ 目录（company/projects/team/terms/solutions） |
| - | 桌面端 | desktop.py 530→629行，三Tab + URL抓取 + 爬取按钮 |
| - | CLI入口 | main.py 13个命令 |
| - | 自动打标签 | tagger.py 规则引擎，insert_notice默认auto_tag |
| - | URL正文提取 | extractor.py trafilatura 单URL抓取 |
| - | ggzy爬虫 | crawlers/ 首页→a页→b页详情管道 |
| - | bug修复 | search_filtered region MATCH→LIKE |
| - | bug修复 | tkinter emoji段错误 |

### E. 待办：多源数据（2026-06-20）

| # | 平台 | 网址 | 状态 |
|---|------|------|------|
| 10 | ggzy 全国公共资源交易平台 | ggzy.gov.cn | ✅ |
| 11 | ccgp 中国政府采购网 | ccgp.gov.cn | WAF封IP，待定 |
| 12 | cebpubservice 招标投标公共服务平台 | bulletin.cebpubservice.com | ✅ J节 |

### F. 爬虫源管理（2026-06-20）

| # | 改动 | 说明 |
|---|------|------|
| - | sources.yml | 配置文件，列出所有爬虫源（名称/类型/URL/关键词/启用状态） |
| - | source_manager.py | 增删查开关 + crawl_all_enabled 多源遍历 |
| - | desktop.py 管理弹窗 | 「管理源」按钮 → 弹窗：列表+启用禁用+删除+添加表单 |
| - | main.py sources/add | `python main.py sources` 列出源；`source-add <名> <URL>` 添加 |
| - | 爬取改为多源 | GUI「爬取最新」遍历所有启用源，统一入库 |

### G. 第二轮优化分析（2026-06-29 — 以下大部分已完成，详见 H~M 节）

| 优先级 | 问题 | 状态 |
|--------|------|------|
| 🔴 | 知识库占位符校验 | ✅ H节 |
| 🔴 | CSV导出 | ✅ H节 |
| 🔴 | 爬虫失败无状态栏反馈 | ✅ H节 |
| 🟡 | AI错误提示不友好 | 待做 |
| 🟡 | 详情弹窗加原文链接 | ✅ 6/30修复 |
| 🟡 | 标书导出用文件对话框 | ✅ 7/2 修复 |
| 🟡 | 无法取消爬取 | ✅ 7/1 修复 |
| 🟡 | 爬取关键词占位提示 | ✅ 7/1 关键词框已删除 |
| 🟡 | "近7天"快捷按钮 | ✅ 7/1 修复 |
| 🟡 | AI超时提示 | ✅ 7/3 思考标记已加 |

### H. P0 三项必修完成（2026-06-29）

| # | 改动 | 说明 |
|---|------|------|
| 1 | 知识库占位符校验 | `load_knowledge_context()` 检测 `XXXXXX`，发现后在上下文追加AI警告 |
| 2 | CSV导出 | 「导出CSV」按钮，utf-8 BOM编码，Excel直接开 |
| 3 | 爬虫状态栏 | 底部新增「上次爬取: 成功 N条」/「失败」，爬完自动更新 |

### I. 爬虫关键词分析（2026-06-30 — 已分析，待Playwright）

**问题**: 关键词只是从首页24条里`in`筛选，不是真正搜索ggzy
**根因**: ggzy搜索是JS POST，requests做不到
**方案**: Playwright搜索 → _fetch_urls分两路（有kw走Playwright，无kw走requests）
**前置**: `playwright install chromium` (~300MB)
**状态**: Playwright包已装，Chromium已装(/data/playwright-browsers)，代码未改

### J. cebpubservice 爬虫上线 (2026-06-30)

| # | 改动 | 说明 |
|---|------|------|
| - | crawlers/cebpubservice.py | 新建 147行，纯 requests 解析列表页 HTML table |
| - | source_manager.py | cebpubservice 占位代码替换为正式调用 |
| - | desktop.py | 源类型下拉去掉"(未实现)"标记 |
| - | sources.yml | 清理无效源，两个源均启用 |

实测:
- ggzy 首页 20条 (存量已覆盖)
- cebpubservice 1页列表 20条新入库
- DB 32 → 53条 (+21)

cebpubservice 特点:
- 3 页 × 20条/页 = 60条，翻页完全通过 page=N 参数
- 不需要 Playwright，纯 requests
- 标题/地区/行业/日期/来源平台/UUID 全部可提取
- 正文暂不抓 (详情页是 JS SPA)

### K. 可投规则 + 关键词删除 + 标书纯文本 (2026-07-01)

| # | 改动 | 说明 |
|---|------|------|
| - | 关键词输入框删除 | 爬虫全量入库，筛选交给GUI搜索，两条路分清楚 |
| - | gen_bid_template() | 去掉 # ** > --- \| 等 Markdown 语法 |
| - | _checklist_section() | 不用 Markdown 表格了，改用纯文本 |

### L. 知识库导入 (2026-07-01)

| # | 改动 | 说明 |
|---|------|------|
| - | knowledge_importer.py | 108行，md/json/yml直接复制，pdf/docx→md，txt→md |
| - | desktop.py | 「导入文件」按钮 + 文件对话框 |
| - | load_knowledge_context() | 加读 imported/ 子目录 (.md/.yml/.json/.txt) |
| - | 依赖 | pdfplumber + python-docx 已安装 |


### M. 界面术语改名 (2026-07-01)

| 原来 | 改成 | 改动的文件 |
|------|------|-----------|
| 停车商机雷达 | 招投标信息工具 | desktop/report/ai_analyzer |
| 商机看板 | 信息总览 | desktop |
| 高优/中优/参考 | A级/B级/C级 | config/db/tagger/desktop/ai_analyzer/report + DB迁移 |
| 可投/仅可投 | 可参与 | desktop/ai_analyzer |
| 不可投 | 已结束 | ai_analyzer |
| 商机 | 标讯 | desktop/ai_analyzer/report |

### N. 打包/部署分析 (2026-07-01)

**打包方案**: PyInstaller --onefile --windowed，需先做路径改造(数据→~/.bid_tool/)
**跨平台**: GitHub Actions 三平台并行打包
**替代工具**: Nuitka(编译,更小更快但构建慢) / Briefcase(原生安装器) / PyApp(Rust包装器) — 均不需要，PyInstaller够用
**部署**: 内网服务器 → web_app.py FastAPI 浏览器访问；外网 → 云服务器+域名+HTTPS
**当前 VM**: 192.168.88.222:8000 可做内网Web服务器，同局域网可直接浏览器访问

**结论**: 桌面版(PyInstaller) + Web版(web_app.py)两条路独立

### O. 路径改造 + GitHub 打包 (2026-07-02)

**路径改造**: 数据全部移到 ~/.bid_tool/
- config.py: DB_PATH/KNOWLEDGE_DIR 改指用户目录
- source_manager/ai/knowledge_importer: 配置文件路径同步
- desktop.py main(): 首次运行自动建目录+建库+种子+复制知识库和配置
- bootstrap() + _get_resource_dir(): PyInstaller打包时走 sys._MEIPASS

**GitHub**: 
- repo: Criss404/bid-tools (私有)
- CI: GitHub Actions 三平台 PyInstaller 打包 (4次修复迭代)

**CI 修复过程**:
1. 矩阵 include 去重 (6 job → 3 job)
2. 加 sys deps (Ubuntu libxml2-dev + python3-tk)
3. fail-fast: false (Ubuntu失败不连累Windows)
4. sources.yml/ai.yml 被 .gitignore 排除 → --add-data 报错 → 强制入库
5. Windows runner 默认 PowerShell → 加 shell: bash

**爬虫取消**: desktop 按钮切换 → source_manager cancel_event → base.py 循环检查 → 连续3次失败自动停止
**Web版**: web_app.py 重写前端，FastAPI 后端 API 全部就绪

### P. 开源准备 + 清理 (2026-07-03)

| # | 改动 | 说明 |
|---|------|------|
| - | LICENSE | MIT |
| - | README | 徽章+项目结构+免责声明+隐去域名 |
| - | ai.yml | 清空真实Key |
| - | knowledge/README | 标注测试模板 |
| - | .gitignore | 加 csv |
| - | 旧CSV/数据库/__pycache__ | 清理 |
| - | docs/optimization-summary.md | 三版分析合并 |
