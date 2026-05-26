import Icon from "./Icon.jsx";

export default function Sidebar({ page, onNav, counts }) {
  const items = [
    { key: "home",      label: "Главная",   icon: "grid" },
    { key: "queue",     label: "Очередь",   icon: "layers", badge: counts.queued + counts.running, badgeGreen: true },
    { key: "analytics", label: "Аналитика", icon: "chart" },
    { key: "help",      label: "Помощь",    icon: "book" },
  ];
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand__logo"><Icon name="bolt" size={22} /></div>
        <div className="brand__text-block">
          <div className="brand__name">Script Agent</div>
          <div className="brand__name-sub">Notebook builder</div>
        </div>
      </div>

      <div className="sidebar__heading">Меню</div>
      <div className="sidebar__group">
        {items.map((it) => (
          <button
            key={it.key}
            className="sidebar__item"
            aria-current={page === it.key ? "page" : undefined}
            onClick={() => onNav(it.key)}
          >
            <Icon name={it.icon} />
            <span>{it.label}</span>
            {it.badge ? (
              <span className={"sidebar__badge" + (it.badgeGreen ? " sidebar__badge--green" : "")}>
                {it.badge}
              </span>
            ) : null}
          </button>
        ))}
      </div>

      <div className="sidebar__heading">Быстрый доступ</div>
      <div className="sidebar__group">
        <button className="sidebar__item" onClick={() => onNav("queue")}>
          <Icon name="history" /><span>История</span>
        </button>
        <button className="sidebar__item" onClick={() => onNav("queue")}>
          <Icon name="bookmark" /><span>Сохранённые</span>
        </button>
      </div>

      <div className="sidebar__spacer"></div>

      <div className="sidebar__user">
        <div className="nav__avatar">ВД</div>
        <div className="sidebar__user-info">
          <div className="sidebar__user-name">Валентин Д.</div>
          <div className="sidebar__user-org">Fresh Group</div>
        </div>
        <button className="sidebar__settings" aria-label="Настройки">
          <Icon name="settings" size={18} />
        </button>
      </div>
    </aside>
  );
}
