# Repository Guidelines

## Project Structure & Module Organization
- `server.py` launches the timetable solver and HTTP server. All solver code lives in `solver_with_ui/`.
- `solver_with_ui/data_model.py` stores static datasets (teachers, sessions, availability). Treat it as the single source of truth when tweaking inputs.
- `solver_with_ui/server.py` builds the CP-SAT model, writes `timetable.json`/`timetable.csv` (or `relaxed_timetable.csv`), and serves the UI and API.
- The React micro-app resides in `solver_with_ui/ui/` (`index.html`, `styles.css`, `app.jsx`) and is served as static assets—no build step required.

## Build, Test, and Development Commands
- `python server.py` – solve the timetable (hard model first, soft fallback if needed) and start the local server at `http://127.0.0.1:8000/`.
- `python -m solver_with_ui.server` – equivalent module entry-point, useful when running from other tooling.
- `curl http://127.0.0.1:8000/api/timetable` – retrieve the latest JSON payload for quick sanity checks or integration tests.

## Coding Style & Naming Conventions
- Python: follow PEP 8 with 4-space indents; keep modules typed (`from __future__ import annotations`) and prefer dataclasses for structured data.
- Solver variables are snake_case; CP-SAT helper functions use verb-first names (e.g., `build_greedy_seed`).
- Front-end JSX is organized into small React components, with PascalCase where new components are introduced; keep CSS scoped via class names defined in `styles.css`.

## Testing Guidelines
- The solver enforces hard constraints within CP-SAT; inspect the console output for `Server running ... Timetable source: ...` to confirm whether the hard or soft schedule was selected.
- Validate endpoints manually: load `/` in a browser to confirm the grid renders, use the dropdown filters, and hit `/api/timetable` to ensure JSON contains the expected keys (`days`, `slots`, `entries`, `teachers`, `students`).
- After editing datasets, re-run `python server.py` and verify the regenerated CSV/JSON files before shipping changes.

## Commit & Pull Request Guidelines
- Use concise, imperative commit messages (e.g., “Add soft fallback for infeasible solver run”) and group related solver/UI changes together.
- Pull requests should mention the impacted modules, note whether the hard timetable remains feasible, and include screenshots or JSON excerpts when UI or data changes alter the timetable.
- Reference any tracked issues or task IDs, and describe manual validation steps taken (solver run, endpoint checks, UI verification).
