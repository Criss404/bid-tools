# 通用爬虫 — 技术可行性分析

> 2026-06-30 — 回答: 能不能做一个通用爬虫，添加任何URL就可以自动爬取

---

## 一、问题本质

你想要的是：

```
用户输入: https://某个招投标网站.com
     ↓
爬虫自动: 发现这个网站上的所有招投标公告列表页
     ↓
         找到每条公告的详情页链接
     ↓
         逐一抓取详情页正文
     ↓
         入库
```

**这本质上是让程序做到:"自己理解网站结构"。**

---

## 二、技术上能不能做

### 能做到80% — 基于页面特征的自动分类

任何招投标网站都有两种页面：

| 页面类型 | 特征 | 做什么 |
|---------|------|--------|
| **列表页** | 链接多(>10个)、正文少 | 提取所有同域链接，加入待爬队列 |
| **详情页** | 正文多(>500字)、链接少 | 用trafilatura提取正文，入库 |

**核心算法 — 链接密度判断**：

```python
def classify_page(html, url):
    links = count_a_tags(html)
    text_len = len(extract_text(html))
    
    if links > 15 and text_len < 1000:
        return "列表页"  → 提取链接，继续爬
    elif text_len > 500:
        return "详情页"  → 提取正文，入库
    else:
        return "跳过"    → 关于我们/联系我们等无用页
```

**基于这个判断，再加同域BFS，就能自动发现并抓取。** 不需要为每个网站写规则。

### 能做到90% — 借助 trafilatura 的列表发现

trafilatura 有内置的链接提取功能。`trafilatura.extract()` 处理页面时会自动识别正文区域，`trafilatura.links` 可以拿文章里的链接。

### 做不到100%

有些网站把内容藏在 JS 里、或需要翻页参数、或有验证码——这些 requests + trafilatura 搞不定。

---

## 三、GitHub 上的现成方案

| 项目 | 做什么 | 能不能直接用 |
|------|--------|-------------|
| **Gerapy Auto Extractor** | 自动区分列表页/详情页，无需写XPath | `pip install gerapy-auto-extractor`，最接近你要的 |
| **AutoScraper** | 给它一个URL+一个你想要的值，它自动学习提取规则 | `pip install autoscraper`，适合"我知道我想抓什么" |
| **Musubi** | 4种爬取策略+AI Agent自动优化爬取参数 | `pip install musubi-scrape`，功能强但依赖较多 |
| **my-site-url-finders** | 纯同域BFS，简单可靠 | 120行代码，可以直接参考 |

**Gerapy Auto Extractor 最适合你的场景。**

---

## 四、对你项目最务实的方案

**不引入新依赖，基于现有 trafilatura + requests 写一个 `GenericCrawler`。**

### 算法

```
GenericCrawler(BaseCrawler):
    _fetch_urls():
        给定一个起始URL → requests下载 → 提取所有同域链接
    
    _parse_detail(html, url):
        用 trafilatura 提取正文
        如果正文 > 200字 → 返回 dict
        如果正文 < 200字 → 判定为列表页 → 返回 None（不是公告）
    
    crawl()【重写模板方法】:
        1. 从起始URL开始 BFS
        2. 每页尝试 parse
        3. 如果 parse 成功（正文>200字）→ 结果列表
        4. 如果 parse 失败 → 提取该页所有同域链接 → 加入队列
        5. 直到队列空或达到 max_pages
```

### 改动量

```
crawlers/generic.py      ~80行  GenericCrawler
source_manager.py         +1行  新的elif分支
desktop.py               改1行  Combobox加一项
```

**约80行代码。纯 requests + trafilatura，不需要新依赖。**

### 效果预估

```
✅ 适用: 静态HTML网站、列表页是纯链接的
⚠️ 部分适用: 翻页带参数的（可能重复爬）
❌ 不适用: 纯JS渲染、需要登录、有验证码的
```

---

## 五、结论

**能做。** 最好的方案不是引入第三方库，是写一个 80 行的 `GenericCrawler`——同域 BFS + 链接密度判断 + trafilatura 正文提取。不需要新依赖，纯用现有的 requests + trafilatura + re。

代价是不能100%覆盖所有网站，但覆盖静态招投标网站足够了。而且代码量极小，对标 `GgzyCrawler` 的 241 行，它更简单。
