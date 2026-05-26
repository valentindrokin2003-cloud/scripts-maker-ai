import Hero from "../components/Hero.jsx";
import Analytics from "../components/Analytics.jsx";

export default function AnalyticsPage({ counts, onNav }) {
  return (
    <div>
      <Hero
        counts={counts}
        eyebrow="Аналитика"
        title="Сколько брифов, где чаще доработка, какая точность."
        sub="Все метрики за последние 28 дней. Данные обновляются раз в час."
      />
      <Analytics />
      <div className="section">
        <div className="section-head">
          <div>
            <h2>Где чаще нужна доработка</h2>
            <p>Самые частые причины отбраковки брифа за 28 дней.</p>
          </div>
        </div>
        <div className="templates">
          <Breakdown pct="38%" tone="amber"  name="Период без года"   role="Шаг 04 — Нормализация периода" desc="Формат «01.01 — 31.03» не уточняет год. Решается префиксом YYYY." />
          <Breakdown pct="29%" tone="rose"   name="Товары вне словаря" role="Шаг 05 — Сопоставление"        desc="Несоответствие с FMCG-словарём. Часто помогает расширение словаря бренда." />
          <Breakdown pct="17%" tone="indigo" name="Регион не распознан" role="Шаг 02 — Извлечение полей"     desc="Сокращения МО/СПб иногда дают неоднозначность. Уточняйте полным названием." />
        </div>
      </div>
    </div>
  );
}

function Breakdown({ pct, tone, name, role, desc }) {
  return (
    <article className="tmpl">
      <div className="tmpl__head">
        <div className={"tmpl__emblem tmpl__emblem--" + tone}>{pct}</div>
        <div>
          <div className="tmpl__name">{name}</div>
          <div className="tmpl__role">{role}</div>
        </div>
      </div>
      <p className="tmpl__desc">{desc}</p>
    </article>
  );
}
