"""Data definitions for the timetable solver.

All static inputs are co-located here so that the solver and UI can import a
single source of truth.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Set, Tuple

DAYS: Tuple[str, ...] = ("Mon", "Tue", "Wed", "Thu", "Fri")
DAY_ORDER: Dict[str, int] = {day: idx for idx, day in enumerate(DAYS)}
TRACKS: Tuple[int, ...] = (1, 2, 3, 4)

# Slots available per day. Friday is limited to slots 4 and 5.
SLOTS_BY_DAY: Dict[str, Tuple[int, ...]] = {
    "Mon": (1, 2, 3, 4, 5),
    "Tue": (1, 2, 3, 4, 5),
    "Wed": (1, 2, 3, 4, 5),
    "Thu": (1, 2, 3, 4, 5),
    "Fri": (4, 5),
}

# Teacher availability map expressed as allowed slots per day.
TEACHER_AVAILABILITY: Dict[str, Dict[str, Tuple[int, ...]]] = {
    "Sanya": {
        "Mon": (1, 2, 3, 4, 5),
        "Tue": (1, 2, 3, 4, 5),
        "Wed": (1, 2, 3, 4, 5),
    },
    "Usha": {
        "Mon": (1, 2, 3, 4, 5),
        "Wed": (1, 2, 3, 4, 5),
        "Thu": (1, 2, 3, 4),
    },
    "Guru": {
        "Mon": (1, 2, 3, 4, 5),
        "Wed": (1, 2, 3, 4, 5),
        "Thu": (1, 2, 3, 4),
    },
    "Gayatri": {
        "Tue": (1, 2, 3, 4, 5),
        "Thu": (1, 2, 3, 4),
    },
    "Zeba": {
        "Mon": (1, 2, 3, 4, 5),
        "Tue": (1, 2, 3, 4, 5),
        "Wed": (1, 2, 3, 4, 5),
        "Thu": (1, 2, 3, 4),
        "Fri": (4, 5),
    },
    "Shravani": {
        "Mon": (1, 2, 3, 4, 5),
        "Tue": (1, 2, 3, 4, 5),
        "Wed": (1, 2, 3, 4, 5),
        "Thu": (1, 2, 3, 4),
        "Fri": (4, 5),
    },
}


@dataclass(frozen=True)
class SessionTemplate:
    teacher: str
    code: str
    subject: str
    multiplicity: int
    students: Tuple[str, ...]


@dataclass(frozen=True)
class SessionInstance:
    uid: str
    teacher: str
    code: str
    subject: str
    students: Tuple[str, ...]


@dataclass
class TimetableData:
    days: Tuple[str, ...]
    day_order: Dict[str, int]
    slots_by_day: Dict[str, Tuple[int, ...]]
    tracks: Tuple[int, ...]
    teacher_availability: Dict[str, Set[Tuple[str, int]]]
    sessions: List[SessionInstance]
    teachers: Tuple[str, ...]
    students: Tuple[str, ...]

    def is_teacher_available(self, teacher: str, day: str, slot: int) -> bool:
        return (day, slot) in self.teacher_availability.get(teacher, set())


def _session_templates() -> Sequence[SessionTemplate]:
    """Return the full list of repeating session templates."""

    def st(teacher: str, code: str, subject: str, multiplicity: int, students: Iterable[str]) -> SessionTemplate:
        return SessionTemplate(teacher=teacher, code=code, subject=subject, multiplicity=multiplicity, students=tuple(students))

    return (
        # Sanya (Math)
        st("Sanya", "Sanya_1", "Math", 3, ["Ekaansh", "Parth"]),
        st("Sanya", "Sanya_2", "Math", 3, ["Nithil", "Aakash", "Nuha", "Karthika"]),
        st("Sanya", "Sanya_3", "Math", 3, ["Ishita", "Abhigya", "Sathvik"]),
        st("Sanya", "Sanya_4", "Math", 3, ["Neil", "Mohammad"]),
        # Usha (Math)
        st("Usha", "Usha_1", "Math", 3, ["Anshika", "Asmi", "Arjun", "Arhat"]),
        st("Usha", "Usha_2", "Math", 3, ["Aashmi", "Arhan", "Trisha", "Vedaant", "Kanav"]),
        st("Usha", "Usha_3", "Math", 3, ["Archana", "Myra", "Mythili", "Shlok"]),
        st("Usha", "Usha_4", "Math", 2, ["Anik", "Sahan", "Sayan"]),
        st("Usha", "Usha_5", "Math", 3, ["Sruthi"]),
        # Gayatri (English)
        st("Gayatri", "Eng_1", "English", 2, ["Ekaansh", "Aakash"]),
        st("Gayatri", "Eng_2", "English", 2, ["Aashmi", "Abhigya", "Ishita", "Neil", "Nithil", "Sathvik", "Sayan", "Arjun", "Mohammad"]),
        st("Gayatri", "Eng_3", "English", 2, ["Anik", "Parth", "Arhan", "Arhat", "Karthika", "Kanav"]),
        st("Gayatri", "Eng_4", "English", 1, ["Anshika", "Archana", "Myra", "Mythili", "Trisha"]),
        st("Gayatri", "Eng_5", "English", 1, ["Asmi", "Nuha", "Sahan", "Shlok", "Sruthi", "Vedaant"]),
        # Shravani (Science)
        st("Shravani", "Sci_1", "Science", 3, ["Neil", "Aakash", "Arhat", "Abhigya", "Sruthi"]),
        st("Shravani", "Sci_2", "Science", 3, ["Mohammad", "Ekaansh", "Ishita", "Nuha", "Karthika"]),
        # Zeba (SST / English cover)
        st("Zeba", "SST_1", "SST", 3, ["Arhat", "Neil", "Parth", "Ekaansh", "Karthika", "Nithil", "Aakash"]),
        st("Zeba", "SST_2", "SST", 3, ["Anik", "Mohammad", "Arjun", "Sathvik"]),
        st("Zeba", "SST_3", "SST", 2, ["Kanav", "Abhigya", "Sruthi", "Nuha", "Sahan", "Sayan", "Ishita"]),
        st("Zeba", "SST_4", "SST", 2, ["Arhan", "Asmi", "Anshika", "Trisha", "Aashmi"]),
        st("Zeba", "SST_5", "SST", 2, ["Myra", "Mythili", "Archana", "Vedaant", "Shlok"]),
        st("Zeba", "Eng_1", "English", 1, ["Ekaansh", "Aakash"]),
        # Guru (Science + Math cover)
        st("Guru", "Sci_3", "Science", 2, ["Aashmi", "Vedaant", "Anshika", "Archana", "Asmi", "Sahan"]),
        st("Guru", "Sci_4", "Science", 2, ["Arhan", "Arjun", "Nithil", "Parth", "Sathvik", "Anik"]),
        st("Guru", "Sci_5", "Science", 2, ["Kanav", "Myra", "Sayan", "Trisha", "Mythili", "Shlok"]),
        st("Guru", "Sanya_1", "Math", 1, ["Ekaansh", "Parth"]),
    )


def expand_templates(templates: Sequence[SessionTemplate]) -> List[SessionInstance]:
    """Expand templates into unique session instances."""
    expanded: List[SessionInstance] = []
    for template in templates:
        for idx in range(1, template.multiplicity + 1):
            uid = f"{template.code}_{template.teacher}_{idx}"
            expanded.append(
                SessionInstance(
                    uid=uid,
                    teacher=template.teacher,
                    code=template.code,
                    subject=template.subject,
                    students=template.students,
                )
            )
    return expanded


def _flatten_teacher_availability() -> Dict[str, Set[Tuple[str, int]]]:
    flat: Dict[str, Set[Tuple[str, int]]] = {}
    for teacher, day_map in TEACHER_AVAILABILITY.items():
        slots: Set[Tuple[str, int]] = set()
        for day, day_slots in day_map.items():
            for slot in day_slots:
                slots.add((day, slot))
        flat[teacher] = slots
    return flat


def _collect_students(instances: Sequence[SessionInstance]) -> Tuple[str, ...]:
    unique: Set[str] = set()
    for inst in instances:
        unique.update(inst.students)
    return tuple(sorted(unique))


def _collect_teachers(instances: Sequence[SessionInstance]) -> Tuple[str, ...]:
    unique: Set[str] = {inst.teacher for inst in instances}
    return tuple(sorted(unique))


def load_data() -> TimetableData:
    """Load all static inputs for the solver."""
    instances = expand_templates(_session_templates())
    return TimetableData(
        days=DAYS,
        day_order=DAY_ORDER,
        slots_by_day=SLOTS_BY_DAY,
        tracks=TRACKS,
        teacher_availability=_flatten_teacher_availability(),
        sessions=instances,
        teachers=_collect_teachers(instances),
        students=_collect_students(instances),
    )


__all__ = ["TimetableData", "SessionInstance", "load_data"]
