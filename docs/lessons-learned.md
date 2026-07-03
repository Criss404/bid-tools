# 开发踩坑记录

> 全项目累计错误与解决，便于下次避坑。

---

## 一、tkinter UI 踩坑

| 问题 | 现象 | 解决 |
|------|------|------|
| emoji 段错误 | `🎯🔍📊` 任何 emoji 字符导致 Linux tkinter 进程直接 Segfault | 全部换成纯 ASCII + 中文 |
| Combobox 蓝底高亮消不掉 | Wayland + GTK Combobox 选中后蓝色高亮滞留，focus_set/disable/redraw 均无效 | 不管它，不影响使用 |
| OptionMenu 换回 Combobox | OptionMenu 颜值差、command 不自动触发筛选联动、动态更新繁琐 | 换回 Combobox，接受蓝底高亮 |
| 右键菜单无法关闭 | Wayland 下 Menu.post() 不能通过点空白处消失 | 砍掉右键菜单 |
| ScrolledText 滚动感觉差 | 大段文本滚动时视觉跳跃 | 使用 tk.END + see(tk.END) 始终定位底部 |

---

## 二、打包和 CI 踩坑

| 问题 | 根因 | 解决 |
|------|------|------|
| --add-data 找不到文件 | sources.yml/ai.yml 被 .gitignore 排除，从未 push 到仓库 | 从 .gitignore 中移除这两个文件，强制 push |
| `matrix.include` 生成 6 个 job | `os: [ubuntu, windows, mac]` + `include:` 双重展开导致多出一倍的重复空 artifact job | 只保留 `include`，不单独列 `os` |
| Windows CI 用 PowerShell 报语法错误 | GitHub Actions Windows runner 默认 PowerShell，不认识 `--` 和 `\` | 加 `shell: bash` |
| Ubuntu 失败连累 Windows/Mac | GitHub Actions 默认 fail-fast: true | 加 `fail-fast: false` |
| Ubuntu `python3-tk` 和 `libxml2` 缺失 | GitHub Actions Ubuntu runner 不预装 tkinter 的 C 绑定和 lxml 编译依赖 | 加 `apt-get install python3-tk libxml2-dev libxslt-dev` |
| Windows 打包后 exe 双击无反应 | `--windowed` 隐藏控制台，所有报错看不见 | 调试时先去掉 `--windowed`，确认能跑再加回去 |
| exe 启动找不到知识库/爬虫源 | `--add-data` 打包后文件在 exe 内部，首次启动 `os.path.dirname(__file__)` 找到的是临时目录而非 exe 内的资源 | 加 `_get_resource_dir()` 区分 `sys._MEIPASS` 和源码目录，加 `bootstrap()` 首次运行时把资源复制到 `~/.bid_tool/` |

---

## 三、爬虫

| 问题 | 现象 | 解决 |
|------|------|------|
| 关键词不生效 | 关键词只是从首页筛，不是发给搜索引擎 | 需要 Playwright 搜索（已装 Chromium，代码未改） |
| 关键词从 GUI 传到爬虫链路断 | GUI 输入框被删，但 source_manager 未收到 | 在源管理弹窗的 keyword 字段继续存在 |
| cebpubservice 列表页 HTML 解析不对 | 第一版正则没匹配到 title 内的 UUID | 改成只匹配 32 位 hex UUID 而不是带 `http://` 的 URL |
| ggzy 正文很短 | 种子数据内容短，爬虫拿到的 ggzy 首页 a 页也只给摘要 | 正文在 b 页（onclick showDetail），需要额外请求 |
| `_fetch_urls` 硬编码只爬首页 | 全用 requests.get(ggzy首页)，无搜索能力 | 预留了 Playwright 分支（未启用） |

---

## 四、AI

| 问题 | 现象 | 解决 |
|------|------|------|
| AI 输出全是 Markdown 符号 | system prompt 要求 AI 用 `##`/`**`/`-` 回答 | system prompt 换成纯文本指令 |
| 拼接代码也写了 Markdown | `return f"## 深度分析\n\n**项目：** {title}"` | 换成纯文本空格线 |
| AI 分析每条的新结果覆盖上一条 | `_set_ai_output` 直接 `delete(1.0, tk.END)` | 改成追加 `_append_to_chat` |
| AI 按钮灰色但 Key 已填写 | 更换 Key 后没调 `_update_ai_buttons()` | `on_save` 之后加 `_update_ai_buttons()` |
| DeepSeek Key 在仓库里暴露 | ai.yml 被 git 追踪，里面是真实 Key | 清空 ai.yml，加 .gitignore（之前已 undo） |
| Combobox 的 model name 带括号后缀传给 API | 显示名是 `"DeepSeek V3 (deepseek-chat)"`，不分离就当成模型名发给 API | 拆成 `model_var`（显示用）+ `_model_id[0]`（API 用） |
| 自定义模型不进列表 | 保存后下次打开 Combobox 里没有上次手动输入的模型 | 加了 `_save_user_model` 持久化到 `ai_user_models.yml` |

---

## 五、数据与路径

| 问题 | 现象 | 解决 |
|------|------|------|
| 打包后 exe 内目录不可写 | data/bid.db 存入 `PROJECT_DIR/data/`，打包后是只读临时目录 | 全部移到 `~/.bid_tool/` |
| 首次启动只建库不复制资源 | 原来只检查 DB 是否存在，没复制 knowledge/sources.yml | 拆出 `bootstrap()` 函数，依次建目录/建库/复制资源 |
| `search_filtered` region 用 MATCH 失败 | FTS5 MATCH 只能用在虚拟表，普通 column 用 LIKE 过滤 | 改为 `LIKE %region_seg%` |
| 标题存的是空格分词的 jieba 结果 | 数据库 title 存了 `"绵阳 城市 停车场 智慧 化..."` | 展示时 `title.replace(" ", "")` 还原 |

---

## 六、资源与环境

| 问题 | 现象 | 解决 |
|------|------|------|
| VM 内存不够跑 Chromium | 1.8GB 内存只有 142MB 可用，Playwright 要求 ≥500MB | 硬着头皮试了一把，居然能跑，headless 模式占用较小 |
| 主磁盘空间不足 | Chromium ~300MB，主盘只剩 991MB | 把 Chromium 装到 `/data` 盘（18GB 剩余） |
| trafilatura 安装失败 (lxml.html.clean 缺失) | lxml 6.1.x 把 html_clean 拆成了独立包 | `pip install lxml_html_clean` |
| python-docx 和 pdfplumber 未安装 | 知识库导入功能需要但 CI 和自己的环境都没装 | `pip install pdfplumber python-docx` |

---

## 七、GitHub

| 问题 | 现象 | 解决 |
|------|------|------|
| Token 缺 workflow 权限 | push workflow 文件被远程拒绝 | re-scope token，勾选 workflow |
| `gh auth token` 命令不存在 | 旧版 gh CLI (<2.0) 不支持 | 从 `~/.config/gh/hosts.yml` 直接取 token |
| push --force 后贡献者只有 Claude | 历史 commits 的作者是 `kris.lan@localhost` | 后续 commit 的 email 已修改为正确邮箱 |

---

## 八、CI 修复迭代总结

4 次修复才打通所有平台构建：

1. `.gitignore` 排除了 `sources.yml` 和 `ai.yml` → `--add-data` 报文件不存在
2. `matrix.os: [...] + include:` 双重展开 → 生成 6 个 job 而不是 3 个
3. Windows runner 默认 PowerShell → 非法参数 `--` 和 `\`
4. Ubuntu 系统库缺失 → lxml/tkinter 无法编译
