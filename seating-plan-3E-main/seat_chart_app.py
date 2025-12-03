"""Tkinter application for shuffling seats and saving charts."""

from __future__ import annotations

import os
import re
import csv
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from typing import Dict, List, Tuple
import copy
import unicodedata

from reportlab.lib import colors

from seat_chart_generator import (
    create_seat_chart,
    simple_shuffle,
    Student,
)
from seat_chart_generator.layout import load_layout, generate_layout
from students import STUDENTS, COMMITTEES


class SeatApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        try:
            self.layout = load_layout()
        except Exception:
            self.layout = generate_layout(10, 5)
        self.students_sorted = sorted(STUDENTS, key=lambda d: d["serial"])
        self.student_data = {d["name_kanji"]: d for d in self.students_sorted}
        self.labels: Dict[int, tk.Label] = {}
        self.fixed_seats: set[int] = set()
        self.empty_seats: Dict[int, Tuple[str, str]] = {}
        try:
            shuffled = simple_shuffle(STUDENTS, self.layout)
        except ValueError:
            shuffled = []
        self.assignments: Dict[int, Student] = {s.seat_number: s for s in shuffled}
        self.seat_numbers = sorted(
            seat for row in self.layout for seat in row if isinstance(seat, int)
        )
        self.total_seats = sum(
            1 for row in self.layout for seat in row if isinstance(seat, int)
        )
        self.required_students = sum(1 for s in STUDENTS if s.get("status") == "在籍")
        self.count_var = tk.StringVar()
        self.search_var = tk.StringVar()
        self.roster_filter_var = tk.StringVar(value="すべて")
        # Default background colour for labels (platform dependent)
        tmp_lbl = tk.Label(self.root)
        self.default_bg = tmp_lbl.cget("bg")
        tmp_lbl.destroy()
        self.title_var = tk.StringVar(value="席替え座席表")
        self.drag_data: dict[str, object] = {}
        self.drag_ghost: tk.Toplevel | None = None
        self.highlight_widget: tk.Widget | None = None
        self.history: list[dict[str, object]] = []
        self.redo_stack: list[dict[str, object]] = []
        self._restoring_state = False
        self._shortcuts_bound = False
        self._fullscreen = False
        self._build_ui()

    def _normalize_text(self, text: str) -> str:
        """Normalize text for flexible matching (kana, width, casing)."""

        def to_hiragana(char: str) -> str:
            code = ord(char)
            if 0x30A1 <= code <= 0x30F4:  # Katakana to Hiragana
                return chr(code - 0x60)
            return char

        normalized = unicodedata.normalize("NFKC", text).casefold()
        normalized = normalized.replace(" ", "").replace("\u3000", "")
        return "".join(to_hiragana(ch) for ch in normalized)

    def _matches_query(self, query: str, *candidates: str) -> bool:
        if not query:
            return True
        norm_q = self._normalize_text(query)
        for candidate in candidates:
            if candidate is None:
                continue
            if norm_q in self._normalize_text(str(candidate)):
                return True
        return False

    def _format_student(self, student: Student) -> str:
        """Return multiline string with student details."""
        return (
            f"{student.serial}\n"
            f"{student.student_id}\n"
            f"{student.name_kanji}\n"
            f"{student.name_kana}"
        )

    def _refresh_roster(self) -> None:
        query = self.search_var.get().strip()
        status_filter = self.roster_filter_var.get()
        self.roster_listbox.delete(0, tk.END)
        for special in ("教卓", "補助机"):
            if not self._matches_query(query, special):
                continue
            self.roster_listbox.insert(tk.END, special)
        for data in self.students_sorted:
            if status_filter == "在籍" and data.get("status") != "在籍":
                continue
            if status_filter == "休学" and data.get("status") != "休学":
                continue
            if status_filter == "女の子" and data.get("gender") != "F":
                continue
            if status_filter == "男の子" and data.get("gender") != "M":
                continue
            if not self._matches_query(query, data["name_kanji"], data.get("name_kana")):
                continue
            self.roster_listbox.insert(tk.END, data["name_kanji"])

    def _take_snapshot(self) -> dict[str, object]:
        return {
            "layout": copy.deepcopy(self.layout),
            "assignments": copy.deepcopy(self.assignments),
            "fixed_seats": set(self.fixed_seats),
            "empty_seats": copy.deepcopy(self.empty_seats),
            "title": self.title_var.get(),
        }

    def _record_state(self) -> None:
        if self._restoring_state:
            return
        self.history.append(self._take_snapshot())
        self.redo_stack.clear()

    def _restore_snapshot(self, snapshot: dict[str, object]) -> None:
        self._restoring_state = True
        self.layout = copy.deepcopy(snapshot["layout"])
        self.assignments = copy.deepcopy(snapshot["assignments"])
        self.fixed_seats = set(snapshot["fixed_seats"])
        self.empty_seats = copy.deepcopy(snapshot["empty_seats"])
        self.title_var.set(str(snapshot.get("title", "")))
        self.total_seats = sum(
            1 for row in self.layout for seat in row if isinstance(seat, int)
        )
        self.seat_numbers = sorted(
            seat for row in self.layout for seat in row if isinstance(seat, int)
        )
        self.labels.clear()
        for widget in self.root.winfo_children():
            widget.destroy()
        self._build_ui()
        self._restoring_state = False

    def _build_ui(self) -> None:
        cols = max(len(r) for r in self.layout)
        main = tk.Frame(self.root)
        main.grid(row=0, column=0, sticky="nsew")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        seat_frame = tk.Frame(main)
        seat_frame.grid(row=0, column=0, padx=(5, 10), pady=5, sticky="nw")
        roster_frame = tk.Frame(main, bd=2, relief="groove")
        roster_frame.grid(row=0, column=1, padx=5, pady=5, sticky="ns")

        for r, row in enumerate(self.layout):
            seat_frame.grid_rowconfigure(r, weight=1, minsize=62)
            for c, seat in enumerate(row):
                seat_frame.grid_columnconfigure(c, weight=1, minsize=90)
                if seat is None or not isinstance(seat, int):
                    continue
                student = self.assignments.get(seat)
                empty_text, empty_colour = self.empty_seats.get(seat, ("", "black"))
                if student:
                    text = self._format_student(student)
                    colour = "red" if student.color == colors.red else "black"
                    justify = "center"
                    anchor = "center"
                elif seat in self.empty_seats:
                    text = empty_text
                    colour = empty_colour
                    justify = (
                        "left" if text and text not in ("教卓", "補助机") else "center"
                    )
                    anchor = "w" if text and text not in ("教卓", "補助机") else "center"
                else:
                    text = ""
                    colour = "black"
                    justify = "center"
                    anchor = "center"
                lbl = tk.Label(
                    seat_frame,
                    text=text,
                    width=11,
                    height=3,
                    fg=colour,
                    justify=justify,
                    anchor=anchor,
                    wraplength=90,
                    padx=3,
                    pady=3,
                )
                lbl.grid(row=r, column=c, padx=3, pady=3, sticky="nsew")
                lbl.bind("<ButtonPress-1>", lambda e, s=seat: self._seat_mouse_down(e, s))
                lbl.bind("<B1-Motion>", self._on_drag_motion)
                lbl.bind("<ButtonRelease-1>", lambda e, s=seat: self._seat_mouse_up(e, s))
                self.labels[seat] = lbl
                self._style_label(seat)

        controls = tk.Frame(main)
        controls.grid(row=1, column=0, columnspan=2, sticky="we", padx=5, pady=5)
        controls.columnconfigure(1, weight=1)
        tk.Label(controls, text="タイトル").grid(row=0, column=0, sticky="w")
        tk.Entry(controls, textvariable=self.title_var, width=20).grid(
            row=0, column=1, columnspan=max(1, cols - 1), sticky="we"
        )
        tk.Button(controls, text="Shuffle", command=self.shuffle).grid(
            row=1, column=0, pady=5
        )
        tk.Button(controls, text="Save", command=self.save).grid(row=1, column=1, pady=5, sticky="w")
        tk.Button(controls, text="CSV保存", command=self.save_csv).grid(
            row=1, column=2, pady=5, padx=2
        )
        tk.Button(controls, text="CSV読込", command=self.load_csv).grid(
            row=1, column=3, pady=5, padx=2
        )
        tk.Button(controls, text="すべて削除", command=self.clear_all).grid(
            row=1, column=4, pady=5, padx=2
        )
        tk.Button(controls, text="縦変更", command=self.change_rows).grid(row=1, column=5, pady=5)
        tk.Button(controls, text="横変更", command=self.change_cols).grid(row=1, column=6, pady=5)
        tk.Button(controls, text="元に戻す (Undo)", command=self.undo).grid(
            row=1, column=7, pady=5, padx=2
        )
        tk.Button(controls, text="やり直し (Redo)", command=self.redo).grid(
            row=1, column=8, pady=5, padx=2
        )
        self.count_label = tk.Label(controls, textvariable=self.count_var)
        self.count_label.grid(
            row=1,
            column=9,
            columnspan=max(1, cols - 9),
            pady=5,
            sticky="w",
        )

        tk.Label(roster_frame, text="学生リスト", font=("", 10, "bold")).pack(
            anchor="w", padx=6, pady=(6, 2)
        )
        search_area = tk.Frame(roster_frame)
        search_area.pack(fill="x", padx=6)
        search_entry = tk.Entry(search_area, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, expand=True, fill="x")
        search_entry.bind("<Return>", lambda *_: self._refresh_roster())
        search_entry.bind("<KeyRelease>", lambda *_: self._refresh_roster())
        tk.Button(search_area, text="検索", command=self._refresh_roster).pack(side=tk.LEFT, padx=(4, 0))
        filter_frame = tk.Frame(roster_frame)
        filter_frame.pack(fill="x", padx=6, pady=(4, 0))
        tk.Label(filter_frame, text="ステータス").pack(side=tk.LEFT)
        tk.OptionMenu(
            filter_frame,
            self.roster_filter_var,
            "すべて",
            "在籍",
            "休学",
            "女の子",
            "男の子",
            command=lambda *_: self._refresh_roster(),
        ).pack(side=tk.LEFT, padx=4)
        self.roster_listbox = tk.Listbox(roster_frame, height=20, width=18)
        self.roster_listbox.pack(side=tk.LEFT, fill="both", expand=True, padx=(6, 0), pady=6)
        roster_scroll = tk.Scrollbar(roster_frame, command=self.roster_listbox.yview)
        roster_scroll.pack(side=tk.LEFT, fill="y", pady=6, padx=(0, 6))
        self.roster_listbox.config(yscrollcommand=roster_scroll.set)
        self.roster_listbox.bind("<ButtonPress-1>", self._start_drag_from_roster)
        self.roster_listbox.bind("<B1-Motion>", self._on_drag_motion)
        self.roster_listbox.bind("<ButtonRelease-1>", self._end_drag)
        tk.Label(roster_frame, text="ドラッグで席に割り当て/置換", fg="gray").pack(
            anchor="w", padx=6, pady=(0, 6)
        )

        self._refresh_roster()
        self._update_counts()
        self._bind_shortcuts()

    def _seat_mouse_down(self, event: tk.Event, seat: int) -> None:
        self.drag_data = {"source": None, "item": None, "start": (event.x_root, event.y_root)}
        self.drag_ghost = None
        self.highlight_widget = None
        self._clear_highlight()
        if seat in self.assignments:
            self.drag_data["source"] = "seat"
            self.drag_data["seat"] = seat
            self.drag_data["item"] = self.assignments[seat].name_kanji
        elif seat in self.empty_seats:
            # Allow dragging out to clear custom text/空席
            self.drag_data["source"] = "seat-empty"
            self.drag_data["seat"] = seat
            self.drag_data["item"] = None
        else:
            # still allow click to open dialog
            self.drag_data["seat"] = seat

    def _seat_mouse_up(self, event: tk.Event, seat: int) -> None:
        if self.drag_data.get("dragging"):
            self._end_drag(event)
        else:
            self._select_student(seat)
        self._clear_highlight()
        self.drag_data = {}

    def _start_drag_from_roster(self, event: tk.Event) -> None:
        idx = self.roster_listbox.nearest(event.y)
        if idx < 0 or idx >= self.roster_listbox.size():
            return
        self.roster_listbox.selection_clear(0, tk.END)
        self.roster_listbox.selection_set(idx)
        name = self.roster_listbox.get(idx)
        self.drag_data = {
            "source": "roster",
            "item": name,
            "dragging": False,
            "start": (event.x_root, event.y_root),
        }

    def _start_drag(self, name: str, x: int, y: int) -> None:
        self.drag_data["dragging"] = True
        self._show_drag_ghost(name, x, y)
        self._highlight_under_cursor(x, y)

    def _on_drag_motion(self, event: tk.Event) -> None:
        if not self.drag_data.get("source"):
            return
        start = self.drag_data.get("start")
        if not self.drag_data.get("dragging") and start:
            dx = abs(event.x_root - start[0])
            dy = abs(event.y_root - start[1])
            if dx < 5 and dy < 5:
                return
            item = self.drag_data.get("item")
            if item:
                self._start_drag(str(item), event.x_root, event.y_root)
            else:
                self._start_drag("(空席)", event.x_root, event.y_root)
        if not self.drag_data.get("dragging"):
            return
        if self.drag_ghost:
            self.drag_ghost.geometry(f"+{event.x_root+10}+{event.y_root+10}")
        self._highlight_under_cursor(event.x_root, event.y_root)

    def _highlight_under_cursor(self, x_root: int, y_root: int) -> None:
        widget = self.root.winfo_containing(x_root, y_root)
        if self.drag_ghost and widget and widget.winfo_toplevel() == self.drag_ghost:
            return
        if widget == self.highlight_widget:
            return
        self._clear_highlight()
        if widget in self.labels.values():
            widget.config(bg="#d6ecff", relief="solid", borderwidth=3)
            self.highlight_widget = widget
        elif widget == self.roster_listbox:
            self.roster_listbox.config(highlightthickness=2, highlightbackground="#4a90e2")
            self.highlight_widget = widget

    def _end_drag(self, event: tk.Event) -> None:
        if not self.drag_data.get("dragging"):
            self._hide_drag_ghost()
            return
        widget = self.root.winfo_containing(event.x_root, event.y_root)
        source = self.drag_data.get("source")
        source_seat = self.drag_data.get("seat")
        item = self.drag_data.get("item")
        if widget in self.labels.values():
            target_seat = next(k for k, v in self.labels.items() if v == widget)
            self._record_state()
            if source == "seat" and source_seat == target_seat:
                pass
            elif source in {"seat", "seat-empty"} and source_seat is not None:
                # moving from a seat
                if item:
                    self._assign_to_seat(target_seat, str(item), record=False)
                self._clear_seat_assignment(int(source_seat), record=False)
            elif source == "roster" and item:
                self._assign_to_seat(target_seat, str(item), record=False)
        elif widget == self.roster_listbox and source in {"seat", "seat-empty"} and source_seat:
            self._record_state()
            self._clear_seat_assignment(int(source_seat), record=False)
        self._hide_drag_ghost()
        self._clear_highlight()
        self.drag_data = {}

    def _clear_highlight(self) -> None:
        if self.highlight_widget in self.labels.values():
            seat = next(k for k, v in self.labels.items() if v == self.highlight_widget)
            self._style_label(seat)
        elif self.highlight_widget == self.roster_listbox:
            self.roster_listbox.config(highlightthickness=0)
        self.highlight_widget = None

    def _bind_shortcuts(self) -> None:
        if self._shortcuts_bound:
            return
        self.root.bind_all("<Control-z>", lambda *_: self.undo())
        self.root.bind_all("<Control-y>", lambda *_: self.redo())
        self.root.bind_all("<F11>", self._toggle_fullscreen)
        self._shortcuts_bound = True

    def _toggle_fullscreen(self, *_: object) -> None:
        self._fullscreen = not self._fullscreen
        self.root.attributes("-fullscreen", self._fullscreen)

    def undo(self) -> None:
        if not self.history:
            return
        self.redo_stack.append(self._take_snapshot())
        snapshot = self.history.pop()
        self._restore_snapshot(snapshot)

    def redo(self) -> None:
        if not self.redo_stack:
            return
        self.history.append(self._take_snapshot())
        snapshot = self.redo_stack.pop()
        self._restore_snapshot(snapshot)

    def _show_drag_ghost(self, text: str, x: int, y: int) -> None:
        self._hide_drag_ghost()
        ghost = tk.Toplevel(self.root)
        ghost.overrideredirect(True)
        tk.Label(ghost, text=text, bg="#4a90e2", fg="white", padx=6, pady=2).pack()
        ghost.attributes("-alpha", 0.85)
        ghost.lift()
        ghost.geometry(f"+{x+10}+{y+10}")
        self.drag_ghost = ghost

    def _hide_drag_ghost(self) -> None:
        if self.drag_ghost is not None:
            self.drag_ghost.destroy()
        self.drag_ghost = None

    def _select_student(self, seat: int) -> None:
        top = tk.Toplevel(self.root)
        top.title(f"Seat {seat}")
        search = tk.StringVar()
        tk.Entry(top, textvariable=search).pack(fill="x", padx=6, pady=(6, 2))
        listbox = tk.Listbox(top, height=15)
        options = []
        if seat in self.empty_seats:
            options.append("空席を解除")
        else:
            options.append("空席にする")
        options.append("テキスト")
        options.extend(d["name_kanji"] for d in self.students_sorted)
        options.extend(["教卓", "補助机"])

        filtered: list[str] = []

        def refresh_list(*_: object) -> None:
            query = search.get().strip()
            listbox.delete(0, tk.END)
            filtered.clear()
            for name in options:
                if name in self.student_data:
                    data = self.student_data[name]
                    if not self._matches_query(query, name, data.get("name_kana")):
                        continue
                elif not self._matches_query(query, name):
                    continue
                filtered.append(name)
                listbox.insert(tk.END, name)

        refresh_list()
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=4)
        scrollbar = tk.Scrollbar(top, command=listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=4, padx=(0, 6))
        listbox.config(yscrollcommand=scrollbar.set)
        search.trace_add("write", refresh_list)

        def choose() -> None:
            if not listbox.curselection():
                return
            name = listbox.get(listbox.curselection())
            top.destroy()
            self._assign_to_seat(seat, name)

        listbox.bind("<Double-Button-1>", lambda e: choose())
        tk.Button(top, text="OK", command=choose).pack(pady=(0, 6))

    def _ask_multiline(self, title: str) -> str | None:
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        text_widget = tk.Text(dialog, width=20, height=4)
        text_widget.pack(padx=5, pady=5)
        result: list[str] = []

        def ok() -> None:
            result.append(text_widget.get("1.0", tk.END).rstrip("\n"))
            dialog.destroy()

        def cancel() -> None:
            dialog.destroy()

        btn = tk.Frame(dialog)
        btn.pack(pady=5)
        tk.Button(btn, text="OK", command=ok).pack(side=tk.LEFT, padx=5)
        tk.Button(btn, text="キャンセル", command=cancel).pack(side=tk.LEFT, padx=5)
        dialog.transient(self.root)
        dialog.grab_set()
        self.root.wait_window(dialog)
        return result[0] if result else None

    def _assign_to_seat(self, seat: int, name: str, record: bool = True) -> None:
        if record:
            self._record_state()
        if name == "空席にする":
            if seat in self.assignments:
                del self.assignments[seat]
            self.empty_seats[seat] = ("", "black")
            self.fixed_seats.add(seat)
            self.labels[seat].config(text="", fg="black")
            self._style_label(seat)
            self._update_counts()
            return
        if name == "空席を解除":
            if seat in self.assignments:
                del self.assignments[seat]
            self.fixed_seats.discard(seat)
            self.empty_seats.pop(seat, None)
            self.labels[seat].config(text="", fg="black")
            self._style_label(seat)
            self._update_counts()
            return
        if name == "テキスト":
            if seat in self.assignments:
                del self.assignments[seat]
            text = self._ask_multiline("テキストを入力してください")
            if text is None:
                return
            colour = simpledialog.askstring(
                "文字色", "色名または#RRGGBBを入力してください", initialvalue="black"
            )
            if not colour:
                colour = "black"
            self.empty_seats[seat] = (text, colour)
            self.fixed_seats.add(seat)
            self.labels[seat].config(text=text, fg=colour, justify="left", anchor="w")
            self._style_label(seat)
            self._update_counts()
            return
        if name in ("教卓", "補助机"):
            if seat in self.assignments:
                del self.assignments[seat]
            self.empty_seats[seat] = (name, "black")
            self.fixed_seats.add(seat)
            self.labels[seat].config(text=name, fg="black")
            self._style_label(seat)
            self._update_counts()
            return

        data = self.student_data[name]
        prev_seat = None
        for s, stu in list(self.assignments.items()):
            if stu.name_kanji == name:
                prev_seat = s
                del self.assignments[s]
                self.labels[s].config(text="", fg="black")
                self.fixed_seats.discard(s)
                self.empty_seats.pop(s, None)
                self._style_label(s)
                break
        if seat in self.assignments:
            del self.assignments[seat]
        student = Student(
            seat_number=seat,
            serial=data["serial"],
            student_id=data["student_id"],
            name_kanji=data["name_kanji"],
            name_kana=data["name_kana"],
            gender=data.get("gender", "M"),
            color=colors.red if data.get("status") == "休学" else None,
        )
        self.assignments[seat] = student
        colour = "red" if student.color == colors.red else "black"
        self.labels[seat].config(text=self._format_student(student), fg=colour, justify="center", anchor="center")
        self.fixed_seats.add(seat)
        self.empty_seats.pop(seat, None)
        self._style_label(seat)
        self._update_counts()

    def _clear_seat_assignment(self, seat: int, record: bool = True) -> None:
        if record:
            self._record_state()
        if seat in self.assignments:
            del self.assignments[seat]
        self.fixed_seats.discard(seat)
        self.empty_seats.pop(seat, None)
        if seat in self.labels:
            self.labels[seat].config(text="", fg="black")
            self._style_label(seat)
        self._update_counts()

    def change_rows(self) -> None:
        current = len(self.layout)
        new_rows = simpledialog.askinteger(
            "行数", "新しい行数を入力", initialvalue=current, minvalue=1
        )
        if not new_rows or new_rows == current:
            return
        cols = max(len(r) for r in self.layout)
        new_layout = generate_layout(new_rows, cols)
        self._reset_layout(new_layout)

    def change_cols(self) -> None:
        current = max(len(r) for r in self.layout)
        new_cols = simpledialog.askinteger(
            "列数", "新しい列数を入力", initialvalue=current, minvalue=1
        )
        if not new_cols or new_cols == current:
            return
        rows = len(self.layout)
        new_layout = generate_layout(rows, new_cols)
        self._reset_layout(new_layout)

    def _reset_layout(self, new_layout: List[List[object]], record: bool = True) -> None:
        if record:
            self._record_state()
        self.layout = new_layout
        self.labels.clear()
        self.fixed_seats.clear()
        self.empty_seats.clear()
        self.assignments.clear()
        self.total_seats = sum(
            1 for row in self.layout for seat in row if isinstance(seat, int)
        )
        self.seat_numbers = sorted(
            seat for row in self.layout for seat in row if isinstance(seat, int)
        )
        for widget in self.root.winfo_children():
            widget.destroy()
        self._build_ui()

    def shuffle(self) -> None:
        self._record_state()
        fixed = {stu.name_kanji: seat for seat, stu in self.assignments.items() if seat in self.fixed_seats}
        try:
            shuffled = simple_shuffle(
                STUDENTS, self.layout, fixed=fixed, empty_seats=list(self.empty_seats.keys())
            )
        except ValueError as exc:
            messagebox.showerror("Error", str(exc))
            return
        self.assignments = {s.seat_number: s for s in shuffled}
        self.fixed_seats = set(fixed.values()) | set(self.empty_seats.keys())
        for seat, lbl in self.labels.items():
            student = self.assignments.get(seat)
            if student:
                text = self._format_student(student)
                colour = "red" if student.color == colors.red else "black"
                lbl.config(justify="center", anchor="center")
            elif seat in self.empty_seats:
                text, colour = self.empty_seats[seat]
                lbl.config(
                    justify="left" if text and text not in ("教卓", "補助机") else "center",
                    anchor="w" if text and text not in ("教卓", "補助机") else "center",
                )
            else:
                text = ""
                colour = "black"
            lbl.config(text=text, fg=colour)
            self._style_label(seat)
        self._update_counts()

    def save_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="seating.csv",
        )
        if not path:
            return
        headers = [
            "seat_number",
            "kind",
            "name_kanji",
            "serial",
            "student_id",
            "name_kana",
            "gender",
            "status",
            "color",
            "empty_text",
            "empty_color",
            "is_fixed",
        ]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for seat in self.seat_numbers:
                row = {h: "" for h in headers}
                row["seat_number"] = seat
                row["is_fixed"] = 1 if seat in self.fixed_seats else 0
                if seat in self.assignments:
                    stu = self.assignments[seat]
                    row.update(
                        {
                            "kind": "student",
                            "name_kanji": stu.name_kanji,
                            "serial": stu.serial,
                            "student_id": stu.student_id,
                            "name_kana": stu.name_kana,
                            "gender": stu.gender,
                            "status": "休学" if stu.color == colors.red else "在籍",
                            "color": getattr(stu.color, "hexval", lambda: "")(),
                        }
                    )
                elif seat in self.empty_seats:
                    text, colour = self.empty_seats[seat]
                    row.update(
                        {
                            "kind": "empty",
                            "empty_text": text,
                            "empty_color": colour,
                        }
                    )
                else:
                    row["kind"] = "open"
                writer.writerow(row)
        messagebox.showinfo("保存", f"CSV を保存しました: {path}")

    def load_csv(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv"), ("すべて", "*.*")])
        if not path:
            return
        self._record_state()
        try:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except Exception as exc:
            messagebox.showerror("読み込みエラー", str(exc))
            return

        self.assignments.clear()
        self.fixed_seats.clear()
        self.empty_seats.clear()

        valid_seats = set(self.seat_numbers)
        for row in rows:
            try:
                seat_num = int(row.get("seat_number", 0))
            except ValueError:
                continue
            if seat_num not in valid_seats:
                continue
            kind = row.get("kind", "").strip()
            is_fixed = row.get("is_fixed", "0") in {"1", "True", "true", "yes", "on"}
            if kind == "student" and row.get("name_kanji"):
                name = row["name_kanji"]
                if name in self.student_data:
                    data = self.student_data[name]
                else:
                    data = {
                        "serial": row.get("serial", ""),
                        "student_id": row.get("student_id", ""),
                        "name_kanji": name,
                        "name_kana": row.get("name_kana", ""),
                        "gender": row.get("gender", "M"),
                        "status": row.get("status", "在籍"),
                    }
                colour_val = row.get("color") or None
                colour = colors.red if data.get("status") == "休学" else None
                if colour_val:
                    try:
                        colour = colors.toColor(colour_val)
                    except Exception:
                        pass
                student = Student(
                    seat_number=seat_num,
                    serial=int(data.get("serial", 0) or 0),
                    student_id=str(data.get("student_id", "")),
                    name_kanji=str(data.get("name_kanji", "")),
                    name_kana=str(data.get("name_kana", "")),
                    gender=str(data.get("gender", "M")),
                    color=colour,
                )
                self.assignments[seat_num] = student
                if is_fixed:
                    self.fixed_seats.add(seat_num)
            elif kind == "empty":
                text = row.get("empty_text", "")
                colour = row.get("empty_color", "black") or "black"
                self.empty_seats[seat_num] = (text, colour)
                if is_fixed or text:
                    self.fixed_seats.add(seat_num)
            else:
                # Treat unknown or "open" kinds as a regular available seat
                if is_fixed:
                    self.fixed_seats.add(seat_num)

        for seat in self.seat_numbers:
            lbl = self.labels.get(seat)
            if lbl is None:
                continue
            if seat in self.assignments:
                stu = self.assignments[seat]
                colour = "red" if stu.color == colors.red else "black"
                lbl.config(text=self._format_student(stu), fg=colour, justify="center", anchor="center")
            elif seat in self.empty_seats:
                text, colour = self.empty_seats[seat]
                lbl.config(text=text, fg=colour)
            else:
                lbl.config(text="", fg="black")
            self._style_label(seat)
        self._update_counts()
        messagebox.showinfo("読み込み", f"CSV から座席を読み込みました: {path}")

    def save(self) -> None:
        safe_title = re.sub(r'[\\/:*?"<>|]', "_", self.title_var.get()) or "seat_chart"
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf"), ("PNG", "*.png"), ("JPEG", "*.jpg;*.jpeg")],
            initialfile=f"{safe_title}.pdf",
        )
        if not path:
            return
        base, ext = os.path.splitext(path)
        if ext.lower() in {".png", ".jpg", ".jpeg"}:
            tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            tmp.close()
            try:
                create_seat_chart(
                    list(self.assignments.values()),
                    seat_rows=self.layout,
                    committees=COMMITTEES,
                    title=self.title_var.get(),
                    output_path=tmp.name,
                    image_path=path,
                    fixed_seat_numbers=list(self.fixed_seats),
                    empty_seat_texts=self.empty_seats,
                )
                messagebox.showinfo("Saved", f"画像を書き出しました: {path}")
            finally:
                if os.path.exists(tmp.name):
                    os.remove(tmp.name)
        else:
            create_seat_chart(
                list(self.assignments.values()),
                seat_rows=self.layout,
                committees=COMMITTEES,
                title=self.title_var.get(),
                output_path=path,
                image_path=None,
                fixed_seat_numbers=list(self.fixed_seats),
                empty_seat_texts=self.empty_seats,
            )
            messagebox.showinfo("Saved", f"PDF を保存しました: {path}")

    def clear_all(self) -> None:
        self._record_state()
        self.assignments.clear()
        self.fixed_seats.clear()
        self.empty_seats.clear()
        for seat, lbl in self.labels.items():
            lbl.config(text="", fg="black")
            self._style_label(seat)
        self._update_counts()

    def _style_label(self, seat: int) -> None:
        lbl = self.labels[seat]
        student = self.assignments.get(seat)
        if seat in self.empty_seats:
            text, _ = self.empty_seats[seat]
            if text in ("教卓", "補助机"):
                lbl.config(
                    bg="white",
                    relief="solid",
                    borderwidth=2,
                    anchor="center",
                    justify="center",
                )
            elif text:
                lbl.config(
                    bg=self.default_bg,
                    relief="groove",
                    borderwidth=2,
                    anchor="w",
                    justify="left",
                )
            else:  # pure empty seat
                parent_bg = lbl.master.cget("bg") if lbl.master else self.default_bg
                lbl.config(
                    bg=parent_bg or self.default_bg,
                    relief="flat",
                    borderwidth=0,
                    anchor="center",
                    justify="center",
                )
        elif student and student.color == colors.red:
            lbl.config(
                bg=self.default_bg,
                relief="flat",
                borderwidth=0,
                anchor="center",
                justify="center",
            )
        else:
            bw = 4 if seat in self.fixed_seats else 2
            lbl.config(
                bg="white",
                relief="solid",
                borderwidth=bw,
                anchor="center",
                justify="center",
            )

    def _update_counts(self) -> None:
        seats_available = self.total_seats - len(self.empty_seats)
        text = f"席数: {seats_available} / 人数: {self.required_students}"
        if seats_available < self.required_students:
            text += " - 席が足りません"
            self.count_label.config(fg="red")
        else:
            self.count_label.config(fg="black")
        self.count_var.set(text)


def main() -> None:
    root = tk.Tk()
    root.title("Seat Shuffler")
    SeatApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
