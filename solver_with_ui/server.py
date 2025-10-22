"""Timetable solver and lightweight HTTP server."""
from __future__ import annotations

import csv
import json
import signal
from collections import defaultdict
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

from ortools.sat.python import cp_model

try:  # Allow running as `python server.py` or `python -m solver_with_ui.server`.
    from .data_model import TimetableData, load_data
except ImportError:  # pragma: no cover - fallback for script execution
    from data_model import TimetableData, load_data  # type: ignore

BASE_DIR = Path(__file__).resolve().parent
UI_DIR = BASE_DIR / "ui"
JSON_PATH = BASE_DIR / "timetable.json"
HARD_CSV = BASE_DIR / "timetable.csv"
SOFT_CSV = BASE_DIR / "relaxed_timetable.csv"

HARD_SOLVER_TIME = 5.0  # seconds
SOFT_SOLVER_TIME = 15.0  # seconds

TIMETABLE_PAYLOAD: Optional[Dict[str, object]] = None
TIMETABLE_SOURCE: Optional[str] = None


@dataclass
class SolveOutcome:
    entries: Optional[List[Dict[str, object]]]
    status: int


def _candidate_slots(session, data: TimetableData) -> List[Tuple[str, int]]:
    slots: List[Tuple[str, int]] = []
    for day in data.days:
        for slot in data.slots_by_day.get(day, ()):  # type: ignore[arg-type]
            if data.is_teacher_available(session.teacher, day, slot):
                slots.append((day, slot))
    return slots


def build_greedy_seed(data: TimetableData) -> Dict[str, Tuple[str, int]]:
    day_cap: Dict[Tuple[str, int], int] = defaultdict(int)
    teacher_busy: Dict[Tuple[str, str, int], bool] = {}
    student_slot_busy: Dict[Tuple[str, str, int], bool] = {}
    student_subject_day: Dict[Tuple[str, str, str], bool] = {}
    student_daily_count: Dict[Tuple[str, str], int] = defaultdict(int)

    all_candidates: Dict[str, List[Tuple[str, int]]] = {
        session.uid: _candidate_slots(session, data) for session in data.sessions
    }

    order = sorted(
        data.sessions,
        key=lambda s: (len(all_candidates[s.uid]), -len(s.students), s.teacher, s.code),
    )

    seed: Dict[str, Tuple[str, int]] = {}

    for session in order:
        candidates = all_candidates[session.uid]
        if not candidates:
            return {}
        candidates.sort(
            key=lambda item: (day_cap[item], data.day_order[item[0]], item[1])
        )
        chosen: Optional[Tuple[str, int]] = None
        for day, slot in candidates:
            if teacher_busy.get((session.teacher, day, slot)):
                continue
            if day_cap[(day, slot)] >= 4:
                continue
            violation = False
            for student in session.students:
                if student_slot_busy.get((student, day, slot)):
                    violation = True
                    break
                if student_subject_day.get((student, day, session.subject)):
                    violation = True
                    break
                if student_daily_count[(student, day)] >= 3:
                    violation = True
                    break
            if violation:
                continue
            chosen = (day, slot)
            break

        if chosen is None:
            return {}

        day, slot = chosen
        seed[session.uid] = chosen
        day_cap[(day, slot)] += 1
        teacher_busy[(session.teacher, day, slot)] = True
        for student in session.students:
            student_slot_busy[(student, day, slot)] = True
            student_subject_day[(student, day, session.subject)] = True
            student_daily_count[(student, day)] += 1

    return seed


