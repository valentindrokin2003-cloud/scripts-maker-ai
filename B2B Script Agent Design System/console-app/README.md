# Script Agent — Console (React + Vite)

Современная сборка интерфейса B2B Script Agent на React + Vite. Подключается к
существующему Flask-бэкенду без изменений в API.

---

## Быстрый старт

```bash
cd console-app
npm install        # один раз, скачает зависимости (~80 МБ в node_modules/)
npm run dev        # запустит dev-сервер на http://localhost:5173
```

В соседней вкладке терминала запусти Flask как обычно:

```bash
python ui_server.py    # должен слушать localhost:8000
```

Vite-конфиг уже прокидывает все запросы `/api/*` с порта 5173 на 8000. То есть
фронт и бэк работают независимо, но fetch'ам это незаметно.

Если у тебя Flask на другом порту — поправь в `vite.config.js`:

```js
proxy: {
  "/api": { target: "http://localhost:8000", changeOrigin: true }
}
```

---

## Деплой на дев-стенд

```bash
npm run build      # соберёт всё в console-app/dist/
```

В `dist/` лежит один `index.html` + папка `assets/` с собранным JS/CSS — это
обычная статика. Скопируй содержимое `dist/` в твой Flask `web/`:

```bash
rm -rf /path/to/scripts-maker-ai/web
cp -r dist /path/to/scripts-maker-ai/web
```

Flask отдаст её точно так же, как сейчас отдаёт старый `web/`.

> **Tip:** для CI-сборки добавь в `package.json` твоего scripts-maker-ai
> репозитория скрипт типа `"build:frontend": "cd console-app && npm install && npm run build && rm -rf ../web && cp -r dist ../web"` — и одна команда полностью обновляет фронт.

---

## Структура

```
console-app/
├── package.json            ← зависимости (React, Vite)
├── vite.config.js          ← конфиг + dev-proxy
├── index.html              ← корневой HTML, Vite сам подставит сборку
└── src/
    ├── main.jsx            ← точка входа React
    ├── App.jsx             ← состояние, роутер, polling
    ├── api.js              ← клиент: fetchJobs, submitBriefs, cancelJob
    ├── data.js             ← константы (статусы, шаблоны, FAQ, сидовые данные)
    ├── styles.css          ← все стили
    ├── components/
    │   ├── Icon.jsx        ← SVG-иконки (Lucide-style)
    │   ├── Sidebar.jsx     ← левое меню
    │   ├── Topbar.jsx      ← верхняя полоса с поиском
    │   ├── Hero.jsx        ← зелёная карточка + 4 KPI
    │   ├── Bento.jsx       ← 4 быстрых действия
    │   ├── UploadSection.jsx
    │   ├── Queue.jsx
    │   ├── PipelineCard.jsx
    │   ├── Templates.jsx
    │   ├── Analytics.jsx
    │   ├── Updates.jsx
    │   ├── Help.jsx
    │   └── Footer.jsx
    └── pages/
        ├── HomePage.jsx
        ├── QueuePage.jsx
        ├── AnalyticsPage.jsx
        └── HelpPage.jsx
```

---

## Как читать код (для знакомства с React)

Начни с `App.jsx` — это «корневой» компонент. Он держит всё состояние
приложения (`useState`), запускает polling очереди (`useEffect`) и решает,
какую страницу показать.

Дальше посмотри один из page-компонентов, например `pages/QueuePage.jsx` —
видно, что страница это просто комбинация трёх блоков: `<UploadSection>`,
`<Queue>`, `<PipelineCard>`. Каждый блок — это маленький компонент в
`components/`, который принимает данные через **props** и рендерит JSX.

Полезные паттерны, которые ты увидишь в этом проекте:

- **`useState`** — переменные, которые автоматически перерисовывают UI:
  ```jsx
  const [files, setFiles] = useState([]);
  setFiles([...files, newFile]); // UI сразу обновится
  ```

- **`useEffect`** — побочные эффекты (запрос на сервер, подписка на события):
  ```jsx
  useEffect(() => {
    fetchJobs().then(setJobs);
  }, []);  // [] значит «один раз при монтировании»
  ```

- **Props** — данные сверху вниз:
  ```jsx
  <Queue jobs={jobs} onSelect={setSelectedId} />
  // внутри Queue:
  export default function Queue({ jobs, onSelect }) { ... }
  ```

- **Условный рендер**:
  ```jsx
  {page === "home" && <HomePage ... />}
  {files.length > 0 && <FileList files={files} />}
  ```

- **Рендер списка**:
  ```jsx
  {jobs.map((j) => <JobRow key={j.job_id} job={j} />)}
  ```

Когда захочешь добавить новую страницу:

1. Создай `src/pages/MyPage.jsx`
2. В `data.js` дополни `PAGE_META`
3. В `Sidebar.jsx` добавь пункт меню
4. В `App.jsx` добавь `{page === "mypage" && <MyPage ... />}`

---

## Что работает без бэкенда

Если Flask не запущен, `App.jsx` ловит ошибку и подменяет данные на
`SEED_JOBS` из `data.js`, чтобы можно было разрабатывать UI без бэка.
Сверху появляется жёлтая полоска с предупреждением.

---

## Что осталось замокать (хардкод сейчас в `data.js` или JSX)

- `CHART_DATA` / `CHART_AXIS` — данные графика в `<Analytics>`
- Donut-numbers в HTML — `Analytics.jsx`
- KPI-дельты (`+12%`, `98.4%`) — `Hero.jsx`
- `UPDATES`, `TEMPLATES`, `HELP_TOPICS`, `FAQ` — статичные массивы

Когда будут эндпоинты — перенеси их fetch в `api.js` и обнови соответствующие
компоненты через `useEffect`.

---

## Полезные команды

```bash
npm run dev        # дев-сервер + горячая перезагрузка
npm run build      # продакшен-сборка → dist/
npm run preview    # локальный просмотр собранного dist/
```
