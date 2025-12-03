from __future__ import annotations

import tkinter as tk
from tkinter import filedialog
from typing import List

from seat_chart_generator.layout import load_layout, save_layout

STATE_SEQUENCE = ["seat", "empty"]
STATE_LABELS = {
    "seat": "座席",
    "empty": "",
}


class LayoutEditor:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.layout_states: List[List[str]] = []
        self.buttons: List[List[tk.Button]] = []
        self.row_var = tk.IntVar()
        self.col_var = tk.IntVar()
        self.grid_frame: tk.Frame | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        current = load_layout()
        rows = len(current)
        cols = max(len(r) for r in current) if current else 1
        self.row_var.set(rows)
        self.col_var.set(cols)

        control = tk.Frame(self.root)
        control.grid(row=0, column=0, columnspan=cols, sticky="w", padx=5, pady=5)
        tk.Label(control, text="行").grid(row=0, column=0)
        tk.Spinbox(
            control,
            from_=1,
            to=20,
            textvariable=self.row_var,
            width=5,
            command=self._resize_grid,
        ).grid(row=0, column=1, padx=(0, 10))
        tk.Label(control, text="列").grid(row=0, column=2)
        tk.Spinbox(
            control,
            from_=1,
            to=20,
            textvariable=self.col_var,
            width=5,
            command=self._resize_grid,
        ).grid(row=0, column=3)

        self.grid_frame = tk.Frame(self.root)
        self.grid_frame.grid(row=1, column=0)

        self._load_initial_states(current)
        self._build_grid()

        tk.Button(self.root, text="保存", command=self.save).grid(row=2, column=0, pady=5)

    def _load_initial_states(self, current: List[List[object]]) -> None:
        self.layout_states.clear()
        for r in range(self.row_var.get()):
            state_row: List[str] = []
            for c in range(self.col_var.get()):
                state = "seat"
                if r < len(current) and c < len(current[r]):
                    cell = current[r][c]
                    if cell is None:
                        state = "empty"
                state_row.append(state)
            self.layout_states.append(state_row)

    def _build_grid(self) -> None:
        if not self.grid_frame:
            return
        for widget in self.grid_frame.winfo_children():
            widget.destroy()
        self.buttons = []
        for r, row in enumerate(self.layout_states):
            btn_row: List[tk.Button] = []
            for c, state in enumerate(row):
                btn = tk.Button(self.grid_frame, text=STATE_LABELS[state], width=6)
                btn.grid(row=r, column=c, padx=2, pady=2)
                btn.configure(command=lambda rr=r, cc=c: self._cycle_state(rr, cc))
                btn_row.append(btn)
            self.buttons.append(btn_row)

    def _resize_grid(self) -> None:
        rows = self.row_var.get()
        cols = self.col_var.get()
        new_states: List[List[str]] = []
        for r in range(rows):
            row: List[str] = []
            for c in range(cols):
                if r < len(self.layout_states) and c < len(self.layout_states[r]):
                    row.append(self.layout_states[r][c])
                else:
                    row.append("seat")
            new_states.append(row)
        self.layout_states = new_states
        self._build_grid()

    def _cycle_state(self, r: int, c: int) -> None:
        state = self.layout_states[r][c]
        idx = STATE_SEQUENCE.index(state)
        new_state = STATE_SEQUENCE[(idx + 1) % len(STATE_SEQUENCE)]
        self.layout_states[r][c] = new_state
        self.buttons[r][c].config(text=STATE_LABELS[new_state])

    def save(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile="seat_layout.json",
        )
        if not path:
            return
        layout: List[List[object]] = []
        seat_num = 1
        for row in self.layout_states:
            layout_row = []
            for state in row:
                if state == "seat":
                    layout_row.append(seat_num)
                    seat_num += 1
                else:
                    layout_row.append(None)
            layout.append(layout_row)
        save_layout(layout, path)


def main() -> None:
    root = tk.Tk()
    root.title("Layout Editor")
    LayoutEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()
