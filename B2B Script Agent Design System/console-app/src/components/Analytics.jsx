import Icon from "./Icon.jsx";
import { CHART_DATA, CHART_AXIS } from "../data.js";

export default function Analytics() {
  const max = Math.max(...CHART_DATA);
  return (
    <section className="section">
      <div className="section-head">
        <div>
          <h2>Аналитика</h2>
          <p>Сколько брифов сделано, где чаще нужна доработка, какая средняя точность.</p>
        </div>
        <a className="section-link" href="#">Подробнее <Icon name="arrow" size={16} /></a>
      </div>
      <div className="analytics">
        <div className="chart-card">
          <div className="chart-head">
            <h3>Сборка notebook за месяц</h3>
            <div className="chart-range">
              <button>7 дней</button>
              <button aria-selected="true">28 дней</button>
              <button>3 мес.</button>
            </div>
          </div>
          <div className="chart-summary">
            <span className="chart-summary__val">412</span>
            <span className="chart-summary__delta">
              <Icon name="trending" size={14} /> +24% к прошлому периоду
            </span>
            <span className="chart-summary__sub">· 98.4% успешных</span>
          </div>
          <div className="chart">
            {CHART_DATA.map((v, i) => (
              <div
                key={i}
                className={"chart__bar" + (i === CHART_DATA.length - 1 ? "" : " chart__bar--soft")}
                style={{ height: (v / max) * 100 + "%" }}
              />
            ))}
          </div>
          <div className="chart-axis">
            {CHART_AXIS.map((d) => <span key={d}>{d}</span>)}
          </div>
        </div>

        <div className="donut-card">
          <div>
            <h3>Распределение по статусам</h3>
            <p className="sub">За последние 28 дней · 412 брифов</p>
          </div>
          <div className="donut-wrap">
            <div className="donut">
              <div className="donut__center">
                <strong>61%</strong>
                <small>готово</small>
              </div>
            </div>
            <div className="legend">
              <Legend dot="#21A038" name="Готово" val="251" />
              <Legend dot="#F2A93B" name="Доработка" val="68" />
              <Legend dot="#E0584D" name="Ошибка" val="42" />
              <Legend dot="rgba(255,255,255,0.18)" name="Отменено" val="51" />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Legend({ dot, name, val }) {
  return (
    <div className="legend__item">
      <span>
        <span className="legend__dot" style={{ background: dot }}></span>
        <span className="legend__name">{name}</span>
      </span>
      <span className="legend__val">{val}</span>
    </div>
  );
}
