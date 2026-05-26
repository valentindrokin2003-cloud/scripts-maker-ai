import Icon from "./Icon.jsx";
import { TEMPLATES } from "../data.js";

export default function Templates() {
  return (
    <section className="section">
      <div className="section-head">
        <div>
          <h2>Шаблоны брифов</h2>
          <p>Готовые форматы — стартуйте быстрее, чем с пустого Excel.</p>
        </div>
        <a className="section-link" href="#">Все шаблоны <Icon name="arrow" size={16} /></a>
      </div>
      <div className="templates">
        {TEMPLATES.map((t) => (
          <article key={t.name} className="tmpl">
            <div className="tmpl__head">
              <div className={"tmpl__emblem tmpl__emblem--" + t.tone}>{t.initials}</div>
              <div>
                <div className="tmpl__name">{t.name}</div>
                <div className="tmpl__role">{t.role}</div>
              </div>
            </div>
            <p className="tmpl__desc">{t.desc}</p>
            <div className="tmpl__foot">
              <span className="tmpl__count">{t.count}</span>
              <button className="tmpl__btn">
                <Icon name="plus" size={14} /> Использовать
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
