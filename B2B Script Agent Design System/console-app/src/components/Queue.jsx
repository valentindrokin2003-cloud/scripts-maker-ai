import Icon from "./Icon.jsx";
import { STATUS_LABEL, STATUS_PRIORITY, PIPELINE_DEFS, formatUpdated } from "../data.js";

function JobRow({ job, selected, onSelect }) {
  const step = job.current_step ?? 0;
  return (
    <article
      className="job"
      data-selected={selected ? "true" : undefined}
      style={{ cursor: "pointer" }}
      onClick={() => onSelect(job.job_id)}
    >
      <div className="job__avatar"><Icon name="excel" /></div>
      <div>
        <div className="job__name">{job.filename}</div>
        <div className="job__sub">
          Шаг {String(step).padStart(2, "0")} из 07 · {job.message || PIPELINE_DEFS[Math.max(0, step - 1)]?.[0] || "Обновление"}
        </div>
      </div>
      <div className="job__right">
        <span className="status-pill" data-status={job.status}>{STATUS_LABEL[job.status] || job.status}</span>
        <span className="job__time">{formatUpdated(job.updated_at)}</span>
      </div>
    </article>
  );
}

export default function Queue({ jobs, filter, onFilter, selectedId, onSelect, title = "Очередь", subtitle }) {
  const tabs = [
    ["all",            "Все"],
    ["running",        "В работе"],
    ["queued",         "В очереди"],
    ["needs_revision", "Доработка"],
    ["completed",      "Готово"],
    ["failed",         "Ошибка"],
  ];

  const counts = { all: jobs.length };
  for (const k of Object.keys(STATUS_LABEL)) counts[k] = 0;
  jobs.forEach((j) => { counts[j.status] = (counts[j.status] || 0) + 1; });

  const sorted = jobs.slice().sort((a, b) => {
    const d = (STATUS_PRIORITY[a.status] ?? 99) - (STATUS_PRIORITY[b.status] ?? 99);
    if (d) return d;
    if (a.status === "queued" && b.status === "queued") {
      return (a.queue_position || 9999) - (b.queue_position || 9999);
    }
    return (b.updated_at || 0) - (a.updated_at || 0);
  });
  const list = filter === "all" ? sorted : sorted.filter((j) => j.status === filter);

  return (
    <section className="card">
      <div className="spread" style={{ marginBottom: 14 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 22, fontWeight: 800, color: "var(--ink)", letterSpacing: "-0.02em" }}>{title}</h2>
          {subtitle && <p style={{ margin: "4px 0 0", fontSize: 14, color: "var(--ink-faint)" }}>{subtitle}</p>}
        </div>
      </div>

      <div className="tabs">
        {tabs.map(([k, lbl]) => (
          <button key={k} className="tab" aria-selected={filter === k} onClick={() => onFilter(k)}>
            {lbl} <span className="count">{counts[k] ?? 0}</span>
          </button>
        ))}
      </div>

      <div className="job-list">
        {list.length === 0 ? (
          <div style={{ padding: 22, textAlign: "center", background: "var(--surface-grey)", borderRadius: "var(--r-md)" }}>
            <strong style={{ display: "block", color: "var(--ink)", fontSize: 15 }}>Очередь пуста</strong>
            <span style={{ fontSize: 13, color: "var(--ink-faint)" }}>
              Загрузите бриф — он появится здесь с прогрессом.
            </span>
          </div>
        ) : list.map((j) => (
          <JobRow key={j.job_id} job={j} selected={selectedId === j.job_id} onSelect={onSelect} />
        ))}
      </div>
    </section>
  );
}
