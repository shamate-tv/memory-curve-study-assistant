# -*- coding: utf-8 -*-
"""记忆曲线 · 高中必修一/二知识点复习助手

一个帮助高中生安排主科复习计划的桌面程序：
- 用 json 保存学习卡片；
- 用间隔重复算法安排复习；
- 用 tkinter 做图形界面。
"""

import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime, timedelta

import notifier
import scheduler
import storage
import task_scheduler

SUBJECTS = ["语文", "数学", "英语", "物理", "化学", "生物", "政治", "历史", "地理", "其他"]
BOOKS = ["必修一", "必修二"]
RATING_NAMES = {
    scheduler.RATING_FORGOT: "忘记",
    scheduler.RATING_VAGUE: "模糊",
    scheduler.RATING_KNOWN: "记住",
}


class ReviewApp(tk.Tk):
    """主窗口。"""

    def __init__(self):
        super().__init__()
        self.title("记忆曲线 · 高中必修一/二知识点复习助手")
        self.geometry("1120x780")
        self.minsize(1000, 680)
        self.configure(bg="#eef2f7")

        self.settings = storage.load_settings()
        self.dark_mode = bool(self.settings.get("dark_mode", False))
        self.daily_new_limit = int(self.settings.get("daily_new_limit", 20) or 20)
        self.daily_review_limit = int(self.settings.get("daily_review_limit", 100) or 0)
        self.daily_stats = storage.load_daily_stats()
        self.spark = storage.load_spark()
        self.cards = storage.load_cards()
        self.current_due = []
        self.current_index = 0
        self.current_card = None
        self.answer_visible = False

        self._build_style()
        self._build_header()
        self._build_stats_bar()
        self._build_notebook()
        self.apply_theme()
        self.refresh_all()

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(500, self.show_startup_reminder)
        self.after(1000, self._check_reminder_loop)

    def _build_style(self):
        self.style = ttk.Style(self)
        style = self.style
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TNotebook", background="#eef2f7", borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            padding=(18, 10),
            font=("Microsoft YaHei", 11),
            background="#dbe4f0",
            foreground="#334155",
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#ffffff")],
            foreground=[("selected", "#1d4ed8")],
        )
        style.configure(
            "Treeview",
            rowheight=30,
            font=("Microsoft YaHei", 10),
            background="#ffffff",
            fieldbackground="#ffffff",
        )
        style.configure(
            "Treeview.Heading",
            font=("Microsoft YaHei", 10, "bold"),
            background="#dbe4f0",
            foreground="#1e293b",
        )
        style.configure("TCombobox", padding=4)
        style.configure("TButton", padding=6, font=("Microsoft YaHei", 10))

    def _build_header(self):
        header = tk.Frame(self, bg="#1e3a8a", height=92)
        header.pack(fill="x")
        header.pack_propagate(False)

        title = tk.Label(
            header,
            text="记忆曲线 · 主科知识复习助手",
            bg="#1e3a8a",
            fg="#ffffff",
            font=("Microsoft YaHei", 22, "bold"),
        )
        title.pack(anchor="w", padx=24, pady=(16, 2))

        subtitle = tk.Label(
            header,
            text="高中必修一、二知识点 · 间隔重复算法 · 帮你安排每天的复习计划",
            bg="#1e3a8a",
            fg="#bfdbfe",
            font=("Microsoft YaHei", 11),
        )
        subtitle.pack(anchor="w", padx=24)

    def _build_stats_bar(self):
        bar = tk.Frame(self, bg="#eef2f7")
        bar.pack(fill="x", padx=18, pady=(12, 0))

        self.var_total = tk.StringVar(value="0")
        self.var_due = tk.StringVar(value="0")
        self.var_mastered = tk.StringVar(value="0")
        self.var_accuracy = tk.StringVar(value="0%")
        self.var_spark = tk.StringVar(value="0 天")

        items = [
            ("总卡片", self.var_total, "#2563eb"),
            ("今日待复习", self.var_due, "#ea580c"),
            ("已掌握", self.var_mastered, "#16a34a"),
            ("总正确率", self.var_accuracy, "#7c3aed"),
            ("🔥 火花", self.var_spark, "#f97316"),
        ]

        for label, variable, color in items:
            card = tk.Frame(bar, bg="#ffffff", highlightbackground="#dbe4f0", highlightthickness=1)
            card.pack(side="left", fill="x", expand=True, padx=(0, 10))
            tk.Label(
                card,
                text=label,
                bg="#ffffff",
                fg="#64748b",
                font=("Microsoft YaHei", 10),
            ).pack(anchor="w", padx=14, pady=(10, 0))
            tk.Label(
                card,
                textvariable=variable,
                bg="#ffffff",
                fg=color,
                font=("Microsoft YaHei", 20, "bold"),
            ).pack(anchor="w", padx=14, pady=(0, 10))

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=18, pady=12)

        self.review_tab = tk.Frame(self.notebook, bg="#ffffff")
        self.manage_tab = tk.Frame(self.notebook, bg="#ffffff")
        self.stats_tab = tk.Frame(self.notebook, bg="#ffffff")
        self.help_tab = tk.Frame(self.notebook, bg="#ffffff")
        self.settings_tab = tk.Frame(self.notebook, bg="#ffffff")
        self.basis_tab = tk.Frame(self.notebook, bg="#ffffff")

        self.notebook.add(self.review_tab, text="今日复习")
        self.notebook.add(self.manage_tab, text="卡片管理")
        self.notebook.add(self.stats_tab, text="学习统计")
        self.notebook.add(self.basis_tab, text="算法依据")
        self.notebook.add(self.settings_tab, text="设置")
        self.notebook.add(self.help_tab, text="使用说明")

        self._build_review_tab()
        self._build_manage_tab()
        self._build_stats_tab()
        self._build_basis_tab()
        self._build_settings_tab()
        self._build_help_tab()

    # 后续方法会在文件中继续补充
    def _build_review_tab(self):
        wrap = tk.Frame(self.review_tab, bg="#ffffff")
        wrap.pack(fill="both", expand=True, padx=20, pady=18)

        top = tk.Frame(wrap, bg="#ffffff")
        top.pack(fill="x")

        progress_row = tk.Frame(wrap, bg="#ffffff")
        progress_row.pack(fill="x", pady=(10, 0))

        self.progress_text = tk.Label(
            progress_row,
            text="今日进度：0 / 0",
            bg="#ffffff",
            fg="#475569",
            font=("Microsoft YaHei", 10),
        )
        self.progress_text.pack(side="left")

        self.progress_bar = ttk.Progressbar(
            progress_row,
            orient="horizontal",
            mode="determinate",
            maximum=100,
            value=0,
        )
        self.progress_bar.pack(side="right", fill="x", expand=True, padx=(12, 0))

        self.review_progress = tk.Label(
            top,
            text="0 / 0",
            bg="#ffffff",
            fg="#1d4ed8",
            font=("Microsoft YaHei", 11, "bold"),
        )
        self.review_progress.pack(side="left")

        self.review_feedback = tk.Label(
            top,
            text="",
            bg="#ffffff",
            fg="#16a34a",
            font=("Microsoft YaHei", 10),
        )
        self.review_feedback.pack(side="right")

        self.review_meta = tk.Label(
            wrap,
            text="",
            bg="#ffffff",
            fg="#64748b",
            font=("Microsoft YaHei", 11),
            anchor="w",
        )
        self.review_meta.pack(fill="x", pady=(8, 10))

        question_box = tk.Frame(
            wrap,
            bg="#f8fafc",
            highlightbackground="#cbd5e1",
            highlightthickness=1,
        )
        question_box.pack(fill="x", pady=(0, 10))

        tk.Label(
            question_box,
            text="问题",
            bg="#f8fafc",
            fg="#2563eb",
            font=("Microsoft YaHei", 10, "bold"),
        ).pack(anchor="w", padx=14, pady=(12, 4))

        self.question_text = tk.Text(
            question_box,
            height=4,
            wrap="word",
            bd=0,
            bg="#f8fafc",
            fg="#0f172a",
            font=("Microsoft YaHei", 14),
            padx=14,
            pady=4,
            state="disabled",
        )
        self.question_text.pack(fill="x")

        self.answer_frame = tk.Frame(
            wrap,
            bg="#ecfdf5",
            highlightbackground="#86efac",
            highlightthickness=1,
        )
        tk.Label(
            self.answer_frame,
            text="答案",
            bg="#ecfdf5",
            fg="#15803d",
            font=("Microsoft YaHei", 10, "bold"),
        ).pack(anchor="w", padx=14, pady=(12, 4))
        self.answer_text = tk.Text(
            self.answer_frame,
            height=6,
            wrap="word",
            bd=0,
            bg="#ecfdf5",
            fg="#14532d",
            font=("Microsoft YaHei", 13),
            padx=14,
            pady=4,
            state="disabled",
        )
        self.answer_text.pack(fill="x")

        button_row = tk.Frame(wrap, bg="#ffffff")
        button_row.pack(fill="x", pady=(14, 0))

        self.show_answer_btn = tk.Button(
            button_row,
            text="显示答案",
            command=self.show_answer,
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            relief="flat",
            font=("Microsoft YaHei", 11, "bold"),
            padx=18,
            pady=8,
            cursor="hand2",
        )
        self.show_answer_btn.pack(side="left")

        self.skip_btn = tk.Button(
            button_row,
            text="跳过这张",
            command=self.skip_current,
            bg="#e2e8f0",
            fg="#334155",
            activebackground="#cbd5e1",
            relief="flat",
            font=("Microsoft YaHei", 10),
            padx=14,
            pady=8,
            cursor="hand2",
        )
        self.skip_btn.pack(side="left", padx=(10, 0))

        self.refresh_due_btn = tk.Button(
            button_row,
            text="刷新队列",
            command=self.refresh_due,
            bg="#e2e8f0",
            fg="#334155",
            activebackground="#cbd5e1",
            relief="flat",
            font=("Microsoft YaHei", 10),
            padx=14,
            pady=8,
            cursor="hand2",
        )
        self.refresh_due_btn.pack(side="left", padx=(10, 0))

        self.rating_frame = tk.Frame(wrap, bg="#ffffff")
        self.rating_frame.pack(fill="x", pady=(14, 0))

        self.rate_buttons = {}
        rating_items = [
            (scheduler.RATING_FORGOT, "忘记", "#dc2626", "#b91c1c"),
            (scheduler.RATING_VAGUE, "模糊", "#f59e0b", "#d97706"),
            (scheduler.RATING_KNOWN, "记住", "#16a34a", "#15803d"),
        ]
        for rating, text, color, active_color in rating_items:
            button = tk.Button(
                self.rating_frame,
                text=text,
                command=lambda value=rating: self.rate_current(value),
                bg=color,
                fg="#ffffff",
                activebackground=active_color,
                activeforeground="#ffffff",
                relief="flat",
                font=("Microsoft YaHei", 11, "bold"),
                padx=22,
                pady=9,
                cursor="hand2",
                state="disabled",
            )
            button.pack(side="left", padx=(0, 10))
            self.rate_buttons[rating] = button

        tip = tk.Label(
            wrap,
            text="规则：忘记 1 天后复习；模糊间隔延长到 1.6 倍；记住间隔延长到 2.2 倍，最长 180 天。",
            bg="#ffffff",
            fg="#94a3b8",
            font=("Microsoft YaHei", 10),
            anchor="w",
        )
        tip.pack(fill="x", pady=(16, 0))

    def _set_text(self, widget, text):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _set_rating_buttons_state(self, state):
        for button in self.rate_buttons.values():
            button.configure(state=state)

    def refresh_due(self):
        self.daily_stats = storage.load_daily_stats()
        self.current_due = scheduler.select_daily_cards(
            self.cards,
            daily_new_limit=self.daily_new_limit,
            daily_review_limit=self.daily_review_limit,
            daily_stats=self.daily_stats,
        )
        self.current_index = 0
        self.answer_visible = False
        self.load_current_card()
        self.update_stats_bar()
        self.update_daily_progress_label()
        self._refresh_spark()
        self.update_progress_bar()

    def load_current_card(self):
        if not self.current_due:
            self.current_card = None
            self.review_meta.configure(text="今日没有待复习卡片，去“卡片管理”里添加或等待下次复习。")
            self._set_text(self.question_text, "今天的复习任务已完成，明天继续续火花。")
            self._set_text(self.answer_text, "")
            self.answer_frame.pack_forget()
            self.show_answer_btn.configure(state="disabled")
            self._set_rating_buttons_state("disabled")
            self.review_progress.configure(text="0 / 0")
            return

        if self.current_index >= len(self.current_due):
            self.current_index = 0

        self.current_card = self.current_due[self.current_index]
        card = self.current_card
        self.review_meta.configure(
            text=f"{card.get('subject', '未分类')} · {card.get('book', '')} · {card.get('chapter', '')}"
        )
        self._set_text(self.question_text, card.get("question", ""))
        self._set_text(self.answer_text, "")
        self.answer_frame.pack_forget()
        self.answer_visible = False
        self.show_answer_btn.configure(state="normal")
        self._set_rating_buttons_state("disabled")
        self.review_progress.configure(
            text=f"{self.current_index + 1} / {len(self.current_due)}"
        )

    def show_answer(self):
        if not self.current_card:
            return
        self._set_text(self.answer_text, self.current_card.get("answer", ""))
        self.answer_frame.pack(fill="x", pady=(0, 4))
        self.answer_visible = True
        self.show_answer_btn.configure(state="disabled")
        self._set_rating_buttons_state("normal")

    def rate_current(self, rating):
        if not self.current_card or not self.answer_visible:
            return

        card = self.current_card
        is_new_card = not bool(card.get("first_review"))
        was_first_today = (
            int(self.daily_stats.get("new_count", 0) or 0)
            + int(self.daily_stats.get("review_count", 0) or 0)
        ) == 0
        scheduler.review_card(card, rating)

        if is_new_card:
            self.daily_stats["new_count"] = int(self.daily_stats.get("new_count", 0) or 0) + 1
        else:
            self.daily_stats["review_count"] = int(self.daily_stats.get("review_count", 0) or 0) + 1
        if was_first_today:
            self._update_spark_on_study()
        storage.save_daily_stats(self.daily_stats)
        storage.save_cards(self.cards)

        self.review_feedback.configure(
            text=f"已记录：{RATING_NAMES[rating]}，下次约 {card.get('interval', 0)} 天后复习。"
        )
        self.current_due = [item for item in self.current_due if item is not card]
        self.current_index = 0
        self.answer_visible = False
        self.load_current_card()
        self.update_stats_bar()
        self.update_daily_progress_label()
        self._refresh_spark()
        self.update_progress_bar()

    def skip_current(self):
        if not self.current_card or len(self.current_due) <= 1:
            return
        self.current_due.append(self.current_due.pop(self.current_index))
        self.current_index = 0
        self.answer_visible = False
        self.load_current_card()
    def _build_manage_tab(self):
        wrap = tk.Frame(self.manage_tab, bg="#ffffff")
        wrap.pack(fill="both", expand=True, padx=18, pady=14)

        filter_row = tk.Frame(wrap, bg="#ffffff")
        filter_row.pack(fill="x", pady=(0, 10))

        tk.Label(
            filter_row,
            text="科目",
            bg="#ffffff",
            fg="#475569",
            font=("Microsoft YaHei", 10),
        ).pack(side="left")

        self.filter_subject = ttk.Combobox(
            filter_row,
            values=["全部"] + SUBJECTS,
            state="readonly",
            width=10,
        )
        self.filter_subject.set("全部")
        self.filter_subject.pack(side="left", padx=(6, 14))

        tk.Label(
            filter_row,
            text="教材",
            bg="#ffffff",
            fg="#475569",
            font=("Microsoft YaHei", 10),
        ).pack(side="left")

        self.filter_book = ttk.Combobox(
            filter_row,
            values=["全部"] + BOOKS,
            state="readonly",
            width=10,
        )
        self.filter_book.set("全部")
        self.filter_book.pack(side="left", padx=(6, 14))

        tk.Label(
            filter_row,
            text="搜索",
            bg="#ffffff",
            fg="#475569",
            font=("Microsoft YaHei", 10),
        ).pack(side="left")

        self.search_var = tk.StringVar()
        search_entry = tk.Entry(
            filter_row,
            textvariable=self.search_var,
            width=22,
            font=("Microsoft YaHei", 10),
            relief="solid",
            bd=1,
            bg="#ffffff",
            fg="#0f172a",
            insertbackground="#0f172a",
        )
        search_entry.pack(side="left", padx=(6, 10))
        search_entry.bind("<Return>", lambda event: self.refresh_tree())

        tk.Button(
            filter_row,
            text="筛选",
            command=self.refresh_tree,
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            relief="flat",
            font=("Microsoft YaHei", 10),
            padx=14,
            pady=5,
            cursor="hand2",
        ).pack(side="left")

        tk.Button(
            filter_row,
            text="重置",
            command=self.reset_filters,
            bg="#e2e8f0",
            fg="#334155",
            activebackground="#cbd5e1",
            relief="flat",
            font=("Microsoft YaHei", 10),
            padx=14,
            pady=5,
            cursor="hand2",
        ).pack(side="left", padx=(8, 0))

        self.manage_count_label = tk.Label(
            filter_row,
            text="",
            bg="#ffffff",
            fg="#64748b",
            font=("Microsoft YaHei", 10),
        )
        self.manage_count_label.pack(side="right")

        tree_frame = tk.Frame(wrap, bg="#ffffff")
        tree_frame.pack(fill="both", expand=True)

        columns = ("id", "subject", "book", "chapter", "question", "next_review", "interval")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            selectmode="extended",
        )
        headings = {
            "id": "编号",
            "subject": "科目",
            "book": "教材",
            "chapter": "章节",
            "question": "问题",
            "next_review": "下次复习",
            "interval": "间隔(天)",
        }
        widths = {
            "id": 52,
            "subject": 70,
            "book": 78,
            "chapter": 150,
            "question": 430,
            "next_review": 100,
            "interval": 72,
        }
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], anchor="w")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", lambda event: self.edit_selected())

        button_row = tk.Frame(wrap, bg="#ffffff")
        button_row.pack(fill="x", pady=(12, 0))

        button_defs = [
            ("新增卡片", self.add_card, "#2563eb", "#ffffff"),
            ("编辑选中", self.edit_selected, "#0f766e", "#ffffff"),
            ("删除选中", self.delete_selected, "#dc2626", "#ffffff"),
            ("重置学习进度", self.reset_selected_progress, "#7c3aed", "#ffffff"),
            ("保存数据", self.save_now, "#475569", "#ffffff"),
        ]
        for text, command, color, fg in button_defs:
            tk.Button(
                button_row,
                text=text,
                command=command,
                bg=color,
                fg=fg,
                activebackground=color,
                activeforeground=fg,
                relief="flat",
                font=("Microsoft YaHei", 10),
                padx=14,
                pady=7,
                cursor="hand2",
            ).pack(side="left", padx=(0, 8))

    def reset_filters(self):
        self.filter_subject.set("全部")
        self.filter_book.set("全部")
        self.search_var.set("")
        self.refresh_tree()

    def _filtered_cards(self):
        subject = self.filter_subject.get()
        book = self.filter_book.get()
        keyword = self.search_var.get().strip().lower()
        result = []
        for card in self.cards:
            if subject != "全部" and card.get("subject") != subject:
                continue
            if book != "全部" and card.get("book") != book:
                continue
            if keyword:
                haystack = " ".join(
                    str(card.get(field, ""))
                    for field in ("subject", "book", "chapter", "question", "answer")
                ).lower()
                if keyword not in haystack:
                    continue
            result.append(card)
        result.sort(key=lambda item: (item.get("subject", ""), item.get("book", ""), int(item.get("id", 0) or 0)))
        return result
    def refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        filtered = self._filtered_cards()
        for card in filtered:
            self.tree.insert(
                "",
                "end",
                iid=str(card.get("id", "")),
                values=(
                    card.get("id", ""),
                    card.get("subject", ""),
                    card.get("book", ""),
                    card.get("chapter", ""),
                    card.get("question", ""),
                    card.get("next_review", ""),
                    card.get("interval", 0),
                ),
            )
        self.manage_count_label.configure(text=f"当前显示 {len(filtered)} / 共 {len(self.cards)} 张")

    def _selected_ids(self):
        ids = []
        for item in self.tree.selection():
            try:
                ids.append(int(item))
            except ValueError:
                continue
        return ids

    def save_now(self):
        storage.save_cards(self.cards)
        messagebox.showinfo("保存成功", "卡片数据已保存到 data.json。")

    def delete_selected(self):
        ids = self._selected_ids()
        if not ids:
            messagebox.showwarning("未选择", "请先在列表中选择要删除的卡片。")
            return
        if not messagebox.askyesno("确认删除", f"确定删除选中的 {len(ids)} 张卡片吗？"):
            return
        self.cards = [card for card in self.cards if int(card.get("id", 0) or 0) not in ids]
        storage.save_cards(self.cards)
        self.refresh_all()

    def reset_selected_progress(self):
        ids = self._selected_ids()
        if not ids:
            messagebox.showwarning("未选择", "请先在列表中选择要重置的卡片。")
            return
        if not messagebox.askyesno("确认重置", f"确定重置选中的 {len(ids)} 张卡片的学习进度吗？"):
            return
        today = date.today().isoformat()
        for card in self.cards:
            if int(card.get("id", 0) or 0) in ids:
                card["interval"] = 0
                card["next_review"] = today
                card["last_review"] = ""
                card["correct_count"] = 0
                card["wrong_count"] = 0
        storage.save_cards(self.cards)
        self.refresh_all()
    def add_card(self):
        self._open_card_dialog(None)

    def edit_selected(self):
        ids = self._selected_ids()
        if not ids:
            messagebox.showwarning("未选择", "请先在列表中选择一张卡片。")
            return
        card = next((item for item in self.cards if int(item.get("id", 0) or 0) == ids[0]), None)
        if card is None:
            messagebox.showerror("错误", "没有找到选中的卡片。")
            return
        self._open_card_dialog(card)

    def _open_card_dialog(self, card):
        is_new = card is None
        dialog = tk.Toplevel(self)
        dialog.title("新增卡片" if is_new else "编辑卡片")
        dialog.geometry("620x620")
        dialog.configure(bg="#ffffff")
        dialog.transient(self)
        dialog.grab_set()

        fields = tk.Frame(dialog, bg="#ffffff")
        fields.pack(fill="both", expand=True, padx=20, pady=18)

        def add_label(text):
            tk.Label(
                fields,
                text=text,
                bg="#ffffff",
                fg="#334155",
                font=("Microsoft YaHei", 10, "bold"),
            ).pack(anchor="w", pady=(8, 3))

        add_label("科目")
        subject_var = tk.StringVar(value=(card or {}).get("subject", "语文"))
        subject_box = ttk.Combobox(fields, values=SUBJECTS, textvariable=subject_var, state="readonly")
        subject_box.pack(fill="x")

        add_label("教材")
        book_var = tk.StringVar(value=(card or {}).get("book", "必修一"))
        book_box = ttk.Combobox(fields, values=BOOKS, textvariable=book_var, state="readonly")
        book_box.pack(fill="x")

        add_label("章节 / 知识点")
        chapter_var = tk.StringVar(value=(card or {}).get("chapter", ""))
        chapter_entry = tk.Entry(
            fields,
            textvariable=chapter_var,
            font=("Microsoft YaHei", 11),
            relief="solid",
            bd=1,
            bg="#ffffff",
            fg="#0f172a",
            insertbackground="#0f172a",
        )
        chapter_entry.pack(fill="x", ipady=5)

        add_label("问题")
        question_text = tk.Text(
            fields,
            height=5,
            wrap="word",
            font=("Microsoft YaHei", 11),
            relief="solid",
            bd=1,
            bg="#ffffff",
            fg="#0f172a",
            insertbackground="#0f172a",
        )
        question_text.pack(fill="x")
        question_text.insert("1.0", (card or {}).get("question", ""))

        add_label("答案")
        answer_text = tk.Text(
            fields,
            height=7,
            wrap="word",
            font=("Microsoft YaHei", 11),
            relief="solid",
            bd=1,
            bg="#ffffff",
            fg="#0f172a",
            insertbackground="#0f172a",
        )
        answer_text.pack(fill="x")
        answer_text.insert("1.0", (card or {}).get("answer", ""))

        def save_card():
            subject = subject_var.get().strip() or "其他"
            book = book_var.get().strip() or "必修一"
            chapter = chapter_var.get().strip()
            question = question_text.get("1.0", "end").strip()
            answer = answer_text.get("1.0", "end").strip()

            if not question or not answer:
                messagebox.showwarning("内容不完整", "问题和答案都不能为空。", parent=dialog)
                return

            if is_new:
                self.cards.append({
                    "id": storage.next_card_id(self.cards),
                    "subject": subject,
                    "book": book,
                    "chapter": chapter,
                    "question": question,
                    "answer": answer,
                    "interval": 0,
                    "next_review": date.today().isoformat(),
                    "last_review": "",
                    "correct_count": 0,
                    "wrong_count": 0,
                })
            else:
                card["subject"] = subject
                card["book"] = book
                card["chapter"] = chapter
                card["question"] = question
                card["answer"] = answer

            storage.save_cards(self.cards)
            dialog.destroy()
            self.refresh_all()

        button_row = tk.Frame(dialog, bg="#ffffff")
        button_row.pack(fill="x", padx=20, pady=(0, 16))

        tk.Button(
            button_row,
            text="保存",
            command=save_card,
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            relief="flat",
            font=("Microsoft YaHei", 11, "bold"),
            padx=22,
            pady=8,
            cursor="hand2",
        ).pack(side="right")

        tk.Button(
            button_row,
            text="取消",
            command=dialog.destroy,
            bg="#e2e8f0",
            fg="#334155",
            activebackground="#cbd5e1",
            relief="flat",
            font=("Microsoft YaHei", 10),
            padx=18,
            pady=8,
            cursor="hand2",
        ).pack(side="right", padx=(0, 10))
    def _build_stats_tab(self):
        wrap = tk.Frame(self.stats_tab, bg="#ffffff")
        wrap.pack(fill="both", expand=True, padx=18, pady=14)

        tk.Label(
            wrap,
            text="学习数据总览",
            bg="#ffffff",
            fg="#0f172a",
            font=("Microsoft YaHei", 15, "bold"),
        ).pack(anchor="w")

        self.stats_summary = tk.Label(
            wrap,
            text="",
            bg="#ffffff",
            fg="#475569",
            font=("Microsoft YaHei", 11),
            anchor="w",
            justify="left",
        )
        self.stats_summary.pack(fill="x", pady=(8, 12))

        self.chart_canvas = tk.Canvas(
            wrap,
            bg="#f8fafc",
            highlightbackground="#cbd5e1",
            highlightthickness=1,
            height=430,
        )
        self.chart_canvas.pack(fill="both", expand=True)
        self.chart_canvas.bind("<Configure>", lambda event: self._draw_chart())

    def _build_basis_tab(self):
        wrap = tk.Frame(self.basis_tab, bg="#ffffff")
        wrap.pack(fill="both", expand=True, padx=18, pady=14)

        text = tk.Text(
            wrap,
            wrap="word",
            bg="#ffffff",
            fg="#334155",
            font=("Microsoft YaHei", 11),
            bd=0,
            padx=8,
            pady=8,
        )
        text.pack(fill="both", expand=True)

        content = """算法依据

一、艾宾浩斯遗忘曲线
德国心理学家艾宾浩斯在 1885 年通过实验发现：新学的内容遗忘速度先快后慢。复习应该安排在快要忘记但还没有完全忘记的时候，效果更好。

二、间隔效应与分散练习
教育心理学研究发现，把学习分散到多天，比一次性集中学习更有利于长期记忆。Cepeda 等人 2006 年的综述指出，合理增加复习间隔可以改善记忆保持。

三、提取练习与测试效应
Roediger 和 Karpicke 在 2006 年的研究中发现，主动回忆比单纯重复阅读更有利于长期记忆。本软件先显示问题，让用户自己回忆，再显示答案，就是在使用提取练习。

四、Leitner 系统
Leitner 在 20 世纪 70 年代提出用“盒子”管理复习：答对的卡片进入更长间隔，答错的卡片回到短间隔。这与“记住延长间隔、忘记回到 1 天”的思路一致。

五、SuperMemo SM-2 和 FSRS
SuperMemo 的 SM-2 算法是许多记忆软件的基础，它根据回忆质量调整后续间隔。FSRS 是近年来更现代的间隔重复算法，会考虑记忆稳定性、题目难度和目标保留率。
本软件为了适合高中阶段学习，使用了一个简化版本，便于理解和修改。

六、本软件的具体规则
- 新卡首次复习后，1 天再复习；
- 忘记：间隔回到 1 天；
- 模糊：间隔变为上一次的 1.6 倍；
- 记住：间隔变为上一次的 2.2 倍；
- 最长间隔 180 天；
- 间隔达到 30 天统计为已掌握；
- 默认每日新卡上限 20 张；
- 默认每日复习上限 100 张；
- 到期复习卡优先安排，新卡排在复习卡之后。

七、火花与续火花
- 每天完成至少一张卡片，就算“续火花”；
- 连续每天完成，火花天数会增加；
- 中断一天，下次完成后火花从 1 开始；
- 顶部的“火花”数字显示连续学习天数。

八、学习提醒
- 在“设置”页可以开启“启动时提醒我”和“每天定时提醒”；
- 可以设置每天的提醒时间；
- 可以导出手机日历提醒文件，导入手机日历后可以设置闹钟；
- 提醒内容会显示今天还有多少张卡片待完成。

九、每日学习量
在“设置”页可以调整每日新卡上限和每日复习上限。程序会优先安排已经到期的复习卡，再安排新卡。默认每日新卡 20 张，每日复习 100 张。

十、算法依据
可以在“算法依据”标签页查看艾宾浩斯遗忘曲线、间隔效应、提取练习、Leitner 系统和 SM-2 的简要说明。

十一、运行环境
- Windows 7 及以上系统；
- Python 3.8 及以上；
- 使用 Python 自带的 tkinter，不需要安装第三方库；
- 不需要联网。
"""
        text.insert("1.0", content)
        text.configure(state="disabled")

    def _build_settings_tab(self):
        outer = tk.Frame(self.settings_tab, bg="#ffffff")
        outer.pack(fill="both", expand=True)

        action_bar = tk.Frame(outer, bg="#ffffff")
        action_bar.pack(side="bottom", fill="x", padx=20, pady=(0, 14))

        tk.Button(
            action_bar,
            text="清理学习缓存",
            command=self.clear_cache,
            bg="#dc2626",
            fg="#ffffff",
            activebackground="#b91c1c",
            activeforeground="#ffffff",
            relief="flat",
            font=("Microsoft YaHei", 10),
            padx=16,
            pady=7,
            cursor="hand2",
        ).pack(side="left")

        tk.Button(
            action_bar,
            text="清除用户数据",
            command=self.clear_user_data,
            bg="#7c3aed",
            fg="#ffffff",
            activebackground="#6d28d9",
            activeforeground="#ffffff",
            relief="flat",
            font=("Microsoft YaHei", 10),
            padx=16,
            pady=7,
            cursor="hand2",
        ).pack(side="left", padx=(10, 0))

        tk.Button(
            action_bar,
            text="打开缓存文件夹",
            command=self.open_cache_folder,
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            relief="flat",
            font=("Microsoft YaHei", 10),
            padx=16,
            pady=7,
            cursor="hand2",
        ).pack(side="left", padx=(10, 0))

        settings_canvas = tk.Canvas(
            outer,
            bg="#ffffff",
            highlightthickness=0,
            bd=0,
        )
        settings_scrollbar = ttk.Scrollbar(
            outer,
            orient="vertical",
            command=settings_canvas.yview,
        )
        settings_canvas.configure(yscrollcommand=settings_scrollbar.set)

        settings_scrollbar.pack(side="right", fill="y")
        settings_canvas.pack(side="left", fill="both", expand=True)

        wrap = tk.Frame(settings_canvas, bg="#ffffff")
        settings_window = settings_canvas.create_window((0, 0), window=wrap, anchor="nw")

        def _update_settings_scrollregion(event=None):
            settings_canvas.configure(scrollregion=settings_canvas.bbox("all"))

        def _resize_settings_inner(event):
            settings_canvas.itemconfigure(settings_window, width=event.width)

        def _on_settings_mousewheel(event):
            settings_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        wrap.bind("<Configure>", _update_settings_scrollregion)
        settings_canvas.bind("<Configure>", _resize_settings_inner)
        settings_canvas.bind(
            "<Enter>",
            lambda event: settings_canvas.bind_all("<MouseWheel>", _on_settings_mousewheel),
        )
        settings_canvas.bind(
            "<Leave>",
            lambda event: settings_canvas.unbind_all("<MouseWheel>"),
        )

        content = tk.Frame(wrap, bg="#ffffff")
        content.pack(fill="both", expand=True, padx=20, pady=18)
        wrap = content

        tk.Label(
            wrap,
            text="设置",
            bg="#ffffff",
            fg="#0f172a",
            font=("Microsoft YaHei", 15, "bold"),
        ).pack(anchor="w")

        tk.Label(
            wrap,
            text="外观",
            bg="#ffffff",
            fg="#1d4ed8",
            font=("Microsoft YaHei", 11, "bold"),
        ).pack(anchor="w", pady=(18, 4))

        self.dark_mode_var = tk.BooleanVar(value=self.dark_mode)
        tk.Checkbutton(
            wrap,
            text="深色模式",
            variable=self.dark_mode_var,
            command=self.toggle_dark_mode,
            bg="#ffffff",
            fg="#0f172a",
            activebackground="#ffffff",
            activeforeground="#0f172a",
            selectcolor="#dbeafe",
            font=("Microsoft YaHei", 11, "bold"),
            cursor="hand2",
        ).pack(anchor="w")

        tk.Label(
            wrap,
            text="开启后界面使用暗色配色，夜间学习更护眼，也能减少屏幕光线刺激。",
            bg="#ffffff",
            fg="#64748b",
            font=("Microsoft YaHei", 10),
        ).pack(anchor="w", pady=(4, 0))

        tk.Frame(wrap, bg="#e2e8f0", height=1).pack(fill="x", pady=18)

        tk.Label(
            wrap,
            text="每日学习量",
            bg="#ffffff",
            fg="#1d4ed8",
            font=("Microsoft YaHei", 11, "bold"),
        ).pack(anchor="w", pady=(0, 6))

        limit_row = tk.Frame(wrap, bg="#ffffff")
        limit_row.pack(fill="x")

        tk.Label(
            limit_row,
            text="每日新卡上限：",
            bg="#ffffff",
            fg="#334155",
            font=("Microsoft YaHei", 10),
        ).pack(side="left")

        self.daily_new_var = tk.StringVar(value=str(self.daily_new_limit))
        new_box = ttk.Combobox(
            limit_row,
            values=["10", "20", "30", "50"],
            textvariable=self.daily_new_var,
            state="readonly",
            width=8,
        )
        new_box.pack(side="left", padx=(0, 18))
        new_box.bind("<<ComboboxSelected>>", lambda event: self.update_daily_limits())

        tk.Label(
            limit_row,
            text="每日复习上限：",
            bg="#ffffff",
            fg="#334155",
            font=("Microsoft YaHei", 10),
        ).pack(side="left")

        review_value = "不限" if self.daily_review_limit == 0 else str(self.daily_review_limit)
        self.daily_review_var = tk.StringVar(value=review_value)
        review_box = ttk.Combobox(
            limit_row,
            values=["30", "50", "100", "不限"],
            textvariable=self.daily_review_var,
            state="readonly",
            width=8,
        )
        review_box.pack(side="left")
        review_box.bind("<<ComboboxSelected>>", lambda event: self.update_daily_limits())

        self.daily_progress_label = tk.Label(
            wrap,
            text="",
            bg="#ffffff",
            fg="#64748b",
            font=("Microsoft YaHei", 10),
        )
        self.daily_progress_label.pack(anchor="w", pady=(8, 0))

        tk.Frame(wrap, bg="#e2e8f0", height=1).pack(fill="x", pady=18)

        tk.Label(
            wrap,
            text="学习提醒",
            bg="#ffffff",
            fg="#1d4ed8",
            font=("Microsoft YaHei", 11, "bold"),
        ).pack(anchor="w", pady=(0, 6))

        self.reminder_startup_var = tk.BooleanVar(
            value=bool(self.settings.get("reminder_startup", True))
        )
        tk.Checkbutton(
            wrap,
            text="启动时提醒我",
            variable=self.reminder_startup_var,
            command=self.update_reminder_settings,
            bg="#ffffff",
            fg="#0f172a",
            activebackground="#ffffff",
            activeforeground="#0f172a",
            selectcolor="#dbeafe",
            font=("Microsoft YaHei", 10),
            cursor="hand2",
        ).pack(anchor="w")

        self.reminder_daily_var = tk.BooleanVar(
            value=bool(self.settings.get("reminder_daily", True))
        )
        tk.Checkbutton(
            wrap,
            text="每天定时提醒",
            variable=self.reminder_daily_var,
            command=self.update_reminder_settings,
            bg="#ffffff",
            fg="#0f172a",
            activebackground="#ffffff",
            activeforeground="#0f172a",
            selectcolor="#dbeafe",
            font=("Microsoft YaHei", 10),
            cursor="hand2",
        ).pack(anchor="w", pady=(6, 0))

        time_row = tk.Frame(wrap, bg="#ffffff")
        time_row.pack(fill="x", pady=(8, 0))

        tk.Label(
            time_row,
            text="提醒时间：",
            bg="#ffffff",
            fg="#334155",
            font=("Microsoft YaHei", 10),
        ).pack(side="left")

        self.reminder_time_var = tk.StringVar(
            value=str(self.settings.get("reminder_time", "19:00"))
        )
        time_box = ttk.Combobox(
            time_row,
            values=["18:00", "19:00", "20:00", "21:00"],
            textvariable=self.reminder_time_var,
            state="readonly",
            width=8,
        )
        time_box.pack(side="left", padx=(0, 18))
        time_box.bind("<<ComboboxSelected>>", lambda event: self.update_reminder_settings())

        tk.Button(
            time_row,
            text="导出手机日历提醒",
            command=self.export_ics,
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            relief="flat",
            font=("Microsoft YaHei", 10),
            padx=14,
            pady=6,
            cursor="hand2",
        ).pack(side="left")

        notify_row = tk.Frame(wrap, bg="#ffffff")
        notify_row.pack(fill="x", pady=(8, 0))

        self.use_windows_toast_var = tk.BooleanVar(
            value=bool(self.settings.get("use_windows_toast", True))
        )
        tk.Checkbutton(
            notify_row,
            text="使用 Windows 系统通知",
            variable=self.use_windows_toast_var,
            command=self.update_reminder_settings,
            bg="#ffffff",
            fg="#0f172a",
            activebackground="#ffffff",
            activeforeground="#0f172a",
            selectcolor="#dbeafe",
            font=("Microsoft YaHei", 10),
            cursor="hand2",
        ).pack(side="left")

        tk.Button(
            notify_row,
            text="测试系统通知",
            command=self.test_windows_toast,
            bg="#0f766e",
            fg="#ffffff",
            activebackground="#115e59",
            activeforeground="#ffffff",
            relief="flat",
            font=("Microsoft YaHei", 10),
            padx=14,
            pady=6,
            cursor="hand2",
        ).pack(side="left", padx=(12, 0))

        compat_row = tk.Frame(wrap, bg="#ffffff")
        compat_row.pack(fill="x", pady=(8, 0))

        self.compat_mode_var = tk.BooleanVar(
            value=bool(self.settings.get("compat_mode", False))
        )
        tk.Checkbutton(
            compat_row,
            text="Win7 兼容模式（系统消息框 + 提示音）",
            variable=self.compat_mode_var,
            command=self.update_reminder_settings,
            bg="#ffffff",
            fg="#0f172a",
            activebackground="#ffffff",
            activeforeground="#0f172a",
            selectcolor="#dbeafe",
            font=("Microsoft YaHei", 10),
            cursor="hand2",
        ).pack(side="left")

        task_row = tk.Frame(wrap, bg="#ffffff")
        task_row.pack(fill="x", pady=(8, 0))

        tk.Label(
            task_row,
            text="程序关闭也能提醒：",
            bg="#ffffff",
            fg="#334155",
            font=("Microsoft YaHei", 10),
        ).pack(side="left")

        tk.Button(
            task_row,
            text="创建定时提醒",
            command=self.create_windows_task,
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            relief="flat",
            font=("Microsoft YaHei", 10),
            padx=14,
            pady=6,
            cursor="hand2",
        ).pack(side="left", padx=(8, 0))

        tk.Button(
            task_row,
            text="删除定时提醒",
            command=self.delete_windows_task,
            bg="#e2e8f0",
            fg="#334155",
            activebackground="#cbd5e1",
            relief="flat",
            font=("Microsoft YaHei", 10),
            padx=14,
            pady=6,
            cursor="hand2",
        ).pack(side="left", padx=(8, 0))

        self.task_status_label = tk.Label(
            task_row,
            text="检测中…",
            bg="#ffffff",
            fg="#64748b",
            font=("Microsoft YaHei", 10),
        )
        self.task_status_label.pack(side="left", padx=(10, 0))

        tk.Frame(wrap, bg="#e2e8f0", height=1).pack(fill="x", pady=18)

        tk.Label(
            wrap,
            text="数据与缓存",
            bg="#ffffff",
            fg="#1d4ed8",
            font=("Microsoft YaHei", 11, "bold"),
        ).pack(anchor="w", pady=(0, 6))

        tk.Label(
            wrap,
            text=f"原始题库：{storage.DEFAULT_DATA_FILE}",
            bg="#ffffff",
            fg="#334155",
            font=("Microsoft YaHei", 10),
            anchor="w",
        ).pack(fill="x", pady=2)

        tk.Label(
            wrap,
            text=f"用户缓存：{storage.USER_DATA_FILE}",
            bg="#ffffff",
            fg="#334155",
            font=("Microsoft YaHei", 10),
            anchor="w",
        ).pack(fill="x", pady=2)

        tk.Label(
            wrap,
            text="清理学习缓存：删除学习记录、今日进度和火花，保留设置。清除用户数据：删除全部用户数据，包括设置和导出的日历文件，程序恢复到第一次使用时的状态。",
            bg="#ffffff",
            fg="#64748b",
            font=("Microsoft YaHei", 10),
            wraplength=760,
            justify="left",
        ).pack(anchor="w", pady=(8, 12))

        tk.Label(
            wrap,
            text="提示：清理缓存后，学习记录会恢复为初始状态，适合重新开始复习计划。",
            bg="#ffffff",
            fg="#94a3b8",
            font=("Microsoft YaHei", 10),
            wraplength=760,
            justify="left",
        ).pack(anchor="w", pady=(16, 0))

        self.update_daily_progress_label()
        self.after(200, self.refresh_task_status)

    def _build_help_tab(self):
        wrap = tk.Frame(self.help_tab, bg="#ffffff")
        wrap.pack(fill="both", expand=True, padx=18, pady=14)

        text = tk.Text(
            wrap,
            wrap="word",
            bg="#ffffff",
            fg="#334155",
            font=("Microsoft YaHei", 11),
            bd=0,
            padx=6,
            pady=6,
        )
        text.pack(fill="both", expand=True)

        content = """记忆曲线 · 高中必修一/二知识点复习助手

一、这个程序是做什么的？
它把高中必修一、二的知识点做成一张张“问题—答案”卡片，并根据你的记忆情况自动安排下一次复习时间。

二、怎么使用？
1. 在“今日复习”里看问题，先自己想答案；
2. 点击“显示答案”；
3. 根据实际情况选择“忘记”“模糊”或“记住”；
4. 程序会自动计算下次复习时间。

三、火花与续火花
每天完成至少一张卡片，就算“续火花”。连续每天完成，火花天数会增加；中断一天，下次完成后从 1 开始。

四、学习提醒
在“设置”页可以开启启动提醒和每天定时提醒，也可以导出手机日历提醒文件。勾选“使用 Windows 系统通知”后，Windows 10/11 会通过通知中心弹出提醒；Windows 7 或通知失败时会自动使用系统消息框和提示音。勾选“Win7 兼容模式”可以强制使用兼容提醒。点击“测试系统通知”可以先检查电脑能否正常弹出通知。点击“创建定时提醒”后，即使程序关闭，Windows 任务计划程序也会在设定时间运行提醒脚本；点击“删除定时提醒”可以取消。

五、每日学习量
在“设置”页可以调整每日新卡上限和每日复习上限。程序会优先安排已经到期的复习卡，再安排新卡。

六、数据与缓存
- data.json：原始题库；
- cache/user_data.json：你的学习记录；
- cache/daily_stats.json：今日完成量；
- cache/spark.json：火花数据；
- 清理缓存不会删除设置和提醒时间；
- 清除用户数据会删除学习记录、火花、设置和提醒文件，恢复到第一次使用时的状态。

七、算法依据
可以在“算法依据”标签页查看艾宾浩斯遗忘曲线、间隔效应、提取练习、Leitner 系统和 SM-2 的简要说明。

八、运行环境
- Windows 7 及以上系统；
- Python 3.8 及以上；
- 使用 Python 自带的 tkinter，不需要安装第三方库；
- 不需要联网。
"""
        text.insert("1.0", content)
        text.configure(state="disabled")

    def toggle_dark_mode(self):
        self.dark_mode = bool(self.dark_mode_var.get())
        self.settings["dark_mode"] = self.dark_mode
        storage.save_settings(self.settings)
        self.apply_theme()

    def clear_cache(self):
        if not messagebox.askyesno("清理学习缓存", "确定删除 cache/user_data.json，并恢复初始题库吗？"):
            return
        storage.clear_user_cache()
        self.cards = storage.load_cards()
        self.refresh_all()
        messagebox.showinfo("清理完成", "学习缓存已清理，已恢复为初始题库。深色模式设置保留。")

    def clear_user_data(self):
        if not messagebox.askyesno(
            "清除用户数据",
            "确定清除所有用户数据吗？学习记录、火花、今日进度、提醒设置和导出的日历文件都会被删除。",
        ):
            return
        storage.clear_all_user_data()
        try:
            task_scheduler.delete_task()
        except Exception:
            pass
        self.settings = storage.load_settings()
        self.dark_mode = bool(self.settings.get("dark_mode", False))
        self.daily_new_limit = int(self.settings.get("daily_new_limit", 20) or 20)
        self.daily_review_limit = int(self.settings.get("daily_review_limit", 100) or 0)
        self.daily_stats = storage.load_daily_stats()
        self.spark = storage.load_spark()
        self.cards = storage.load_cards()

        storage.save_settings(self.settings)
        storage.save_daily_stats(self.daily_stats)
        storage.save_spark(self.spark)

        self.dark_mode_var.set(self.dark_mode)
        self.daily_new_var.set(str(self.daily_new_limit))
        self.daily_review_var.set("不限" if self.daily_review_limit == 0 else str(self.daily_review_limit))
        self.reminder_startup_var.set(bool(self.settings.get("reminder_startup", True)))
        self.reminder_daily_var.set(bool(self.settings.get("reminder_daily", True)))
        self.reminder_time_var.set(str(self.settings.get("reminder_time", "19:00")))
        if hasattr(self, "use_windows_toast_var"):
            self.use_windows_toast_var.set(bool(self.settings.get("use_windows_toast", True)))
        if hasattr(self, "compat_mode_var"):
            self.compat_mode_var.set(bool(self.settings.get("compat_mode", False)))

        self.apply_theme()
        self.refresh_all()
        messagebox.showinfo("清除完成", "所有用户数据已清除，程序已恢复为第一次使用时的状态。")

    def open_cache_folder(self):
        storage.ensure_cache_dir()
        path = str(storage.CACHE_DIR)
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as exc:
            messagebox.showerror("无法打开", f"无法打开缓存文件夹：{exc}")

    def _theme_palette(self):
        if self.dark_mode:
            return {
                "window": "#0b1120",
                "panel": "#111827",
                "panel_alt": "#0f172a",
                "input_bg": "#0f172a",
                "text": "#f8fafc",
                "text_mid": "#cbd5e1",
                "text_muted": "#94a3b8",
                "tree_bg": "#0f172a",
                "tree_fg": "#e5e7eb",
                "heading_bg": "#1f2937",
                "heading_fg": "#e5e7eb",
                "accent": "#60a5fa",
                "success_bg": "#052e16",
                "success_fg": "#bbf7d0",
            }
        return {
            "window": "#eef2f7",
            "panel": "#ffffff",
            "panel_alt": "#f8fafc",
            "input_bg": "#ffffff",
            "text": "#0f172a",
            "text_mid": "#334155",
            "text_muted": "#64748b",
            "tree_bg": "#ffffff",
            "tree_fg": "#0f172a",
            "heading_bg": "#dbe4f0",
            "heading_fg": "#1e293b",
            "accent": "#1d4ed8",
            "success_bg": "#ecfdf5",
            "success_fg": "#14532d",
        }

    def apply_theme(self):
        palette = self._theme_palette()
        self.configure(bg=palette["window"])
        style = self.style

        style.configure("TNotebook", background=palette["window"], borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            padding=(18, 10),
            font=("Microsoft YaHei", 11),
            background=palette["heading_bg"],
            foreground=palette["heading_fg"],
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", palette["panel"])],
            foreground=[("selected", palette["accent"])],
        )
        style.configure(
            "Treeview",
            rowheight=30,
            font=("Microsoft YaHei", 10),
            background=palette["tree_bg"],
            fieldbackground=palette["tree_bg"],
            foreground=palette["tree_fg"],
        )
        style.configure(
            "Treeview.Heading",
            font=("Microsoft YaHei", 10, "bold"),
            background=palette["heading_bg"],
            foreground=palette["heading_fg"],
        )
        style.configure(
            "TCombobox",
            padding=4,
            fieldbackground=palette["input_bg"],
            background=palette["input_bg"],
            foreground=palette["text"],
            arrowcolor=palette["text"],
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", palette["input_bg"])],
            foreground=[("readonly", palette["text"])],
        )
        style.configure("TButton", padding=6, font=("Microsoft YaHei", 10))
        self._recolor_widgets(self)

        if hasattr(self, "chart_canvas"):
            self.chart_canvas.configure(bg=palette["panel_alt"])
            self._draw_chart()

    def _recolor_widgets(self, parent):
        bg_pairs = [
            ("#eef2f7", "#0b1120"),
            ("#ffffff", "#111827"),
            ("#f8fafc", "#0f172a"),
            ("#e2e8f0", "#1f2937"),
            ("#ecfdf5", "#052e16"),
            ("#dbe4f0", "#1f2937"),
            ("#cbd5e1", "#334155"),
        ]
        fg_pairs = [
            ("#0f172a", "#f8fafc"),
            ("#334155", "#cbd5e1"),
            ("#475569", "#cbd5e1"),
            ("#64748b", "#94a3b8"),
            ("#14532d", "#bbf7d0"),
            ("#15803d", "#86efac"),
            ("#1d4ed8", "#93c5fd"),
            ("#2563eb", "#60a5fa"),
            ("#1e293b", "#e5e7eb"),
        ]

        if self.dark_mode:
            bg_map = {light: dark for light, dark in bg_pairs}
            fg_map = {light: dark for light, dark in fg_pairs}
        else:
            bg_map = {dark: light for light, dark in bg_pairs}
            fg_map = {dark: light for light, dark in fg_pairs}

        def recolor(widget):
            for child in widget.winfo_children():
                for option, mapping in (
                    ("bg", bg_map),
                    ("fg", fg_map),
                    ("highlightbackground", bg_map),
                    ("activebackground", bg_map),
                    ("selectcolor", bg_map),
                    ("insertbackground", fg_map),
                ):
                    try:
                        value = child.cget(option)
                    except tk.TclError:
                        continue
                    if value in mapping:
                        try:
                            child.configure(**{option: mapping[value]})
                        except tk.TclError:
                            pass
                recolor(child)

        recolor(parent)

    def update_daily_limits(self):
        self.daily_new_limit = int(self.daily_new_var.get())
        review_text = self.daily_review_var.get()
        self.daily_review_limit = 0 if review_text == "不限" else int(review_text)
        self.settings["daily_new_limit"] = self.daily_new_limit
        self.settings["daily_review_limit"] = self.daily_review_limit
        storage.save_settings(self.settings)
        self.refresh_due()
        self.refresh_stats()

    def update_daily_progress_label(self):
        if not hasattr(self, "daily_progress_label"):
            return
        new_count = int(self.daily_stats.get("new_count", 0) or 0)
        review_count = int(self.daily_stats.get("review_count", 0) or 0)
        self.daily_progress_label.configure(
            text=f"今日已续火花：新卡 {new_count} 张，复习 {review_count} 张。"
        )

    def update_reminder_settings(self):
        self.settings["reminder_startup"] = bool(self.reminder_startup_var.get())
        self.settings["reminder_daily"] = bool(self.reminder_daily_var.get())
        self.settings["reminder_time"] = self.reminder_time_var.get()
        if hasattr(self, "use_windows_toast_var"):
            self.settings["use_windows_toast"] = bool(self.use_windows_toast_var.get())
        if hasattr(self, "compat_mode_var"):
            self.settings["compat_mode"] = bool(self.compat_mode_var.get())
        storage.save_settings(self.settings)
        try:
            if task_scheduler.task_exists():
                task_scheduler.create_daily_task(self.reminder_time_var.get())
        except Exception:
            pass

    def _show_reminder_popup(self):
        due = len(self.current_due) if hasattr(self, "current_due") else 0
        if due <= 0:
            return
        done = int(self.daily_stats.get("new_count", 0) or 0) + int(self.daily_stats.get("review_count", 0) or 0)
        message = f"今天还有 {due} 张卡片待完成，完成后可以续火花。"
        if done > 0:
            message = message + chr(10) + f"今日已经完成 {done} 张。"

        use_toast = bool(self.settings.get("use_windows_toast", True))
        if hasattr(self, "use_windows_toast_var"):
            use_toast = bool(self.use_windows_toast_var.get())
        force_compat = bool(self.settings.get("compat_mode", False))
        if hasattr(self, "compat_mode_var"):
            force_compat = bool(self.compat_mode_var.get())
        if use_toast and notifier.show_windows_toast(
            "记忆曲线 · 学习提醒",
            message.replace(chr(10), " "),
            force_compat=force_compat,
        ):
            return
        messagebox.showinfo("学习提醒", message)

    def test_windows_toast(self):
        message = "这是一条测试通知。如果能看到它，说明系统提醒已经可以正常使用。"
        force_compat = bool(self.settings.get("compat_mode", False))
        if hasattr(self, "compat_mode_var"):
            force_compat = bool(self.compat_mode_var.get())
        if notifier.show_windows_toast("记忆曲线复习助手", message, force_compat=force_compat):
            messagebox.showinfo("测试成功", "已发送测试提醒，请查看 Windows 通知或系统消息框。")
        else:
            messagebox.showwarning("测试失败", "未能拉起系统提醒，将使用程序内弹窗。")
            messagebox.showinfo("学习提醒", message)

    def refresh_task_status(self):
        try:
            text = task_scheduler.task_status_text()
        except Exception:
            text = "检测失败"
        if hasattr(self, "task_status_label"):
            self.task_status_label.configure(text=text)

    def create_windows_task(self):
        ok, message = task_scheduler.create_daily_task(self.reminder_time_var.get())
        if ok:
            messagebox.showinfo("创建成功", message)
        else:
            messagebox.showerror("创建失败", message)
        self.refresh_task_status()

    def delete_windows_task(self):
        ok, message = task_scheduler.delete_task()
        if ok:
            messagebox.showinfo("删除成功", message)
        else:
            messagebox.showerror("删除失败", message)
        self.refresh_task_status()

    def show_startup_reminder(self):
        try:
            if not self.reminder_startup_var.get():
                return
            self._show_reminder_popup()
        except tk.TclError:
            pass

    def _check_reminder_loop(self):
        try:
            if self.reminder_daily_var.get():
                now_text = datetime.now().strftime("%H:%M")
                today_text = date.today().isoformat()
                if (
                    now_text == self.reminder_time_var.get()
                    and self.daily_stats.get("reminder_shown_date") != today_text
                ):
                    self.daily_stats["reminder_shown_date"] = today_text
                    storage.save_daily_stats(self.daily_stats)
                    self._show_reminder_popup()
        except tk.TclError:
            return
        self.after(30000, self._check_reminder_loop)

    def export_ics(self):
        time_text = self.reminder_time_var.get() or "19:00"
        try:
            hour_text, minute_text = time_text.split(":")
            hour = int(hour_text)
            minute = int(minute_text)
        except (ValueError, AttributeError):
            hour, minute = 19, 0

        today = date.today()
        due = len(self.current_due) if hasattr(self, "current_due") else 0
        dtstart = f"{today.strftime('%Y%m%d')}T{hour:02d}{minute:02d}00"
        dtstamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        uid = f"memory-curve-{today.strftime('%Y%m%d')}-{hour:02d}{minute:02d}@local"
        description = f"打开记忆曲线，完成今日复习任务，续火花。今天还有 {due} 张卡片待完成。"

        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//MemoryCurve//Study Reminder//CN",
            "CALSCALE:GREGORIAN",
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART:{dtstart}",
            "RRULE:FREQ=DAILY",
            "SUMMARY:续火花：完成今日复习",
            f"DESCRIPTION:{description}",
            "BEGIN:VALARM",
            "TRIGGER:-PT0M",
            "ACTION:DISPLAY",
            "DESCRIPTION:学习提醒",
            "END:VALARM",
            "END:VEVENT",
            "END:VCALENDAR",
        ]
        storage.ensure_cache_dir()
        path = storage.CACHE_DIR / "记忆曲线提醒.ics"
        path.write_text((chr(13) + chr(10)).join(lines), encoding="utf-8")
        messagebox.showinfo("导出成功", "手机日历提醒文件已生成：" + chr(10) + str(path))

    def _refresh_spark(self):
        self.spark = storage.load_spark()
        if hasattr(self, "var_spark"):
            self.var_spark.set(f"{int(self.spark.get('streak', 0) or 0)} 天")

    def _update_spark_on_study(self):
        today = date.today()
        yesterday = (today - timedelta(days=1)).isoformat()
        spark = storage.load_spark()
        last_date = spark.get("last_study_date", "")
        if last_date == today.isoformat():
            pass
        elif last_date == yesterday:
            spark["streak"] = int(spark.get("streak", 0) or 0) + 1
        else:
            spark["streak"] = 1
        spark["last_study_date"] = today.isoformat()
        storage.save_spark(spark)
        self.spark = spark

    def update_progress_bar(self):
        done_new = int(self.daily_stats.get("new_count", 0) or 0)
        done_review = int(self.daily_stats.get("review_count", 0) or 0)
        done = done_new + done_review
        remaining = len(self.current_due) if hasattr(self, "current_due") else 0
        total = done + remaining

        if total <= 0:
            percent = 0
            text = "今日任务已完成，明天继续续火花。"
        else:
            percent = int(done / total * 100)
            text = f"今日进度：{done} / {total} 张，完成即可续火花。"

        if hasattr(self, "progress_bar"):
            self.progress_bar.configure(value=percent)
        if hasattr(self, "progress_text"):
            self.progress_text.configure(text=text)

    def update_stats_bar(self):
        total = len(self.cards)
        due = len(self.current_due) if hasattr(self, "current_due") else len(scheduler.get_due_cards(self.cards))
        mastered = sum(1 for card in self.cards if scheduler.is_mastered(card))
        correct = sum(int(card.get("correct_count", 0) or 0) for card in self.cards)
        wrong = sum(int(card.get("wrong_count", 0) or 0) for card in self.cards)
        accuracy = 0 if correct + wrong == 0 else round(correct / (correct + wrong) * 100, 1)
        streak = int(self.spark.get("streak", 0) or 0) if hasattr(self, "spark") else 0

        self.var_total.set(str(total))
        self.var_due.set(str(due))
        self.var_mastered.set(str(mastered))
        self.var_accuracy.set(f"{accuracy}%")
        self.var_spark.set(f"{streak} 天")

    def refresh_stats(self):
        total = len(self.cards)
        due_total = len(scheduler.get_due_cards(self.cards))
        queue_count = len(self.current_due) if hasattr(self, "current_due") else 0
        mastered = sum(1 for card in self.cards if scheduler.is_mastered(card))
        new_done = int(self.daily_stats.get("new_count", 0) or 0)
        review_done = int(self.daily_stats.get("review_count", 0) or 0)
        streak = int(self.spark.get("streak", 0) or 0) if hasattr(self, "spark") else 0
        self.stats_summary.configure(
            text=f"共 {total} 张卡片；已到期 {due_total} 张，今日计划 {queue_count} 张；"
                 f"已掌握 {mastered} 张；今日已学新卡 {new_done} 张，已复习 {review_done} 张；火花 {streak} 天。"
        )
        self._draw_chart()

    def _draw_chart(self):
        canvas = self.chart_canvas
        canvas.delete("all")
        width = max(int(canvas.winfo_width()), 760)
        height = max(int(canvas.winfo_height()), 420)
        palette = self._theme_palette()

        title_color = palette["text"]
        label_color = palette["text_mid"]
        muted_color = palette["text_muted"]
        box_fill = "#1e3a8a" if self.dark_mode else "#e0f2fe"
        box_outline = "#3b82f6" if self.dark_mode else "#bae6fd"
        box_text_main = "#dbeafe" if self.dark_mode else "#0c4a6e"
        box_text_sub = "#bfdbfe" if self.dark_mode else "#0369a1"

        colors = {
            "语文": "#ef4444", "数学": "#3b82f6", "英语": "#8b5cf6",
            "物理": "#06b6d4", "化学": "#f59e0b", "生物": "#22c55e",
            "政治": "#e11d48", "历史": "#a16207", "地理": "#0d9488",
            "其他": "#64748b",
        }
        counts = {subject: 0 for subject in SUBJECTS}
        for card in self.cards:
            subject = card.get("subject", "其他")
            counts[subject] = counts.get(subject, 0) + 1

        canvas.create_text(20, 18, text="各科卡片数量", anchor="w", fill=title_color, font=("Microsoft YaHei", 12, "bold"))
        max_count = max(counts.values()) if counts else 1
        max_count = max(max_count, 1)
        chart_top = 52
        chart_bottom = 250
        bar_width = 44
        gap = 24
        start_x = 42
        for index, subject in enumerate(SUBJECTS):
            count = counts.get(subject, 0)
            bar_height = int((chart_bottom - chart_top) * count / max_count)
            x1 = start_x + index * (bar_width + gap)
            x2 = x1 + bar_width
            y1 = chart_bottom - bar_height
            canvas.create_rectangle(x1, y1, x2, chart_bottom, fill=colors.get(subject, "#64748b"), outline="")
            canvas.create_text((x1 + x2) / 2, y1 - 12, text=str(count), fill=label_color, font=("Microsoft YaHei", 9))
            canvas.create_text((x1 + x2) / 2, chart_bottom + 16, text=subject, fill=muted_color, font=("Microsoft YaHei", 9))

        canvas.create_text(20, 310, text="未来 7 天复习计划（张）", anchor="w", fill=title_color, font=("Microsoft YaHei", 12, "bold"))
        today = date.today()
        box_width = max(70, int((width - 60) / 7) - 8)
        for offset in range(7):
            current_day = today.fromordinal(today.toordinal() + offset)
            count = sum(1 for card in self.cards if card.get("next_review") == current_day.isoformat())
            x1 = 24 + offset * (box_width + 8)
            x2 = x1 + box_width
            canvas.create_rectangle(x1, 340, x2, 405, fill=box_fill, outline=box_outline)
            canvas.create_text((x1 + x2) / 2, 360, text=f"{(offset + 1)}天", fill=box_text_sub, font=("Microsoft YaHei", 9))
            canvas.create_text((x1 + x2) / 2, 385, text=f"{count} 张", fill=box_text_main, font=("Microsoft YaHei", 11, "bold"))

    def refresh_all(self):
        self.refresh_due()
        self.refresh_tree()
        self.refresh_stats()

    def on_close(self):
        storage.save_cards(self.cards)
        self.destroy()


if __name__ == "__main__":
    app = ReviewApp()
    app.mainloop()