def _build_model(
    data: TimetableData,
    relax: bool,
    seed: Optional[Dict[str, Tuple[str, int]]] = None,
) -> Tuple[cp_model.CpModel, Dict[Tuple[str, str, int], cp_model.IntVar]]:
    model = cp_model.CpModel()
    assignment: Dict[Tuple[str, str, int], cp_model.IntVar] = {}
    session_vars: Dict[str, List[cp_model.IntVar]] = defaultdict(list)
    teacher_day_slot: Dict[Tuple[str, str, int], List[cp_model.IntVar]] = defaultdict(list)
    student_day_slot: Dict[Tuple[str, str, int], List[cp_model.IntVar]] = defaultdict(list)
    student_day_subject: Dict[Tuple[str, str, str], List[cp_model.IntVar]] = defaultdict(list)
    student_day_total: Dict[Tuple[str, str], List[cp_model.IntVar]] = defaultdict(list)
    day_slot_capacity: Dict[Tuple[str, int], List[cp_model.IntVar]] = defaultdict(list)

    for session in data.sessions:
        for day in data.days:
            for slot in data.slots_by_day.get(day, ()):  # type: ignore[arg-type]
                if not data.is_teacher_available(session.teacher, day, slot):
                    continue
                var = model.NewBoolVar(f"x_{session.uid}_{day}_{slot}")
                assignment[(session.uid, day, slot)] = var
                session_vars[session.uid].append(var)
                teacher_day_slot[(session.teacher, day, slot)].append(var)
                day_slot_capacity[(day, slot)].append(var)
                for student in session.students:
                    student_day_slot[(student, day, slot)].append(var)
                    student_day_subject[(student, day, session.subject)].append(var)
                    student_day_total[(student, day)].append(var)

    for session in data.sessions:
        vars_for_session = session_vars.get(session.uid)
        if not vars_for_session:
            raise ValueError(f"No feasible slots for session {session.uid}")
        model.Add(sum(vars_for_session) == 1)

    penalties: List[Tuple[cp_model.IntVar, int]] = []

    def add_upper_bound(
        vars_list: Sequence[cp_model.IntVar],
        limit: int,
        weight: int,
        label: str,
        enforce_hard: bool = False,
    ) -> None:
        if not vars_list:
            return
        if enforce_hard or not relax:
            model.Add(sum(vars_list) <= limit)
            return
        if len(vars_list) <= limit:
            model.Add(sum(vars_list) <= limit)
            return
        slack = model.NewIntVar(0, len(vars_list) - limit, f"slack_{label}_{len(penalties)}")
        model.Add(sum(vars_list) <= limit + slack)
        penalties.append((slack, weight))

    for (teacher, day, slot), vars_list in teacher_day_slot.items():
        add_upper_bound(vars_list, 1, 1000, f"teacher_{teacher}_{day}_{slot}", enforce_hard=True)

    for (student, day, slot), vars_list in student_day_slot.items():
        add_upper_bound(vars_list, 1, 1000, f"student_slot_{student}_{day}_{slot}")

    for (student, day, subject), vars_list in student_day_subject.items():
        add_upper_bound(vars_list, 1, 700, f"subject_{student}_{day}_{subject}")

    for (student, day), vars_list in student_day_total.items():
        add_upper_bound(vars_list, 3, 500, f"daily_load_{student}_{day}")

    for key, vars_list in day_slot_capacity.items():
        if vars_list:
            model.Add(sum(vars_list) <= 4)

    if seed:
        for (session_uid, day, slot), var in assignment.items():
            if session_uid in seed:
                target_day, target_slot = seed[session_uid]
                model.AddHint(var, 1 if (day, slot) == (target_day, target_slot) else 0)

    if relax:
        objective_terms = [weight * slack for slack, weight in penalties]
        model.Minimize(sum(objective_terms) if objective_terms else 0)

    return model, assignment


def _extract_entries(
    solver: cp_model.CpSolver,
    assignment: Dict[Tuple[str, str, int], cp_model.IntVar],
    data: TimetableData,
) -> List[Dict[str, object]]:
    session_lookup = {session.uid: session for session in data.sessions}
    entries: List[Dict[str, object]] = []
    for (session_uid, day, slot), var in assignment.items():
        if solver.Value(var):
            session = session_lookup[session_uid]
            entries.append(
                {
                    "uid": session_uid,
                    "day": day,
                    "slot": slot,
                    "teacher": session.teacher,
                    "code": session.code,
                    "subject": session.subject,
                    "students": list(session.students),
                }
            )

    entries.sort(key=lambda e: (data.day_order[e["day"]], e["slot"], e["teacher"], e["code"]))
    track_buckets: Dict[Tuple[str, int], List[Dict[str, object]]] = defaultdict(list)
    for entry in entries:
        track_buckets[(entry["day"], entry["slot"])].append(entry)

    for key, bucket in track_buckets.items():
        bucket.sort(key=lambda e: (e["teacher"], e["code"], e["uid"]))
        if len(bucket) > 4:
            raise ValueError(f"Slot capacity exceeded for {key}")
        for track_idx, entry in enumerate(bucket, start=1):
            entry["track"] = track_idx

    entries.sort(key=lambda e: (data.day_order[e["day"]], e["slot"], e["track"], e["teacher"], e["code"]))

    for entry in entries:
        entry.pop("uid", None)

    return entries


def _solve_once(
    data: TimetableData,
    relax: bool,
    time_limit: float,
    seed: Optional[Dict[str, Tuple[str, int]]] = None,
    force_seed: bool = False,
) -> SolveOutcome:
    model, assignment = _build_model(data, relax=relax, seed=seed)

    if seed and force_seed:
        for (session_uid, day, slot), var in assignment.items():
            if session_uid in seed:
                if (day, slot) == seed[session_uid]:
                    model.Add(var == 1)
                else:
                    model.Add(var == 0)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5.0 if force_seed else time_limit
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return SolveOutcome(entries=None, status=status)

    entries = _extract_entries(solver, assignment, data)
    return SolveOutcome(entries=entries, status=status)


