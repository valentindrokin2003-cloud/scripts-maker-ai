import Icon from "./Icon.jsx";

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer__brand">
        <div className="brand">
          <div className="brand__logo"><Icon name="bolt" size={22} /></div>
          <div>
            <div className="brand__name">Script Agent</div>
            <div className="brand__name-sub">Notebook builder · B2B</div>
          </div>
        </div>
        <p>Внутренний сервис генерации <code>.ipynb</code> из Excel-брифов. Очередь, шаблоны и аналитика на одном экране.</p>
      </div>
      <div>
        <h4>Продукт</h4>
        <ul>
          <li><a href="#">Очередь</a></li>
          <li><a href="#">Шаблоны брифов</a></li>
          <li><a href="#">Аналитика</a></li>
          <li><a href="#">История</a></li>
        </ul>
      </div>
      <div>
        <h4>Документация</h4>
        <ul>
          <li><a href="#">Формат брифа</a></li>
          <li><a href="#">Словарь товаров</a></li>
          <li><a href="#">CLI и API</a></li>
          <li><a href="#">Журнал изменений</a></li>
        </ul>
      </div>
      <div>
        <h4>Команда</h4>
        <ul>
          <li><a href="#">Помощь</a></li>
          <li><a href="#">Telegram-канал</a></li>
          <li><a href="#">Сообщить об ошибке</a></li>
          <li><a href="#">Безопасность</a></li>
        </ul>
      </div>
    </footer>
  );
}
