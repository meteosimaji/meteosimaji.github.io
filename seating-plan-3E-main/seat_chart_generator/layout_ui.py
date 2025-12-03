"""Tkinter UI for editing the seat layout as a 2D array."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import List

from .layout import load_layout, save_layout


def edit_layout(path: str = "seat_layout.json") -> None:
    layout = load_layout(path)
    rows = tk.IntVar(value=len(layout))
    cols = tk.IntVar(value=max(len(r) for r in layout) if layout else 1)

    root = tk.Tk()
    root.title("Seat Layout Editor")

    grid_vars: List[List[tk.StringVar]] = []

    def build_grid() -> None:
        for widget in root.grid_slaves():
            if int(widget.grid_info().get("row", 0)) >= 2:
                widget.destroy()
        grid_vars.clear()
        for r in range(rows.get()):
            row_vars: List[tk.StringVar] = []
            for c in range(cols.get()):
                value = ""
                if r < len(layout) and c < len(layout[r]) and layout[r][c] is not None:
                    value = str(layout[r][c])
                var = tk.StringVar(value=value)
                tk.Entry(root, textvariable=var, width=5).grid(row=r + 2, column=c, padx=2, pady=2)
                row_vars.append(var)
            grid_vars.append(row_vars)

    def save() -> None:
        new_layout: List[List[int | None]] = []
        for row_vars in grid_vars:
            row: List[int | None] = []
            for var in row_vars:
                text = var.get().strip()
                if text:
                    row.append(int(text))
                else:
                    row.append(None)
            new_layout.append(row)
        save_layout(new_layout, path)
        messagebox.showinfo("Saved", "Seat layout saved!")

    tk.Label(root, text="Rows").grid(row=0, column=0)
    tk.Spinbox(root, from_=1, to=20, textvariable=rows, width=5, command=build_grid).grid(row=0, column=1)
    tk.Label(root, text="Columns").grid(row=0, column=2)
    tk.Spinbox(root, from_=1, to=20, textvariable=cols, width=5, command=build_grid).grid(row=0, column=3)
    tk.Button(root, text="Save", command=save).grid(row=1, column=0, columnspan=4, pady=5)

    build_grid()
    root.mainloop()


if __name__ == "__main__":
    edit_layout()
