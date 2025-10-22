const { useEffect, useMemo, useState } = React;

const SLOT_TIMES = {
  1: "08:50",
  2: "09:25",
  3: "10:00",
  4: "10:45",
  5: "11:20",
};

const TEACHER_STYLES = {
  Sanya: {
    bg: "linear-gradient(135deg, rgba(59,130,246,0.35), rgba(59,130,246,0.15))",
    border: "rgba(59,130,246,0.6)",
    shadow: "0 10px 25px rgba(59,130,246,0.28)",
  },
  Usha: {
    bg: "linear-gradient(135deg, rgba(244,114,182,0.35), rgba(244,114,182,0.18))",
    border: "rgba(244,114,182,0.6)",
    shadow: "0 10px 25px rgba(244,114,182,0.28)",
  },
  Guru: {
    bg: "linear-gradient(135deg, rgba(34,211,238,0.35), rgba(34,211,238,0.15))",
    border: "rgba(34,211,238,0.55)",
    shadow: "0 10px 25px rgba(34,211,238,0.28)",
  },
  Gayatri: {
    bg: "linear-gradient(135deg, rgba(129,140,248,0.32), rgba(129,140,248,0.18))",
    border: "rgba(129,140,248,0.6)",
    shadow: "0 10px 25px rgba(129,140,248,0.26)",
  },
  Zeba: {
    bg: "linear-gradient(135deg, rgba(251,191,36,0.35), rgba(251,191,36,0.15))",
    border: "rgba(251,191,36,0.55)",
    shadow: "0 10px 25px rgba(251,191,36,0.26)",
  },
  Shravani: {
    bg: "linear-gradient(135deg, rgba(52,211,153,0.35), rgba(52,211,153,0.18))",
    border: "rgba(52,211,153,0.55)",
    shadow: "0 10px 25px rgba(52,211,153,0.26)",
  },
  default: {
    bg: "linear-gradient(135deg, rgba(148,163,184,0.28), rgba(148,163,184,0.12))",
    border: "rgba(148,163,184,0.5)",
    shadow: "0 10px 24px rgba(148,163,184,0.22)",
  },
};

