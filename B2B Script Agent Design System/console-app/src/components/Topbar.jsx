import Icon from "./Icon.jsx";

export default function Topbar({ title, subtitle }) {
  return (
    <header className="topbar">
      <div className="topbar__crumbs">
        <h1>{title}</h1>
        {subtitle && <span>· {subtitle}</span>}
      </div>
      <div className="topbar__spacer"></div>
      <label className="topbar__search">
        <Icon name="search" size={16} />
        <input placeholder="Поиск по брифам, шаблонам, статусам" />
      </label>
      <button className="nav__icon-btn" aria-label="Уведомления">
        <Icon name="bell" />
        <span className="dot"></span>
      </button>
    </header>
  );
}
