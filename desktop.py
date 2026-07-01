#!/usr/bin/env python3
"""招投标信息工具 — 桌面端（tkinter）

架构：纯壳。所有逻辑调已有模块：db / search / bid_writer / ai_analyzer / report
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import os
import sys
import shutil
from datetime import datetime

# 确保能 import 同目录模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import get_all_notices, get_notice_by_id, get_stats, init_database, seed_data, delete_notice, delete_notices
from config import DB_PATH
from search import search
from bid_writer import gen_bid_template, gen_bid_ai
from ai_analyzer import ask, analyze_one, rank_opportunities, weekly_report
from report import report_dict


# ── 全局样式 ──
FONT = ("Noto Sans CJK SC", 10)
FONT_BOLD = ("Noto Sans CJK SC", 10, "bold")
FONT_TITLE = ("Noto Sans CJK SC", 14, "bold")


class BidToolApp:
    """主应用"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("招投标信息工具")
        self.root.geometry("1100x750")
        self.root.minsize(900, 600)

        self._build_header()
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 4))

        self._build_opportunity_tab()
        self._build_bid_tab()
        self._build_ai_tab()

        self._build_statusbar()
        self._refresh_statusbar()

    # ═══════════════════════════════════════════
    # 顶部标题栏
    # ═══════════════════════════════════════════

    def _build_header(self):
        frame = tk.Frame(self.root, bg="#1a1a2e", height=48)
        frame.pack(fill=tk.X)
        tk.Label(frame, text="[=] 招投标信息工具",
                  font=FONT_TITLE, fg="white", bg="#1a1a2e",
                  padx=16, pady=8).pack(side=tk.LEFT)
        tk.Label(frame, text="全国公共资源交易平台 · 实时监控",
                  font=FONT, fg="#aaa", bg="#1a1a2e",
                  padx=8, pady=8).pack(side=tk.LEFT)

    # ═══════════════════════════════════════════
    # Tab1: 信息总览
    # ═══════════════════════════════════════════

    def _build_opportunity_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  信息总览  ")

        # ── 搜索栏第1行 ──
        sf1 = tk.Frame(tab)
        sf1.pack(fill=tk.X, padx=8, pady=(8, 2))

        tk.Label(sf1, text="搜索：", font=FONT).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(sf1, textvariable=self.search_var,
                                      font=FONT, width=26)
        self.search_entry.pack(side=tk.LEFT, padx=2)
        self.search_entry.bind("<Return>", lambda e: self._refresh_data())
        tk.Button(sf1, text="搜索", font=FONT,
                  command=self._refresh_data).pack(side=tk.LEFT, padx=2)

        tk.Label(sf1, text="  地区：", font=FONT).pack(side=tk.LEFT)
        self.filter_region = ttk.Combobox(sf1, width=6, font=FONT, state="readonly")
        self.filter_region.pack(side=tk.LEFT, padx=2)
        self.filter_region.set("全部")
        self.filter_region.bind("<<ComboboxSelected>>", lambda e: self._refresh_data())

        tk.Label(sf1, text="类型：", font=FONT).pack(side=tk.LEFT)
        self.filter_type = ttk.Combobox(sf1, width=10, font=FONT, state="readonly")
        self.filter_type.pack(side=tk.LEFT, padx=2)
        self.filter_type.set("全部")
        self.filter_type.bind("<<ComboboxSelected>>", lambda e: self._refresh_data())

        tk.Label(sf1, text="优先级：", font=FONT).pack(side=tk.LEFT)
        self.filter_priority = ttk.Combobox(sf1, width=5, font=FONT, state="readonly")
        self.filter_priority.pack(side=tk.LEFT, padx=2)
        self.filter_priority.set("全部")
        self.filter_priority.bind("<<ComboboxSelected>>", lambda e: self._refresh_data())

        self.filter_bid_var = tk.BooleanVar(value=False)
        cb_bid = tk.Checkbutton(sf1, text="可参与", variable=self.filter_bid_var,
                                 font=FONT, command=self._refresh_data)
        cb_bid.pack(side=tk.LEFT, padx=4)

        # ── 搜索栏第2行: 日期范围 ──
        sf2 = tk.Frame(tab)
        sf2.pack(fill=tk.X, padx=8, pady=(0, 4))

        tk.Label(sf2, text="日期：", font=FONT).pack(side=tk.LEFT)
        self.date_from_var = tk.StringVar()
        self.date_from_entry = tk.Entry(sf2, textvariable=self.date_from_var, font=FONT, width=10)
        self.date_from_entry.pack(side=tk.LEFT)
        self.date_from_entry.bind("<Return>", lambda e: self._refresh_data())
        tk.Label(sf2, text=" ~ ", font=FONT).pack(side=tk.LEFT)
        self.date_to_var = tk.StringVar()
        self.date_to_entry = tk.Entry(sf2, textvariable=self.date_to_var, font=FONT, width=10)
        self.date_to_entry.pack(side=tk.LEFT)
        self.date_to_entry.bind("<Return>", lambda e: self._refresh_data())
        tk.Label(sf2, text=" (YYYY-MM-DD)", font=(FONT[0], 8), fg="#999").pack(side=tk.LEFT)
        tk.Label(sf2, text="   ", font=FONT).pack(side=tk.LEFT)
        tk.Button(sf2, text="今天", font=(FONT[0], 9),
                  command=self._set_date_today).pack(side=tk.LEFT, padx=1)
        tk.Button(sf2, text="本周", font=(FONT[0], 9),
                  command=self._set_date_this_week).pack(side=tk.LEFT, padx=1)
        tk.Button(sf2, text="近7天", font=(FONT[0], 9),
                  command=self._set_date_last7days).pack(side=tk.LEFT, padx=1)
        tk.Button(sf2, text="清除日期", font=(FONT[0], 9),
                  command=self._clear_date).pack(side=tk.LEFT, padx=1)
        tk.Label(sf2, text="  ", font=FONT).pack(side=tk.LEFT)
        tk.Button(sf2, text="重置全部筛选", font=(FONT[0], 9),
                  command=self._reset_all_filters).pack(side=tk.LEFT, padx=2)

        # ── 结果表格 ──
        tree_frame = tk.Frame(tab)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        columns = ("ID", "标题", "类型", "地区", "日期", "优先级", "评分", "可参与")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                  height=15, selectmode="extended")
        widths = [40, 400, 100, 60, 90, 60, 50, 50]
        for col, w in zip(columns, widths):
            self.tree.heading(col, text=col,
                              command=lambda c=col: self._on_column_click(c))
            self.tree.column(col, width=w, anchor="w" if col == "标题" else "center")

        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Double-1>", lambda e: self._on_tree_double_click())
        self.tree.bind("<Delete>", lambda e: self._delete_selected())
        self.tree.bind("<Control-a>", lambda e: self._select_all())

        # 排序状态
        self.sort_col = "评分"
        self.sort_reverse = True

        # 操作按钮
        btn_frame = tk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=8, pady=4)
        tk.Button(btn_frame, text="刷新全部", font=FONT,
                  command=self._load_all).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="管理源", font=FONT,
                  command=self._open_source_manager).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="查看详情", font=FONT,
                  command=self._show_detail).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="批量删除", font=FONT, fg="#c0392b",
                  command=self._delete_selected).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="导出CSV", font=FONT,
                  command=self._export_csv).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="爬取最新", font=FONT,
                  command=self._do_crawl, bg="#2c3e50", fg="white").pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="查看日志", font=(FONT[0], 9),
                  command=self._show_crawl_log).pack(side=tk.LEFT, padx=2)

        # URL 抓取行
        url_frame = tk.Frame(tab)
        url_frame.pack(fill=tk.X, padx=8, pady=(0, 4))
        tk.Label(url_frame, text="抓取URL：", font=FONT).pack(side=tk.LEFT)
        self.url_entry = tk.StringVar()
        tk.Entry(url_frame, textvariable=self.url_entry, font=FONT).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        tk.Button(url_frame, text="抓取入库", font=FONT,
                  command=self._do_fetch_url).pack(side=tk.LEFT, padx=2)

        self._refresh_data()

    # ─── 动态下拉更新 ───

    def _update_filter_values(self):
        from db import get_db
        conn = get_db()
        regions = [r[0] for r in conn.execute(
            "SELECT DISTINCT region FROM notices WHERE region != '' ORDER BY region").fetchall()]
        reg_clean = sorted(set((r or "").replace(" ", "") for r in regions if r and r not in ("—", "-")))
        self.filter_region["values"] = ["全部"] + reg_clean
        types = [t[0] for t in conn.execute(
            "SELECT DISTINCT notice_type FROM notices ORDER BY notice_type").fetchall()]
        self.filter_type["values"] = ["全部"] + [t for t in types if t]
        priorities = [p[0] for p in conn.execute(
            "SELECT DISTINCT priority FROM notices ORDER BY priority").fetchall()]
        self.filter_priority["values"] = ["全部"] + [p for p in priorities if p]
        conn.close()

    def _set_date_today(self):
        from datetime import date
        t = date.today().strftime("%Y-%m-%d")
        self.date_from_var.set(t)
        self.date_to_var.set(t)
        self._refresh_data()

    def _set_date_this_week(self):
        from datetime import date, timedelta
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        self.date_from_var.set(monday.strftime("%Y-%m-%d"))
        self.date_to_var.set(today.strftime("%Y-%m-%d"))
        self._refresh_data()

    def _set_date_last7days(self):
        from datetime import date, timedelta
        today = date.today()
        self.date_from_var.set((today - timedelta(days=7)).strftime("%Y-%m-%d"))
        self.date_to_var.set(today.strftime("%Y-%m-%d"))
        self._refresh_data()

    def _clear_date(self):
        self.date_from_var.set("")
        self.date_to_var.set("")
        self._refresh_data()

    def _reset_all_filters(self):
        self.search_var.set("")
        self.filter_region.set("全部")
        self.filter_type.set("全部")
        self.filter_priority.set("全部")
        self.filter_bid_var.set(False)
        self._clear_date()

    def _on_column_click(self, col: str):
        if self.sort_col == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_col = col
            self.sort_reverse = False
        for c in ("ID", "标题", "类型", "地区", "日期", "优先级", "评分", "可参与"):
            label = c
            if c == self.sort_col:
                label = f"{c} {'v' if self.sort_reverse else '^'}"
            self.tree.heading(c, text=label,
                              command=lambda x=c: self._on_column_click(x))
        self._refresh_data()

    def _refresh_data(self):
        self._update_filter_values()
        kw = self.search_var.get().strip()
        region = self.filter_region.get()
        ntype = self.filter_type.get()
        priority = self.filter_priority.get()
        bid_only = self.filter_bid_var.get()
        date_from = self.date_from_var.get().strip()
        date_to = self.date_to_var.get().strip()

        if kw:
            from search import search_filtered
            rows = search_filtered(
                kw,
                region="" if region == "全部" else region,
                notice_type="" if ntype == "全部" else ntype,
                can_bid_only=False,
            )
        else:
            rows = get_all_notices()

        filtered = []
        for r in rows:
            r_region = (r.get("region") or "").replace(" ", "")
            if region and region != "全部" and r_region != region.replace(" ", ""):
                continue
            if ntype and ntype != "全部" and r.get("notice_type", "") != ntype:
                continue
            if priority and priority != "全部" and r.get("priority", "") != priority:
                continue
            if bid_only and not r.get("can_bid"):
                continue
            pub_date = r.get("pub_date", "") or ""
            if date_from and pub_date < date_from:
                continue
            if date_to and pub_date > date_to:
                continue
            filtered.append(r)

        # 列名 → dict key 映射
        _col_key = {"ID": "id", "标题": "title", "类型": "notice_type",
                     "地区": "region", "日期": "pub_date", "优先级": "priority",
                     "评分": "score", "可参与": "can_bid"}
        _sort_key_col = _col_key.get(self.sort_col, self.sort_col)

        def _sort_key(r):
            val = r.get(_sort_key_col, "")
            if val is None:
                val = ""
            if self.sort_col == "评分":
                return float(r.get("score", 0))
            if self.sort_col == "ID":
                return int(r.get("id", 0))
            if self.sort_col == "可参与":
                return int(r.get("can_bid", 0))
            if self.sort_col == "日期":
                return str(val)
            return str(val).replace(" ", "")

        filtered.sort(key=_sort_key, reverse=self.sort_reverse)
        self._populate_tree(filtered)
        self._refresh_statusbar(showing=len(filtered))

    def _load_all(self):
        self._refresh_data()

    def _populate_tree(self, rows: list[dict]):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for r in rows:
            title = (r.get("title") or "").replace(" ", "")
            region = (r.get("region") or "—").replace(" ", "")
            notice_type = r.get("notice_type", "—")
            pub_date = r.get("pub_date", "—") or "—"
            priority = r.get("priority", "—")
            can_bid = "Y" if r.get("can_bid") else ""
            score = f"{r.get('score', 0):.0f}"

            tag = "high" if priority == "A级" else ("mid" if priority == "B级" else "ref")
            self.tree.insert("", tk.END,
                             values=(r["id"], title, notice_type, region,
                                    pub_date, priority, score, can_bid),
                             tags=(tag,))

        self.tree.tag_configure("high", background="#fde8e8")
        self.tree.tag_configure("mid", background="#fef3e2")
        self.tree.tag_configure("ref", background="#f8f8f8")

    def _show_detail(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先在表格中选中一条标讯")
            return

        nid = self.tree.item(sel[0], "values")[0]
        row = get_notice_by_id(int(nid))
        if not row:
            return

        title = (row.get("title") or "").replace(" ", "")
        content = (row.get("content") or "").replace(" ", "")

        win = tk.Toplevel(self.root)
        win.title("标讯详情")
        win.geometry("650x450")

        # 元数据区
        meta_frame = tk.Frame(win)
        meta_frame.pack(fill=tk.X, padx=8, pady=(8, 0))
        meta_text = tk.Text(meta_frame, font=FONT, height=4, wrap=tk.WORD)
        meta_text.pack(fill=tk.X)
        meta_text.insert(tk.END, f"【{title}】\n")
        for k in ["notice_type", "biz_type", "region", "publisher",
                   "budget", "pub_date", "priority", "stage", "score"]:
            val = row.get(k, "—") or "—"
            meta_text.insert(tk.END, f"{k}: {val}\n")

        # 原文链接
        url = row.get("url", "")
        if url:
            link_frame = tk.Frame(win)
            link_frame.pack(fill=tk.X, padx=8, pady=2)
            tk.Label(link_frame, text="原文链接:", font=FONT).pack(side=tk.LEFT)
            tk.Label(link_frame, text=url[:80], font=(FONT[0], 9),
                      fg="#2980b9", cursor="hand2").pack(side=tk.LEFT, padx=4)
            tk.Button(link_frame, text="在浏览器打开", font=(FONT[0], 9),
                      command=lambda u=url: __import__("webbrowser").open(u)).pack(
                          side=tk.LEFT, padx=4)

        # 正文区
        txt = scrolledtext.ScrolledText(win, font=FONT, wrap=tk.WORD)
        txt.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        txt.insert(tk.END, f"{content}")
        txt.configure(state=tk.NORMAL)  # 允许复制文字

    def _select_all(self):
        for item in self.tree.get_children():
            self.tree.selection_add(item)

    def _export_csv(self):
        import csv
        from datetime import datetime
        fname = f"标讯导出_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(fname, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["ID", "标题", "类型", "地区", "日期", "优先级", "评分", "可参与"])
            for item in self.tree.get_children():
                w.writerow(self.tree.item(item, "values"))
        messagebox.showinfo("导出", f"已保存到 {fname}")

    def _delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先选中要删除的标讯（Ctrl+点击多选，Shift+点击连续选，Ctrl+A 全选）")
            return

        ids = [int(self.tree.item(i, "values")[0]) for i in sel]
        titles = [self.tree.item(i, "values")[1] for i in sel]
        count = len(ids)

        # 确认弹窗：显示前 10 条标题
        preview_titles = "\n".join(f"  {t[:60]}" for t in titles[:10])
        if count > 10:
            preview_titles += f"\n  ... 还有 {count - 10} 条"

        if not messagebox.askyesno("确认批量删除",
                                   f"确定要删除以下 {count} 条标讯吗？\n\n{preview_titles}"):
            return

        n = delete_notices(ids)
        if n > 0:
            self._refresh_data()
            self._refresh_statusbar()

    def _open_source_manager(self):
        """弹窗：爬虫源管理"""
        from source_manager import list_sources, add_source, remove_source, toggle_source

        def refresh_list():
            src_list.delete(0, tk.END)
            for s in list_sources():
                status = "+" if s.get("enabled", True) else "-"
                src_list.insert(tk.END, f"[{status}] {s['name']}  ({s['type']})")

        win = tk.Toplevel(self.root)
        win.title("爬虫源管理")
        win.geometry("600x420")

        # 列表
        tk.Label(win, text="已配置的爬虫源：", font=FONT_BOLD).pack(padx=8, anchor=tk.W)
        src_list = tk.Listbox(win, font=("monospace", 9), height=10)
        src_list.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        refresh_list()

        btn_bar = tk.Frame(win)
        btn_bar.pack(fill=tk.X, padx=8, pady=2)
        tk.Button(btn_bar, text="启用/禁用", font=FONT,
                  command=lambda: _toggle()).pack(side=tk.LEFT)
        tk.Button(btn_bar, text="删除", font=FONT,
                  command=lambda: _delete()).pack(side=tk.LEFT, padx=4)

        # 添加表单
        frm = tk.Frame(win)
        frm.pack(fill=tk.X, padx=8, pady=8)
        tk.Label(frm, text="添加新源：", font=FONT_BOLD).pack(anchor=tk.W)

        row1 = tk.Frame(frm)
        row1.pack(fill=tk.X, pady=2)
        tk.Label(row1, text="名称:", font=FONT).pack(side=tk.LEFT)
        name_var = tk.StringVar()
        tk.Entry(row1, textvariable=name_var, font=FONT, width=20).pack(side=tk.LEFT, padx=2)
        tk.Label(row1, text="  URL:", font=FONT).pack(side=tk.LEFT)
        url_var = tk.StringVar()
        tk.Entry(row1, textvariable=url_var, font=FONT, width=30).pack(side=tk.LEFT, padx=2)

        row2 = tk.Frame(frm)
        row2.pack(fill=tk.X, pady=2)
        tk.Label(row2, text="类型:", font=FONT).pack(side=tk.LEFT)
        type_var = tk.StringVar(value="single")
        type_cb = ttk.Combobox(row2, textvariable=type_var,
                                values=["ggzy - 公共资源平台爬虫", "cebpubservice - 招标投标平台",
                                         "single - 单页正文抓取(trafilatura)"],
                                width=32, font=FONT, state="readonly")
        type_cb.pack(side=tk.LEFT, padx=2)

        # 说明文字
        tk.Label(frm, text="类型说明: ggzy=定向爬虫, single=只抓这一个URL的正文(不是爬虫!)",
                  font=(FONT[0], 8), fg="#999").pack(anchor=tk.W, pady=(2, 4))

        row3 = tk.Frame(frm)
        row3.pack(fill=tk.X, pady=2)
        tk.Label(row3, text="URL格式: 必须带 https:// 开头", font=(FONT[0], 9), fg="#c0392b").pack(anchor=tk.W)

        tk.Label(row2, text="  关键词:", font=FONT).pack(side=tk.LEFT)
        kw_var = tk.StringVar()
        tk.Entry(row2, textvariable=kw_var, font=FONT, width=12).pack(side=tk.LEFT, padx=2)

        tk.Button(frm, text="添加", font=FONT,
                  command=lambda: _add()).pack(pady=4)

        def _toggle():
            sel = src_list.curselection()
            if sel:
                line = src_list.get(sel[0])
                url = _url_from_line(line)
                if url:
                    toggle_source(url)
                    refresh_list()

        def _delete():
            sel = src_list.curselection()
            if sel:
                line = src_list.get(sel[0])
                url = _url_from_line(line)
                if url and messagebox.askyesno("确认", f"删除 {url[:60]}?"):
                    remove_source(url)
                    refresh_list()

        def _add():
            name = name_var.get().strip()
            url = url_var.get().strip()
            if not name or not url:
                return
            add_source(name, url, type_var.get(), kw_var.get().strip())
            name_var.set("")
            url_var.set("")
            kw_var.set("")
            refresh_list()

        def _url_from_line(line):
            for s in list_sources():
                if s.get('name') in line:
                    return s.get('url')
            return None

    def _do_crawl(self):
        """后台爬取 — 不弹窗，状态栏显示进度"""
        self._crawl_log_lines = ["正在爬取...\n"]
        self._set_crawl_status("正在爬取... 0 条", "#888")

        def log_cb(msg: str):
            self._crawl_log_lines.append(msg)
            # 从日志里提取进度 (如 "[1] 招标公告 ...")
            import re
            m = re.search(r'完成[：:]\s*抓取\s*(\d+)/(\d+)', msg)
            if m:
                self.root.after(0, lambda: self._set_crawl_status(
                    f"正在爬取... {m.group(1)}/{m.group(2)} 条", "#888"))
            if "完成" in msg and "抓取" in msg:
                parts = msg.split("完成：")
                if len(parts) > 1:
                    self.root.after(0, lambda: self._set_crawl_status(
                        f"正在爬取... {parts[1].strip()}", "#888"))

        def task():
            try:
                from source_manager import crawl_all_enabled
                results = crawl_all_enabled(log_callback=log_cb)
                total = sum(results.values())
                ok = "成功" if total > 0 else "无新数据"
                self._crawl_log_lines.append(f"\n总共入库: {total} 条新公告")
                self.root.after(0, lambda: [
                    self._load_all(),
                    self._refresh_statusbar(),
                    self._set_crawl_status(f"上次爬取: {ok} {total}条",
                                            "#27ae60" if total > 0 else "#888")
                ])
            except Exception as e:
                self._crawl_log_lines.append(f"\n[X] 爬取失败: {e}")
                self.root.after(0, lambda: self._set_crawl_status(
                    "上次爬取: 失败", "#c0392b"))
        threading.Thread(target=task, daemon=True).start()

    def _show_crawl_log(self):
        """弹出日志窗口 — 只有用户主动点击时"""
        log_win = tk.Toplevel(self.root)
        log_win.title("爬取日志")
        log_win.geometry("650x400")
        log_text = scrolledtext.ScrolledText(log_win, font=("monospace", 9), wrap=tk.WORD)
        log_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        lines = getattr(self, '_crawl_log_lines', [])
        if lines:
            log_text.insert(tk.END, "\n".join(lines))
        else:
            log_text.insert(tk.END, "暂无爬取记录。")

    def _do_fetch_url(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showinfo("提示", "请输入 URL")
            return
        self.url_entry.set("")
        # 异步抓取
        def task():
            try:
                from extractor import ingest_url
                ok = ingest_url(url)
                if ok:
                    self.root.after(0, lambda: [self._load_all(), self._refresh_statusbar()])
                else:
                    self.root.after(0, lambda: messagebox.showwarning(
                        "抓取失败", "无法提取正文。请确认:\n1. pip3 install trafilatura\n2. URL 可访问"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showwarning("错误", str(e)))
        threading.Thread(target=task, daemon=True).start()

    def _on_tree_double_click(self):
        sel = self.tree.selection()
        if sel:
            nid = int(self.tree.item(sel[0], "values")[0])
            self.bid_notice_id.set(str(nid))
            self.bid_title_var.set(self.tree.item(sel[0], "values")[1])
            self.notebook.select(1)

    # ═══════════════════════════════════════════
    # Tab2: 标书生成
    # ═══════════════════════════════════════════

    def _build_bid_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  标书生成  ")

        # 顶部：选择标讯
        top = tk.Frame(tab)
        top.pack(fill=tk.X, padx=8, pady=8)

        tk.Label(top, text="标讯 ID：", font=FONT).pack(side=tk.LEFT)
        self.bid_notice_id = tk.StringVar()
        tk.Entry(top, textvariable=self.bid_notice_id, font=FONT,
                  width=6).pack(side=tk.LEFT, padx=2)
        tk.Label(top, text="标题：", font=FONT).pack(side=tk.LEFT, padx=(8, 0))
        self.bid_title_var = tk.StringVar()
        tk.Entry(top, textvariable=self.bid_title_var, font=FONT,
                  state="readonly", width=55).pack(side=tk.LEFT, padx=2)

        tk.Button(top, text="去看板双击选标讯", font=FONT,
                  command=lambda: self.notebook.select(0)).pack(side=tk.LEFT, padx=8)
        tk.Button(top, text="载入标讯", font=FONT,
                  command=self._load_bid_notice).pack(side=tk.LEFT, padx=2)

        # 生成模式
        mode_frame = tk.Frame(tab)
        mode_frame.pack(fill=tk.X, padx=8, pady=4)

        tk.Label(mode_frame, text="生成模式：", font=FONT_BOLD).pack(side=tk.LEFT)
        self.bid_mode = tk.StringVar(value="template")
        tk.Radiobutton(mode_frame, text="模板模式（离线，纯本地）",
                        variable=self.bid_mode, value="template",
                        font=FONT).pack(side=tk.LEFT, padx=4)
        tk.Radiobutton(mode_frame, text="AI 增强（DeepSeek + 知识库）",
                        variable=self.bid_mode, value="ai",
                        font=FONT).pack(side=tk.LEFT, padx=4)

        tk.Button(mode_frame, text="查看知识库", font=(FONT[0], 9),
                  command=self._show_knowledge).pack(side=tk.LEFT, padx=(20, 4))
        tk.Button(mode_frame, text="导入文件", font=(FONT[0], 9),
                  command=self._import_knowledge).pack(side=tk.LEFT, padx=4)

        tk.Button(mode_frame, text=">> 生成标书 <<", font=FONT_BOLD,
                  command=self._gen_bid, bg="#2c3e50", fg="white",
                  padx=20).pack(side=tk.RIGHT, padx=8)

        # 预览区
        preview_frame = tk.Frame(tab)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        tk.Label(preview_frame, text="标书预览：", font=FONT_BOLD).pack(anchor=tk.W)
        self.bid_preview = scrolledtext.ScrolledText(preview_frame,
                                                      font=("monospace", 9),
                                                      wrap=tk.WORD)
        self.bid_preview.pack(fill=tk.BOTH, expand=True, pady=4)

        btn_frame = tk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=8, pady=4)
        tk.Button(btn_frame, text="导出 .md", font=FONT,
                  command=self._export_bid).pack(side=tk.LEFT)

    def _load_bid_notice(self):
        nid_str = self.bid_notice_id.get().strip()
        if not nid_str:
            return
        row = get_notice_by_id(int(nid_str))
        if row:
            self.bid_title_var.set((row.get("title") or "").replace(" ", ""))
        else:
            messagebox.showwarning("提示", f"标讯 ID={nid_str} 不存在")

    def _show_knowledge(self):
        """弹窗展示知识库所有文件内容"""
        win = tk.Toplevel(self.root)
        win.title("知识库浏览器")
        win.geometry("700x500")

        # 左侧文件列表，右侧内容
        paned = tk.PanedWindow(win, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        left = tk.Frame(paned, width=180)
        paned.add(left)
        right = tk.Frame(paned)
        paned.add(right)

        # 文件列表
        tk.Label(left, text="知识库文件", font=FONT_BOLD).pack(pady=4)
        file_list = tk.Listbox(left, font=(FONT[0], 9), width=25)
        file_list.pack(fill=tk.BOTH, expand=True, padx=4)

        # 内容预览
        preview = scrolledtext.ScrolledText(right, font=("monospace", 9), wrap=tk.WORD)
        preview.pack(fill=tk.BOTH, expand=True)

        # 收集所有知识库文件
        import glob
        kb_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge")
        files = []
        for ext in ("*.yml", "*.yaml", "*.json", "*.md"):
            for p in glob.glob(os.path.join(kb_dir, "**", ext), recursive=True):
                rel = os.path.relpath(p, kb_dir)
                files.append((rel, p))

        for rel, full in sorted(files):
            file_list.insert(tk.END, rel)

        def on_select(e=None):
            sel = file_list.curselection()
            if not sel:
                return
            rel = file_list.get(sel[0])
            full = os.path.join(kb_dir, rel)
            preview.delete(1.0, tk.END)
            try:
                with open(full, "r", encoding="utf-8") as f:
                    preview.insert(tk.END, f.read())
            except Exception:
                preview.insert(tk.END, "[无法读取]")
            preview.insert(tk.END, f"\n\n── 文件路径: knowledge/{rel} ──")

        file_list.bind("<<ListboxSelect>>", on_select)

    def _import_knowledge(self):
        """文件导入对话框 → 自动转格式 → knowledge/imported/"""
        from tkinter import filedialog
        from knowledge_importer import import_file

        paths = filedialog.askopenfilenames(
            title="选择要导入的知识库文件",
            filetypes=[
                ("所有支持格式", "*.md *.yml *.yaml *.json *.pdf *.docx *.txt"),
                ("Markdown", "*.md"),
                ("PDF", "*.pdf"),
                ("Word", "*.docx"),
                ("文本", "*.txt"),
                ("YAML/JSON", "*.yml *.yaml *.json"),
            ])
        if not paths:
            return

        ok, fail = 0, 0
        for p in paths:
            result = import_file(p)
            if result:
                ok += 1
            else:
                fail += 1

        if fail:
            messagebox.showinfo("导入完成",
                f"成功 {ok} 个文件\n失败 {fail} 个（可能是格式不支持或文件损坏）\n\n"
                f"导入目录: knowledge/imported/")
        else:
            messagebox.showinfo("导入完成",
                f"成功导入 {ok} 个文件\n导入目录: knowledge/imported/")

    def _gen_bid(self):
        nid_str = self.bid_notice_id.get().strip()
        if not nid_str:
            messagebox.showinfo("提示", "请先输入标讯 ID")
            return

        mode = self.bid_mode.get()
        self.bid_preview.delete(1.0, tk.END)
        self.bid_preview.insert(tk.END, "正在生成标书，请稍候...\n")

        if mode == "template":
            def task():
                try:
                    result = gen_bid_template(int(nid_str))
                    self.root.after(0, lambda: self._show_bid_result(result))
                except Exception as e:
                    self.root.after(0, lambda: self._show_bid_result(f"[X] 生成失败：{e}"))
        else:
            def task():
                try:
                    result = gen_bid_ai(int(nid_str))
                    self.root.after(0, lambda: self._show_bid_result(result))
                except Exception as e:
                    self.root.after(0, lambda: self._show_bid_result(f"[X] AI 生成失败：{e}"))

        threading.Thread(target=task, daemon=True).start()

    def _show_bid_result(self, text: str):
        self.bid_preview.delete(1.0, tk.END)
        self.bid_preview.insert(tk.END, text)

    def _export_bid(self):
        content = self.bid_preview.get(1.0, tk.END).strip()
        if not content:
            return
        from tkinter import filedialog
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = filedialog.asksaveasfilename(
            title="保存标书",
            defaultextension=".md",
            initialfile=f"投标书_{ts}.md",
            filetypes=[("Markdown", "*.md"), ("文本文件", "*.txt"), ("所有文件", "*.*")])
        if not fname:
            return
        with open(fname, "w", encoding="utf-8") as f:
            f.write(content)
        messagebox.showinfo("导出", f"已保存到 {fname}")

    # ═══════════════════════════════════════════
    # Tab3: AI 分析
    # ═══════════════════════════════════════════

    def _build_ai_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  AI 分析  ")

        # 左侧操作区
        left = tk.Frame(tab, width=280)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)
        left.pack_propagate(False)

        # AI 状态 + 设置
        status_frame = tk.Frame(left)
        status_frame.pack(fill=tk.X, pady=(0, 8))

        from ai import is_ready, get_config
        self.ai_status_label = tk.Label(status_frame, font=(FONT[0], 9))
        self.ai_status_label.pack(side=tk.LEFT)
        tk.Button(status_frame, text="AI 设置", font=FONT,
                  command=self._open_ai_settings).pack(side=tk.RIGHT)
        self._update_ai_status()

        tk.Label(left, text="AI 分析工具", font=FONT_TITLE).pack(anchor=tk.W, pady=(0, 12))

        buttons = [
            ("深度分析单条标讯", self._ai_analyze_one, "选中标讯进行五维度深度评估"),
            ("标讯排名推荐", self._ai_rank, "基于评分标准排序 Top 5 推荐"),
            ("生成本周周报", self._ai_weekly, "本周标讯概览 + 趋势 + 行动建议"),
            ("自由提问", self._ai_ask, "基于数据库真实数据回答你的问题"),
        ]

        self.ai_buttons = []
        for label, cmd, desc in buttons:
            frm = tk.Frame(left, bd=1, relief=tk.SOLID, padx=8, pady=6)
            frm.pack(fill=tk.X, pady=3)
            btn = tk.Button(frm, text=label, font=FONT, command=cmd,
                             bg="#2c3e50", fg="white")
            btn.pack(fill=tk.X)
            self.ai_buttons.append(btn)
            tk.Label(frm, text=desc, font=(FONT[0], 8), fg="#666").pack(anchor=tk.W)
        self._update_ai_buttons()

        tk.Label(left, text="\n标讯 ID（深度分析用）：", font=FONT).pack(anchor=tk.W)
        self.ai_notice_id = tk.StringVar()
        tk.Entry(left, textvariable=self.ai_notice_id, font=FONT, width=10).pack(anchor=tk.W, pady=2)

        tk.Label(left, text="\n自由提问：", font=FONT).pack(anchor=tk.W)
        self.ai_question = tk.StringVar()
        tk.Entry(left, textvariable=self.ai_question, font=FONT).pack(fill=tk.X, pady=2)
        tk.Label(left, text="\n例：四川有什么停车项目可投？",
                  font=(FONT[0], 8), fg="#999").pack(anchor=tk.W)

        # 右侧输出区
        right = tk.Frame(tab)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8), pady=8)

        tk.Label(right, text="分析结果：", font=FONT_BOLD).pack(anchor=tk.W)
        self.ai_output = scrolledtext.ScrolledText(right, font=("monospace", 9),
                                                    wrap=tk.WORD)
        self.ai_output.pack(fill=tk.BOTH, expand=True, pady=4)
        tk.Button(right, text="清空", font=FONT,
                  command=lambda: self.ai_output.delete(1.0, tk.END)).pack(anchor=tk.E)

    def _update_ai_status(self):
        from ai import is_ready, get_config
        if is_ready():
            cfg = get_config()
            self.ai_status_label.configure(
                text=f"已配置 ({cfg['model']})", fg="#27ae60")
        else:
            self.ai_status_label.configure(
                text="未配置 API Key", fg="#999")

    def _update_ai_buttons(self):
        from ai import is_ready
        state = tk.NORMAL if is_ready() else tk.DISABLED
        for btn in self.ai_buttons:
            btn.configure(state=state)

    @staticmethod
    def _load_user_models():
        """加载用户自定义模型列表 [(mid, label, url), ...]"""
        try:
            path = os.path.join(os.path.expanduser("~"), ".bid_tool", "ai_user_models.yml")
            with open(path, "r", encoding="utf-8") as f:
                import yaml
                return yaml.safe_load(f) or []
        except Exception:
            return []

    @staticmethod
    def _save_user_model(mid: str, url: str):
        """添加一个自定义模型到持久化列表"""
        models = BidToolApp._load_user_models()
        for m in models:
            if m[0] == mid:
                return  # 已存在
        name = mid if len(mid) <= 20 else mid[:17] + "..."
        models.append([mid, name, url])
        try:
            import yaml
            path = os.path.join(os.path.expanduser("~"), ".bid_tool", "ai_user_models.yml")
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(models, f, allow_unicode=True)
        except Exception:
            pass

    def _open_ai_settings(self):
        from ai import get_config, update_config, test_connection, is_ready
        import yaml, os

        win = tk.Toplevel(self.root)
        win.title("AI 配置")
        win.geometry("480x400")
        win.resizable(False, False)

        cfg = get_config()

        tk.Label(win, text="AI API 配置", font=FONT_TITLE).pack(pady=8)

        frm = tk.Frame(win)
        frm.pack(padx=16, pady=8, fill=tk.X)

        tk.Label(frm, text="API Key:", font=FONT).pack(anchor=tk.W)
        key_var = tk.StringVar(value=cfg["key"])
        key_entry = tk.Entry(frm, textvariable=key_var, font=FONT, width=45, show="*")
        key_entry.pack(fill=tk.X, pady=2)
        tk.Label(frm, text="注册获取: https://platform.deepseek.com/",
                  font=(FONT[0], 8), fg="#999").pack(anchor=tk.W)

        # 预定义模型列表 — 加载已保存的自定义模型
        BUILTIN_PRESETS = [
            ("deepseek-chat", "DeepSeek V3", "https://api.deepseek.com"),
            ("deepseek-reasoner", "DeepSeek R1 (推理)", "https://api.deepseek.com"),
            ("qwen-max", "通义千问 Max", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            ("qwen-plus", "通义千问 Plus", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            ("gpt-4o", "GPT-4o", "https://api.openai.com/v1"),
            ("gpt-4o-mini", "GPT-4o Mini", "https://api.openai.com/v1"),
            ("", "—— 本地/自定义 ——", ""),
        ]
        # 加载用户自定义模型
        user_presets = [(m[0], m[1], m[2]) for m in BidToolApp._load_user_models()]
        PRESETS = BUILTIN_PRESETS[:-1] + user_presets + [BUILTIN_PRESETS[-1]]

        preset_labels = [f"{label} ({mid})" if mid else label for mid, label, _ in PRESETS]

        tk.Label(frm, text="\nBase URL:", font=FONT).pack(anchor=tk.W)
        url_var = tk.StringVar(value=cfg["url"])
        tk.Entry(frm, textvariable=url_var, font=FONT, width=45).pack(fill=tk.X, pady=2)

        tk.Label(frm, text="\nModel:", font=FONT).pack(anchor=tk.W)

        # _model_id[0] = 实际传给API的模型名（纯ID），model_var = Combobox显示用
        _model_id = [cfg["model"]]
        model_var = tk.StringVar(value=cfg["model"])
        model_cb = ttk.Combobox(frm, textvariable=model_var, values=preset_labels,
                                 font=FONT, width=43)
        model_cb.pack(fill=tk.X, pady=2)
        tk.Label(frm, text="选预设或用下拉选「自定义」后输入模型名 + URL，保存即加入列表",
                  font=(FONT[0], 8), fg="#999").pack(anchor=tk.W)

        # 如果已保存的 model 匹配预设法，显示漂亮名称；实际ID保持不变
        for mid, label, _ in PRESETS:
            if cfg["model"] == mid and mid:
                model_var.set(f"{label} ({mid})")
                break

        def on_model_selected(e=None):
            sel = model_cb.get()
            if not sel or sel.startswith("——"):
                return
            for mid, label, url in PRESETS:
                if mid and f"({mid})" in sel:
                    url_var.set(url)
                    _model_id[0] = mid           # ← 纯ID
                    model_var.set(f"{label} ({mid})")  # ← 漂亮显示
                    return
            # 未匹配预设 → 用户自定义输入
            _model_id[0] = sel.strip()
            model_var.set(sel.strip())

        model_cb.bind("<<ComboboxSelected>>", on_model_selected)

        # 手动输入时，同步 _model_id 为纯文本（去掉可能的括号后缀）
        def _sync_model_id(*_args):
            val = model_var.get().strip()
            for mid, label, _ in PRESETS:
                if mid and f"({mid})" in val:
                    return  # 是预设格式，不覆盖 _model_id（由 on_selected 控制）
            _model_id[0] = val
        model_var.trace_add("write", _sync_model_id)

        # 状态反馈标签 — 先 pack 保证 on_test 闭包能访问
        status_lbl = tk.Label(frm, text="", font=(FONT[0], 9), pady=4)
        status_lbl.pack()

        # 按钮
        btn_frm = tk.Frame(frm)
        btn_frm.pack(pady=8)

        def on_test():
            status_lbl.configure(text="测试中...", fg="#666")
            win.update()
            # 用实际 model ID，不是 Combobox 显示名
            test_model = _model_id[0]
            result = test_connection(key_var.get(), url_var.get(), test_model)
            color = "#27ae60" if "成功" in result else "#c0392b"
            status_lbl.configure(text=result, fg=color)

        def on_save():
            mid_to_save = _model_id[0] if _model_id[0] else model_var.get().strip()

            update_config(key_var.get(), url_var.get(), mid_to_save)

            # 保存自定义模型到持久化列表
            if mid_to_save and not any(mid_to_save == m for m, _, _ in BUILTIN_PRESETS if m):
                BidToolApp._save_user_model(mid_to_save, url_var.get().strip())

            self._update_ai_status()
            self._update_ai_buttons()
            messagebox.showinfo("已保存", "AI 配置已更新")
            win.destroy()

        tk.Button(btn_frm, text="测试连接", font=FONT, command=on_test).pack(
            side=tk.LEFT, padx=4)
        tk.Button(btn_frm, text="保存", font=FONT_BOLD, command=on_save,
                   bg="#2c3e50", fg="white").pack(side=tk.LEFT, padx=4)

    def _set_ai_output(self, text: str):
        self.ai_output.delete(1.0, tk.END)
        self.ai_output.insert(tk.END, text)

    def _append_ai_output(self, label: str, text: str):
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M")
        sep = "-" * 50
        self.ai_output.insert(tk.END, f"\n[{ts}] {label}\n{sep}\n{text}\n")
        self.ai_output.see(tk.END)

    def _run_ai_task(self, task_fn, label: str, loading_text: str):
        self.ai_output.insert(tk.END, f"[{loading_text}]\n")
        self.ai_output.see(tk.END)
        def work():
            try:
                r = task_fn()
                self.root.after(0, lambda: self._append_ai_output(label, r))
            except Exception as e:
                self.root.after(0, lambda: self._append_ai_output(label, f"[X] {e}"))
        threading.Thread(target=work, daemon=True).start()

    def _ai_analyze_one(self):
        nid = self.ai_notice_id.get().strip()
        if not nid:
            messagebox.showinfo("提示", "请先输入标讯 ID")
            return
        self._run_ai_task(lambda: analyze_one(int(nid)), "深度分析", "AI 分析中...")

    def _ai_rank(self):
        self._run_ai_task(rank_opportunities, "标讯排名", "AI 排名中...")

    def _ai_weekly(self):
        self._run_ai_task(weekly_report, "本周周报", "AI 生成周报中...")

    def _ai_ask(self):
        q = self.ai_question.get().strip()
        if not q:
            messagebox.showinfo("提示", "请先输入问题")
            return
        self._run_ai_task(lambda: ask(q), f"提问: {q[:30]}", "AI 思考中...")

    # ═══════════════════════════════════════════
    # 底部状态栏
    # ═══════════════════════════════════════════

    def _build_statusbar(self):
        self.status_frame = tk.Frame(self.root, bg="#f0f0f0", height=28)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_labels = {}
        for key, color in [("showing", "#333"), ("can_bid", "#27ae60"), ("high_priority", "#c0392b"), ("crawl_status", "#888")]:
            lbl = tk.Label(self.status_frame, font=(FONT[0], 9), bg="#f0f0f0", fg=color)
            lbl.pack(side=tk.LEFT, padx=12)
            self.status_labels[key] = lbl

    def _refresh_statusbar(self, showing: int = 0):
        try:
            s = get_stats()
            total = s['total']
            if showing > 0:
                self.status_labels["showing"].configure(
                    text=f"显示：{showing}/{total} 条")
            else:
                self.status_labels["showing"].configure(
                    text=f"总标讯：{total} 条")
            self.status_labels["can_bid"].configure(
                text=f"可投标：{s['can_bid']} 条")
            self.status_labels["high_priority"].configure(
                text=f"高优：{s['high_priority']} 条")
        except Exception:
            pass

    def _set_crawl_status(self, text: str, color: str = "#888"):
        try:
            self.status_labels["crawl_status"].configure(text=text, fg=color)
        except Exception:
            pass

    def run(self):
        self.root.mainloop()


# ── 入口 ─────────────────────────────────────────────────

def main():
    user_dir = os.path.join(os.path.expanduser("~"), ".bid_tool")
    os.makedirs(os.path.join(user_dir, "data"), exist_ok=True)
    os.makedirs(os.path.join(user_dir, "knowledge"), exist_ok=True)

    # 首次运行：建库 + 种子数据
    if not os.path.exists(DB_PATH):
        print("首次运行，正在初始化数据库...")
        init_database()
        seed_data()

    # 首次运行：复制知识库模板
    kb_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge")
    kb_dst = os.path.join(user_dir, "knowledge")
    if os.path.exists(kb_src) and not os.listdir(kb_dst):
        print("正在复制知识库...")
        for item in os.listdir(kb_src):
            s = os.path.join(kb_src, item)
            d = os.path.join(kb_dst, item)
            if os.path.isdir(s): shutil.copytree(s, d, dirs_exist_ok=True)
            else: shutil.copy2(s, d)

    # 首次运行：复制默认配置
    for fname in ["sources.yml", "ai.yml"]:
        cfg_dst = os.path.join(user_dir, fname)
        cfg_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), fname)
        if not os.path.exists(cfg_dst) and os.path.exists(cfg_src):
            shutil.copy2(cfg_src, cfg_dst)

    root = tk.Tk()
    app = BidToolApp(root)
    app.run()


if __name__ == "__main__":
    main()
