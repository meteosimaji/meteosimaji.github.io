"""Seat assignment logic."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from .models import Student


def assign_students_to_seats(
    students: List[Student],
    seat_rows: List[List[int]],
    reserved_students: Iterable[str] = (),
    reserved_seat_numbers: Optional[List[int]] = None,
) -> Dict[int, Student]:
    """Assign students to seats, respecting priority requests."""
    reserved_students_set = {name.strip() for name in reserved_students}
    for s in students:
        if s.name_kanji in reserved_students_set:
            s.special_needs = True

    seats_available: List[int] = [n for row in seat_rows for n in row if isinstance(n, int)]

    if reserved_seat_numbers:
        reserved_queue: List[int] = [n for n in reserved_seat_numbers if n in seats_available]
    else:
        reserved_queue = []
        for row in seat_rows:
            for seat in row:
                if seat in seats_available:
                    reserved_queue.append(seat)
            if reserved_queue:
                pass

    special_students: List[Student] = [s for s in students if s.special_needs]
    assignments: Dict[int, Student] = {s.seat_number: s for s in students}

    if special_students:
        reserved_queue = reserved_queue[: len(special_students)] if reserved_queue else []
        special_students.sort(key=lambda s: s.seat_number)
        for seat, student in zip(reserved_queue, special_students):
            if assignments.get(seat) is None or assignments[seat] is student:
                if assignments.get(student.seat_number) is student:
                    del assignments[student.seat_number]
                student.seat_number = seat
                assignments[seat] = student

    return assignments