function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [teacherFilter, setTeacherFilter] = useState("All");
  const [studentFilter, setStudentFilter] = useState("All");

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);
    fetch("/api/timetable")
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`);
        }
        return response.json();
      })
      .then((payload) => {
        if (!isMounted) return;
        setData(payload);
        setLoading(false);
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err.message || "Unable to load timetable.");
        setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const filteredEntries = useMemo(() => {
    if (!data) return [];
    return data.entries.filter((entry) => {
      if (teacherFilter !== "All" && entry.teacher !== teacherFilter) {
        return false;
      }
      if (studentFilter !== "All" && !entry.students.includes(studentFilter)) {
        return false;
      }
      return true;
    });
  }, [data, teacherFilter, studentFilter]);

  const gridData = useMemo(() => {
    if (!data) return {};
    const base = {};
    data.days.forEach((day) => {
      base[day] = {};
      data.slots.forEach((slot) => {
        base[day][slot] = [];
      });
    });
    filteredEntries.forEach((entry) => {
      if (!base[entry.day]) {
        base[entry.day] = {};
        data.slots.forEach((slot) => {
          base[entry.day][slot] = [];
        });
      }
      if (!base[entry.day][entry.slot]) {
        base[entry.day][entry.slot] = [];
      }
      base[entry.day][entry.slot].push(entry);
    });
    Object.values(base).forEach((slotMap) => {
      Object.values(slotMap).forEach((sessions) => {
        sessions.sort((a, b) => {
          if (a.track !== b.track) return a.track - b.track;
          return a.code.localeCompare(b.code);
        });
      });
    });
    return base;
  }, [data, filteredEntries]);

  const teacherOptions = useMemo(() => {
    if (!data) return ["All"];
    return ["All", ...data.teachers];
  }, [data]);

  const studentOptions = useMemo(() => {
    if (!data) return ["All"];
    return ["All", ...data.students];
  }, [data]);

  const clearFilters = () => {
    setTeacherFilter("All");
    setStudentFilter("All");
  };

  const totalSessions = data ? data.entries.length : 0;
  const filteredCount = filteredEntries.length;
  const filtersActive = teacherFilter !== "All" || studentFilter !== "All";

  if (loading) {
    return (
      <div className="app">
        <header className="hero">
          <span className="badge">Scheduler</span>
          <h1>Weekly Timetable</h1>
          <p>Preparing the latest schedule…</p>
        </header>
      </div>
    );
  }

  if (error) {
    return (
      <div className="app">
      <header className="hero">
        <span className="badge">Scheduler</span>
        <h1>Weekly Timetable</h1>
      </header>
      <p className="error">{error}</p>
    </div>
  );
  }

  if (!data) {
    return null;
  }

  return (
    <div className="app">
      <header className="hero">
        <span className="badge">Codex Scheduler</span>
        <h1>Weekly Timetable</h1>
        <p>
          Explore the full week at a glance. Use filters to spotlight a teacher’s load
          or follow a specific student through their sessions.
        </p>
        <div className="hero-metrics">
          <div className="metric-card">
            <span>Total sessions</span>
            <strong>{totalSessions}</strong>
          </div>
          <div className="metric-card">
            <span>Teachers scheduled</span>
            <strong>{data.teachers.length}</strong>
          </div>
          <div className="metric-card">
            <span>Students covered</span>
            <strong>{data.students.length}</strong>
          </div>
          <div className="metric-card">
            <span>{filtersActive ? "Sessions after filters" : "Visible sessions"}</span>
            <strong>{filtersActive ? filteredCount : totalSessions}</strong>
          </div>
        </div>
      </header>
      <section className="control-card">
        <label>
          Teacher
          <select value={teacherFilter} onChange={(event) => setTeacherFilter(event.target.value)}>
            {teacherOptions.map((option) => (
              <option value={option} key={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
        <label>
          Student
          <select value={studentFilter} onChange={(event) => setStudentFilter(event.target.value)}>
            {studentOptions.map((option) => (
              <option value={option} key={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
        <button type="button" onClick={clearFilters}>
          Clear filters
        </button>
      </section>
      <section className="grid-wrapper">
        <div className="grid">
          <div className="grid-header">Slot</div>
          {data.days.map((day) => (
            <div className="grid-header" key={`head-${day}`}>
              {day}
            </div>
          ))}
          {data.slots.map((slot) => (
            <React.Fragment key={`row-${slot}`}>
              <div className="slot-label">
                <span className="slot-title">Slot {slot}</span>
                <span className="slot-time">{SLOT_TIMES[slot]}</span>
              </div>
              {data.days.map((day) => {
                const sessions = (gridData[day] && gridData[day][slot]) || [];
                return (
                  <div className="cell" key={`${day}-${slot}`}>
                    {sessions.length > 0 && (
                      <div className="session-list">
                        {sessions.map((session) => {
                          const palette = TEACHER_STYLES[session.teacher] || TEACHER_STYLES.default;
                          return (
                            <div
                              className="session-card"
                              key={`${session.day}-${session.slot}-${session.track}-${session.code}`}
                              style={{
                                "--session-bg": palette.bg,
                                "--session-border": palette.border,
                                "--session-shadow": palette.shadow,
                              }}
                            >
                              <div className="session-header">
                                <span className="session-teacher">{session.teacher}</span>
                                <span className="session-code">{session.code}</span>
                              </div>
                              <div className="session-subject">{session.subject}</div>
                              <div className="student-count">{session.students.length} learners</div>
                              <div className="student-list">{session.students.join(", ")}</div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </React.Fragment>
          ))}
        </div>
      </section>
      <footer className="legend">
        Legend: Colors distinguish teachers. Slot timings — 1: 08:50, 2: 09:25,
        3: 10:00, 4: 10:45, 5: 11:20. Friday remains focused on slots 4–5.
        Filters stack, narrowing the view to matching sessions.
      </footer>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
