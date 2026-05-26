import { useState } from "react";
import Icon from "./Icon.jsx";
import { HELP_TOPICS, FAQ } from "../data.js";

export default function Help() {
  const [openIdx, setOpenIdx] = useState(0);

  return (
    <div>
      <section className="help-hero">
        <h2>Помощь и документация</h2>
        <p>Соберите ответ за минуту: формат брифа, шаблоны, частые проблемы, контакты команды.</p>
        <div className="help-hero__search">
          <Icon name="search" size={18} />
          <input placeholder="Что нужно сделать?" />
          <button>Спросить</button>
        </div>
      </section>

      <div className="section">
        <div className="section-head">
          <div>
            <h2>Темы помощи</h2>
            <p>6 разделов покрывают 95% вопросов команды.</p>
          </div>
          <a className="section-link" href="#">Все статьи <Icon name="arrow" size={16} /></a>
        </div>
        <div className="help-topics">
          {HELP_TOPICS.map((t) => (
            <button key={t.title} className="help-topic" type="button">
              <div className="help-topic__icon"><Icon name={t.icon} size={22} /></div>
              <div>
                <h3>{t.title}</h3>
                <p>{t.desc}</p>
              </div>
              <ul>
                {t.items.map((it) => (
                  <li key={it}>
                    <span>{it}</span>
                    <Icon name="arrow" size={14} />
                  </li>
                ))}
              </ul>
            </button>
          ))}
        </div>
      </div>

      <div className="section help-split">
        <section className="faq">
          <h2>Частые вопросы</h2>
          {FAQ.map((item, i) => (
            <article
              key={i}
              className="faq__item"
              data-open={openIdx === i ? "true" : undefined}
              onClick={() => setOpenIdx(openIdx === i ? -1 : i)}
            >
              <div className="faq__q">
                <span>{item.q}</span>
                <Icon name="plus" />
              </div>
              <div className="faq__a">{item.a}</div>
            </article>
          ))}
        </section>

        <aside className="contact-card">
          <h3>Связаться с командой</h3>
          <p>Если ответа нет в документации — мы рядом. Среднее время ответа ~ 12 минут в рабочее время.</p>
          <div className="contact-row">
            <div className="contact-row__icon"><Icon name="bell" size={18} /></div>
            <div>
              <strong>Telegram-чат</strong>
              <small>@b2b_script_agent · 24 человека онлайн</small>
            </div>
          </div>
          <div className="contact-row">
            <div className="contact-row__icon"><Icon name="file" size={18} /></div>
            <div>
              <strong>Сообщить о баге</strong>
              <small>Прикрепите бриф и шаг, на котором упало</small>
            </div>
          </div>
          <div className="contact-row">
            <div className="contact-row__icon"><Icon name="book" size={18} /></div>
            <div>
              <strong>Документация в Notion</strong>
              <small>Архитектура, эндпоинты, словари</small>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
