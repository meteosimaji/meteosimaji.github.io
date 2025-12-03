from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from reportlab.lib import colors


@dataclass
class Student:
    """Representation of a single student for the seat chart."""

    seat_number: int
    serial: int
    student_id: str
    name_kanji: str
    name_kana: str
    gender: str = "M"
    special_needs: bool = False
    color: Optional[colors.Color] = None

    def __post_init__(self) -> None:
        self.serial = int(self.serial)
        self.student_id = str(self.student_id).strip()
        self.name_kanji = str(self.name_kanji).strip()
        self.name_kana = str(self.name_kana).strip()
        self.gender = str(self.gender).strip().upper()
