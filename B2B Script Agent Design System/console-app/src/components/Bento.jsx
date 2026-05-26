import Icon from "./Icon.jsx";

export default function Bento({ onUpload, onAnalytics }) {
  const items = [
    { icon: "upload",  title: "Загрузить .xlsx",     sub: "До 10 брифов за один заход. Последовательная обработка.",        hint: "Перейти",  onClick: onUpload, green: true },
    { icon: "layers",  title: "Из шаблона",          sub: "8 готовых форматов брифа — от ритейла до e-commerce.",            hint: "Открыть",  onClick: onUpload },
    { icon: "history", title: "Последние брифы",     sub: "Повторно соберите notebook из уже обработанного брифа.",          hint: "Открыть",  onClick: onUpload },
    { icon: "chart",   title: "Аналитика",            sub: "Сколько брифов сделано за неделю, где чаще нужна доработка.",     hint: "Смотреть", onClick: onAnalytics },
  ];
  return (
    <div className="bento">
      {items.map((it) => (
        <button
          key={it.title}
          className={"bento-card" + (it.green ? " bento-card--green" : "")}
          onClick={it.onClick}
        >
          <div className="bento-card__icon"><Icon name={it.icon} size={22} /></div>
          <div>
            <div className="bento-card__title">{it.title}</div>
            <div className="bento-card__sub">{it.sub}</div>
            <div className="bento-card__hint">{it.hint} <Icon name="arrow" size={14} /></div>
          </div>
        </button>
      ))}
    </div>
  );
}
