"""Shuffle student seating and generate a seat chart."""

from __future__ import annotations

import re

from seat_chart_generator import create_seat_chart, load_layout, simple_shuffle
from students import STUDENTS, COMMITTEES


def main() -> None:
    seat_rows = load_layout()
    students = simple_shuffle(STUDENTS, seat_rows)
    title = "席替え座席表"
    safe_title = re.sub(r'[\\/:*?"<>|]', "_", title)
    create_seat_chart(
        students,
        seat_rows=seat_rows,
        committees=COMMITTEES,
        title=title,
        output_path=f"{safe_title}.pdf",
        image_path=f"{safe_title}.png",
    )


if __name__ == "__main__":
    main()
