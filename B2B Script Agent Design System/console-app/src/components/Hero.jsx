import Icon from "./Icon.jsx";

function KPI({ iconName, label, value, delta, tone }) {
  const cls = tone === "amber"  ? "kpi__icon kpi__icon--amber"
            : tone === "rose"   ? "kpi__icon kpi__icon--rose"
            : tone === "indigo" ? "kpi__icon kpi__icon--indigo"
            : "kpi__icon";
  return (
    <article className="kpi">
      <div className="spread">
        <span className={cls}><Icon name={iconName} /></span>
        <span className="kpi__delta">{delta}</span>
      </div>
      <div>
        <div className="kpi__label">{label}</div>
        <div className="kpi__value">{value}</div>
      </div>
    </article>
  );
}

export default function Hero({ counts, onUpload, eyebrow, title, sub }) {
  return (
    <section className="hero">
      <div className="hero-card">
        <div>
          <p className="hero-eyebrow">{eyebrow ?? "Добрый день, Валентин"}</p>
          <h1 className="hero-title">{title ?? "Соберите notebook из брифа за 7 шагов."}</h1>
          <p className="hero-sub">
            {sub ?? (
              <>Загрузите Excel-бриф — сервис проверит поля, нормализует период, подберёт regex и
              соберёт готовый <code>.ipynb</code> для вашего пайплайна.</>
            )}
          </p>
        </div>
        {onUpload && (
          <div className="hero-actions">
            <button className="hero-btn hero-btn--solid" onClick={onUpload}>
              <Icon name="upload" size={18} /> Загрузить бриф
            </button>
            <button className="hero-btn hero-btn--ghost">
              <Icon name="layers" size={18} /> Использовать шаблон
            </button>
          </div>
        )}
      </div>
      <div className="hero-stats">
        <KPI iconName="clock"   label="В очереди"      value={counts.queued    ?? 0} delta="+2 за час" tone="amber" />
        <KPI iconName="bolt"    label="В работе"       value={counts.running   ?? 0} delta="онлайн" />
        <KPI iconName="check"   label="Готово сегодня" value={counts.completed ?? 0} delta="+12%" />
        <KPI iconName="sparkle" label="Точность"       value="98.4%"                  delta="+0.6 пп" tone="indigo" />
      </div>
    </section>
  );
}
