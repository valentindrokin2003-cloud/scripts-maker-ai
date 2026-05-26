import Icon from "./Icon.jsx";
import { UPDATES } from "../data.js";

export default function Updates() {
  return (
    <section className="section">
      <div className="section-head">
        <div>
          <h2>Новости и советы</h2>
          <p>Обновления модели, новые шаблоны, рекомендации по подготовке брифа.</p>
        </div>
        <a className="section-link" href="#">Все новости <Icon name="arrow" size={16} /></a>
      </div>
      <div className="updates">
        {UPDATES.map((u) => (
          <article key={u.title} className="update">
            <span className={"update__tag update__tag--" + u.tone}>{u.tag}</span>
            <div className="update__title">{u.title}</div>
            <div className="update__body">{u.body}</div>
            <div className="update__foot">
              <span>{u.date}</span>
              <span>{u.time} чтения</span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
