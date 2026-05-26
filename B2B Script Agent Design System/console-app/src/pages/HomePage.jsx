import Hero from "../components/Hero.jsx";
import Bento from "../components/Bento.jsx";
import Updates from "../components/Updates.jsx";
import Icon from "../components/Icon.jsx";
import { STATUS_LABEL, PIPELINE_DEFS, formatUpdated } from "../data.js";

export default function HomePage({ counts, jobs, onSelect, onNav }) {
  return (
    <div>
      <Hero counts={counts} onUpload={() => onNav("queue")} />

      <div className="section">
        <Bento onUpload={() => onNav("queue")} onAnalytics={() => onNav("analytics")} />
      </div>

      <div className="section">
        <div className="section-head">
          <div>
            <h2>Последние брифы</h2>
            <p>Свежие задачи из очереди — статусы и прогресс.</p>
          </div>
          <button className="section-link" onClick={() => onNav("queue")}>
            Открыть очередь <Icon name="arrow" size={16} />
          </button>
        </div>
        <div className="job-list">
          {jobs.slice(0, 4).map((j) => {
            const step = j.current_step ?? 0;
            return (
              <article
                key={j.job_id}
                className="job"
                style={{ cursor: "pointer" }}
                onClick={() => { onSelect(j.job_id); onNav("queue"); }}
              >
                <div className="job__avatar"><Icon name="excel" /></div>
                <div>
                  <div className="job__name">{j.filename}</div>
                  <div className="job__sub">
                    Шаг {String(step).padStart(2, "0")} из 07 · {j.message || PIPELINE_DEFS[Math.max(0, step - 1)]?.[0]}
                  </div>
                </div>
                <div className="job__right">
                  <span className="status-pill" data-status={j.status}>{STATUS_LABEL[j.status]}</span>
                  <span className="job__time">{formatUpdated(j.updated_at)}</span>
                </div>
              </article>
            );
          })}
        </div>
      </div>

      <Updates />
    </div>
  );
}