def _run_with_fallback(data: TimetableData) -> Tuple[List[Dict[str, object]], str]:
    seed = build_greedy_seed(data)
    hard_outcome = None
    if seed:
        hard_outcome = _solve_once(
            data,
            relax=False,
            time_limit=HARD_SOLVER_TIME,
            seed=seed,
            force_seed=True,
        )
        if hard_outcome.entries is None:
            hard_outcome = _solve_once(
                data,
                relax=False,
                time_limit=HARD_SOLVER_TIME,
                seed=seed,
            )
    else:
        hard_outcome = _solve_once(
            data,
            relax=False,
            time_limit=HARD_SOLVER_TIME,
        )
    if hard_outcome.entries is not None:
        return hard_outcome.entries, "timetable.csv"

    soft_outcome = _solve_once(
        data,
        relax=True,
        time_limit=SOFT_SOLVER_TIME,
        seed=seed if seed else None,
    )
    if soft_outcome.entries is None:
        raise RuntimeError("Timetable infeasible even after relaxing soft constraints.")
    return soft_outcome.entries, "relaxed_timetable.csv"


def _build_payload(entries: List[Dict[str, object]], data: TimetableData) -> Dict[str, object]:
    return {
        "days": list(data.days),
        "slots": [1, 2, 3, 4, 5],
        "entries": [
            {
                "day": entry["day"],
                "slot": entry["slot"],
                "track": entry["track"],
                "teacher": entry["teacher"],
                "code": entry["code"],
                "subject": entry["subject"],
                "students": entry["students"],
            }
            for entry in entries
        ],
        "teachers": list(data.teachers),
        "students": list(data.students),
    }


def _write_outputs(payload: Dict[str, object], csv_filename: str) -> None:
    csv_path = HARD_CSV if csv_filename == HARD_CSV.name else SOFT_CSV
    rows: Sequence[Dict[str, object]] = payload["entries"]  # type: ignore[assignment]

    with open(csv_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["Day", "Slot", "Track", "Teacher", "Code", "Subject", "Students"])
        for row in rows:
            writer.writerow(
                [
                    row["day"],
                    row["slot"],
                    row["track"],
                    row["teacher"],
                    row["code"],
                    row["subject"],
                    ", ".join(row["students"]),
                ]
            )

    with open(JSON_PATH, "w", encoding="utf-8") as json_file:
        json.dump(payload, json_file, indent=2)

    stale_path = SOFT_CSV if csv_path == HARD_CSV else HARD_CSV
    if stale_path.exists():
        stale_path.unlink()


class TimetableHandler(BaseHTTPRequestHandler):
    server_version = "TimetableHTTP/1.0"

    def _ensure_payload(self) -> Dict[str, object]:
        if TIMETABLE_PAYLOAD is None:
            self.send_error(HTTPStatus.SERVICE_UNAVAILABLE, "Timetable not ready")
            raise RuntimeError("Timetable not ready")
        return TIMETABLE_PAYLOAD

    def _serve_bytes(self, content: bytes, content_type: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _serve_file(self, relative_path: str, content_type: str) -> None:
        target = UI_DIR / relative_path
        if not target.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return
        content = target.read_bytes()
        self._serve_bytes(content, content_type)

    def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler naming)
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ("/", "/index.html"):
            self._serve_file("index.html", "text/html; charset=utf-8")
        elif path == "/styles.css":
            self._serve_file("styles.css", "text/css; charset=utf-8")
        elif path == "/app.jsx":
            self._serve_file("app.jsx", "text/javascript; charset=utf-8")
        elif path == "/api/timetable":
            payload = self._ensure_payload()
            body = json.dumps(payload).encode("utf-8")
            self._serve_bytes(body, "application/json; charset=utf-8")
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003 - matches BaseHTTPRequestHandler
        # Trim noisy default logging.
        message = "%s - %s" % (self.address_string(), format % args)
        print(message)


def initialize_timetable() -> Tuple[Dict[str, object], str]:
    data = load_data()
    entries, csv_name = _run_with_fallback(data)
    payload = _build_payload(entries, data)
    _write_outputs(payload, csv_name)
    return payload, csv_name


def run_server() -> None:
    global TIMETABLE_PAYLOAD, TIMETABLE_SOURCE
    TIMETABLE_PAYLOAD, TIMETABLE_SOURCE = initialize_timetable()
    server = ThreadingHTTPServer(("127.0.0.1", 8000), TimetableHandler)

    def shutdown_handler(signum: int, _: Optional[object]) -> None:
        print(f"\nReceived signal {signum}. Shutting down.")
        server.shutdown()

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    source_file = TIMETABLE_SOURCE or HARD_CSV.name
    print(f"Server running at http://127.0.0.1:8000/  — Timetable source: {source_file}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
