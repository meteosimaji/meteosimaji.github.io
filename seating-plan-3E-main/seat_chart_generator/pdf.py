"""PDF generation for seat charts."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.colors import HexColor, toColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

from .models import Student
from .assignment import assign_students_to_seats


def _draw_centered_text(
    canv: canvas.Canvas,
    x: float,
    y: float,
    text: str,
    font_name: str,
    font_size: float,
    colour: colors.Color = colors.black,
    max_width: Optional[float] = None,
) -> None:
    if max_width is not None:
        width = pdfmetrics.stringWidth(text, font_name, font_size)
        if width > max_width:
            scale = max_width / width
            font_size *= scale
    canv.setFont(font_name, font_size)
    canv.setFillColor(colour)
    text_width = pdfmetrics.stringWidth(text, font_name, font_size)
    canv.drawString(x - text_width / 2.0, y, text)


def _parse_colour(value: str) -> colors.Color:
    try:
        if value.startswith("#"):
            return HexColor(value)
        return toColor(value)
    except Exception:
        return colors.black


def create_seat_chart(
    students: List[Student],
    seat_rows: List[List[Optional[int]]] | None = None,
    reserved_students: Iterable[str] = (),
    reserved_seat_numbers: Optional[List[int]] = None,
    committees: Optional[List[Tuple[str, List[str]]]] = None,
    title: str = "座席表",
    exam_notice: Optional[str] = None,
    output_path: str = "seat_chart.pdf",
    image_path: str | None = None,
    fixed_seat_numbers: Iterable[int] = (),
    empty_seat_texts: Optional[Dict[int, Tuple[str, str]]] = None,
) -> None:
    if seat_rows is None:
        from .layout import DEFAULT_SEAT_ROWS

        seat_rows = DEFAULT_SEAT_ROWS

    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))

    assignments: Dict[int, Student] = assign_students_to_seats(
        students, seat_rows, reserved_students, reserved_seat_numbers
    )

    empty_seat_texts = empty_seat_texts or {}

    page_width, page_height = A4
    c = canvas.Canvas(output_path, pagesize=A4)
    c.setTitle(title)

    margin_top = 35 * mm
    margin_side = 15 * mm

    committee_line_height = 7 * mm
    committees_height = committee_line_height * len(committees or [])
    margin_bottom = 15 * mm
    committee_gap = 5 * mm if committees else 0
    grid_top = page_height - margin_top
    grid_bottom = margin_bottom + committees_height + committee_gap
    grid_height = grid_top - grid_bottom

    seat_rows_filtered = [row for row in seat_rows if any(isinstance(s, int) for s in row)]
    num_rows = len(seat_rows_filtered)

    max_seats_in_row = max(len([s for s in row if isinstance(s, int)]) for row in seat_rows)
    available_width = page_width - 2 * margin_side
    seat_width = 38 * mm
    gap_h = 6 * mm
    total_width = max_seats_in_row * seat_width + (max_seats_in_row - 1) * gap_h
    if total_width > available_width:
        scale = available_width / total_width
        seat_width *= scale
        gap_h *= scale

    seat_height_base = 22 * mm
    gap_ratio = 5.0 / 22.0
    denom = num_rows + gap_ratio * (num_rows - 1)
    seat_height_fitted = grid_height / denom
    seat_height = seat_height_fitted if seat_height_base > seat_height_fitted else seat_height_base
    gap_v = seat_height * gap_ratio

    total_rows_height = num_rows * seat_height + (num_rows - 1) * gap_v
    y_start = grid_top - (grid_height - total_rows_height) / 2.0 - seat_height

    first_row_top: float | None = None
    last_row_y = None
    row_index = 0
    fixed_seats = set(fixed_seat_numbers)
    for row in seat_rows:
        seats_in_row = [s for s in row if isinstance(s, int)]
        if not seats_in_row:
            continue
        num_seats = len(seats_in_row)
        row_width = num_seats * seat_width + (num_seats - 1) * gap_h
        x_start = margin_side + (available_width - row_width) / 2.0
        y = y_start - (seat_height + gap_v) * row_index
        for seat_num in row:
            if not isinstance(seat_num, int):
                continue
            x = x_start
            student = assignments.get(seat_num)
            is_fixed = seat_num in fixed_seats
            if student is None and not is_fixed:
                x_start += seat_width + gap_h
                continue
            if student and student.color == colors.red:
                text_colour = student.color
                top_margin = seat_height * 0.05
                line_gap = seat_height * 0.04
                serial_font_size = seat_height * 0.18
                id_font_size = seat_height * 0.18
                name_font_size = seat_height * 0.34
                kana_font_size = seat_height * 0.18
                _draw_centered_text(
                    c,
                    x + seat_width / 2.0,
                    y + seat_height + serial_font_size * 0.1,
                    str(student.serial),
                    font_name="HeiseiKakuGo-W5",
                    font_size=serial_font_size,
                    colour=text_colour,
                    max_width=seat_width - 4 * mm,
                )
                current_y = y + seat_height - top_margin
                current_y -= id_font_size
                _draw_centered_text(
                    c,
                    x + seat_width / 2.0,
                    current_y,
                    student.student_id,
                    font_name="HeiseiKakuGo-W5",
                    font_size=id_font_size,
                    colour=text_colour,
                    max_width=seat_width - 4 * mm,
                )
                current_y -= line_gap
                current_y -= name_font_size
                _draw_centered_text(
                    c,
                    x + seat_width / 2.0,
                    current_y,
                    student.name_kanji,
                    font_name="HeiseiKakuGo-W5",
                    font_size=name_font_size,
                    colour=text_colour,
                    max_width=seat_width - 6 * mm,
                )
                current_y -= line_gap
                current_y -= kana_font_size
                _draw_centered_text(
                    c,
                    x + seat_width / 2.0,
                    current_y,
                    student.name_kana,
                    font_name="HeiseiKakuGo-W5",
                    font_size=kana_font_size,
                    colour=text_colour,
                    max_width=seat_width - 6 * mm,
                )
                x_start += seat_width + gap_h
                continue
            text, colour = empty_seat_texts.get(seat_num, ("", "black"))
            if student is None:
                if not text:
                    x_start += seat_width + gap_h
                    continue
                if text in ("教卓", "補助机"):
                    line_width = 1
                    c.setLineWidth(line_width)
                    c.setStrokeColor(colors.black)
                    c.setFillColor(colors.white)
                    c.rect(x, y, seat_width, seat_height, stroke=1, fill=1)
                    lines = text.splitlines()
                    font_size = seat_height * 0.35
                    line_height = font_size * 1.2
                    total_height = line_height * len(lines)
                    start_y = y + (seat_height + total_height) / 2.0 - line_height
                    for idx, line in enumerate(lines):
                        _draw_centered_text(
                            c,
                            x + seat_width / 2.0,
                            start_y - idx * line_height,
                            line,
                            font_name="HeiseiKakuGo-W5",
                            font_size=font_size,
                            colour=_parse_colour(colour),
                            max_width=seat_width - 4 * mm,
                        )
                    x_start += seat_width + gap_h
                    continue
                lines = text.splitlines()
                font_size = seat_height * 0.35
                line_height = font_size * 1.2
                total_height = line_height * len(lines)
                start_y = y + (seat_height + total_height) / 2.0 - line_height
                for idx, line in enumerate(lines):
                    _draw_centered_text(
                        c,
                        x + seat_width / 2.0,
                        start_y - idx * line_height,
                        line,
                        font_name="HeiseiKakuGo-W5",
                        font_size=font_size,
                        colour=_parse_colour(colour),
                        max_width=seat_width - 4 * mm,
                    )
                x_start += seat_width + gap_h
                continue
            # Fixed seats were previously drawn thicker, but now all seats use
            # the same line width for consistency.
            c.setLineWidth(1)
            c.setStrokeColor(colors.black)
            c.setFillColor(colors.white)
            c.rect(x, y, seat_width, seat_height, stroke=1, fill=1)
            if student.gender == "F":
                inner = 1.5
                c.rect(
                    x + inner,
                    y + inner,
                    seat_width - 2 * inner,
                    seat_height - 2 * inner,
                    stroke=1,
                    fill=0,
                )
            if student.special_needs:
                text_colour = colors.red
            else:
                text_colour = colors.black
            if student.color is not None:
                text_colour = student.color
            top_margin = seat_height * 0.05
            line_gap = seat_height * 0.04
            serial_font_size = seat_height * 0.18
            id_font_size = seat_height * 0.18
            name_font_size = seat_height * 0.34
            kana_font_size = seat_height * 0.18

            # Draw serial number above the desk to provide more space inside
            _draw_centered_text(
                c,
                x + seat_width / 2.0,
                y + seat_height + serial_font_size * 0.1,
                str(student.serial),
                font_name="HeiseiKakuGo-W5",
                font_size=serial_font_size,
                colour=text_colour,
                max_width=seat_width - 4 * mm,
            )

            current_y = y + seat_height - top_margin

            current_y -= id_font_size
            _draw_centered_text(
                c,
                x + seat_width / 2.0,
                current_y,
                student.student_id,
                font_name="HeiseiKakuGo-W5",
                font_size=id_font_size,
                colour=text_colour,
                max_width=seat_width - 4 * mm,
            )
            current_y -= line_gap

            current_y -= name_font_size
            _draw_centered_text(
                c,
                x + seat_width / 2.0,
                current_y,
                student.name_kanji,
                font_name="HeiseiKakuGo-W5",
                font_size=name_font_size,
                colour=text_colour,
                max_width=seat_width - 6 * mm,
            )
            current_y -= line_gap

            current_y -= kana_font_size
            _draw_centered_text(
                c,
                x + seat_width / 2.0,
                current_y,
                student.name_kana,
                font_name="HeiseiKakuGo-W5",
                font_size=kana_font_size,
                colour=text_colour,
                max_width=seat_width - 6 * mm,
            )
            x_start += seat_width + gap_h
        if first_row_top is None:
            first_row_top = y + seat_height
        last_row_y = y
        row_index += 1

    if committees:
        col1_width = available_width * 0.3
        col23_width = (available_width - col1_width) / 2.0
        committee_font_size = 10
        y = margin_bottom
        for name, members in reversed(committees):
            main = members[0] if members else ""
            sub = members[1] if len(members) > 1 else "／"
            x = margin_side
            c.rect(x, y, col1_width, committee_line_height)
            _draw_centered_text(
                c,
                x + col1_width / 2.0,
                y + (committee_line_height - committee_font_size) / 2.0,
                name,
                font_name="HeiseiKakuGo-W5",
                font_size=committee_font_size,
            )
            x += col1_width
            c.rect(x, y, col23_width, committee_line_height)
            _draw_centered_text(
                c,
                x + col23_width / 2.0,
                y + (committee_line_height - committee_font_size) / 2.0,
                main,
                font_name="HeiseiKakuGo-W5",
                font_size=committee_font_size,
            )
            x += col23_width
            c.rect(x, y, col23_width, committee_line_height)
            _draw_centered_text(
                c,
                x + col23_width / 2.0,
                y + (committee_line_height - committee_font_size) / 2.0,
                sub,
                font_name="HeiseiKakuGo-W5",
                font_size=committee_font_size,
            )
            y += committee_line_height

    if exam_notice:
        lines = exam_notice.split("\n")
        notice_font_size = 12
        notice_width = max(
            pdfmetrics.stringWidth(line, "HeiseiKakuGo-W5", notice_font_size) for line in lines
        )
        x_pos = page_width - margin_side - notice_width
        y_pos = (last_row_y - seat_height) - 15 * mm
        for i, line in enumerate(lines):
            c.setFont("HeiseiKakuGo-W5", notice_font_size)
            c.setFillColor(colors.blue)
            c.drawString(
                x_pos,
                y_pos + notice_font_size * 1.2 * (len(lines) - i - 1),
                line,
            )

    if first_row_top is not None:
        title_y = first_row_top + 10 * mm
    else:
        title_y = page_height - 20 * mm
    title_font_size = 18
    title_width = pdfmetrics.stringWidth(title, "HeiseiKakuGo-W5", title_font_size)
    c.setFont("HeiseiKakuGo-W5", title_font_size)
    c.setFillColor(colors.black)
    title_x = (page_width - title_width) / 2.0
    c.drawString(title_x, title_y, title)
    underline_offset = 2
    c.line(title_x, title_y - underline_offset, title_x + title_width, title_y - underline_offset)

    c.save()
    if image_path:
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(output_path)
            page = doc.load_page(0)
            pix = page.get_pixmap(matrix=fitz.Matrix(4, 4))
            pix.save(image_path)
        except Exception as exc:
            print(f"画像の保存に失敗しました: {exc}")
