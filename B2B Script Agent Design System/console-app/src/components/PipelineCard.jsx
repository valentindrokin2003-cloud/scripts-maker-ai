import { useState } from "react";
import Icon from "./Icon.jsx";
import { cancelJob } from "../api.js";
import { PIPELINE_DEFS } from "../data.js";

function stepStatus(job, idx, step) {
  if (job?.steps?.[idx - 1]?.status) return job.steps[idx - 1].status;
  if (!job) return "pending";
  if (job.status === "failed"          && idx === step) return "error";
  if (job.status === "needs_revision"  && idx === step) return "review";
  if (idx < step) return "done";
  if (idx === step && (job.status === "running" || job.status === "queued")) return "active";
  return "pending";
}

export default function PipelineCard({ job }) {
  const step = job ? (job.current_step ?? 0) : 0;
  const pct = job?.progress != null ? job.progress : Math.round((step / 7) * 100);
  const [cancelling, setCancelling] = useState(false);

  const handleCancel = async () => {
    if (!job || cancelling) return;
    setCancelling(true);
    try { await cancelJob(job.job_id); } catch {}
    finally { setCancelling(false); }
  };

  return (
    <section className="pipeline-card">
      <h2 style={{ margin: "0 0 16px", fontSize: 22, fontWeight: 800, color: "var(--ink)", letterSpacing: "-0.02em" }}>
        Прогресс
      </h2>

      <div className="pipeline-summary">
        <div>
          <div className="pipeline-summary__progress">{job ? job.filename : "Нет активной задачи"}</div>
          <div className="pipeline-summary__step">
            {job
              ? `Шаг ${String(step).padStart(2, "0")} из 07 — ${PIPELINE_DEFS[Math.max(0, step - 1)]?.[0] ?? "запуск"}`
              : "Выберите задачу из очереди"}
          </div>
          <div className="pipeline-bar">
            <div className="pipeline-bar__fill" style={{ width: `${pct}%` }}></div>
          </div>
        </div>
        <div className="pipeline-summary__pct">{pct}%</div>
      </div>

      <div className="pipeline-list">
        {PIPELINE_DEFS.map(([title, detail], i) => {
          const idx = i + 1;
          const st = stepStatus(job, idx, step);
          return (
            <div key={idx} className="step" data-status={st === "pending" ? undefined : st}>
              <div className="step__num">
                {st === "done" ? <Icon name="check" size={16} /> : String(idx).padStart(2, "0")}
              </div>
              <div>
                <div className="step__title">{title}</div>
                <div className="step__detail">{(job?.steps?.[i] && job.steps[i].detail) || detail}</div>
              </div>
              <div className="step__icon">
                {st === "active" && <Icon name="play" size={18} />}
                {st === "review" && <Icon name="sparkle" size={18} />}
                {st === "error"  && <Icon name="x" size={18} />}
              </div>
            </div>
          );
        })}
      </div>

      {job && (job.download_url || job.cancellable) && (
        <div style={{ marginTop: 16, display: "flex", gap: 10 }}>
          {job.download_url && (
            <a
              href={job.download_url}
              download
              style={{
                flex: 1,
                height: 44,
                display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8,
                borderRadius: "var(--r-pill)",
                background: "var(--sb-green)",
                color: "#fff",
                fontSize: 14, fontWeight: 700,
                textDecoration: "none",
              }}
            >
              <Icon name="download" size={16} /> Скачать notebook
            </a>
          )}
          {job.cancellable && (
            <button
              onClick={handleCancel}
              disabled={cancelling}
              style={{
                flex: job.download_url ? "0 0 auto" : 1,
                height: 44,
                padding: "0 18px",
                borderRadius: "var(--r-pill)",
                background: "var(--rose-soft)",
                color: "var(--rose)",
                border: "1px solid var(--rose-soft)",
                fontSize: 14, fontWeight: 700,
                cursor: cancelling ? "not-allowed" : "pointer",
                display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8,
              }}
            >
              <Icon name="x" size={16} /> {cancelling ? "Отмена…" : "Отменить"}
            </button>
          )}
        </div>
      )}
    </section>
  );
}
