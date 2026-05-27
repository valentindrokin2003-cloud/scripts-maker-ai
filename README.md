# B2B Script Agent

Генерирует заполненный Jupyter-ноутбук из Excel-брифа. Сервис читает бриф,
извлекает структурированные поля через DeepSeek, нормализует даты, подбирает
товарные слова по словарю, строит regex-паттерны и собирает итоговый `.ipynb`.

## Веб-интерфейс

Запустить локальный сервер:

```bash
python3 ui_server.py
```

Открыть в браузере: `http://127.0.0.1:8765`

Интерфейс принимает Excel-бриф (`.xlsx`), запускает тот же пайплайн что и CLI,
и позволяет скачать готовый `.ipynb`. Готовые файлы копируются в `output/ui/`,
временные загрузки хранятся в `.runtime/ui/` (в git не попадают).

Чтобы открыть доступ другим людям в той же сети:

```bash
python3 ui_server.py --host 0.0.0.0 --port 8765
```

Дополнительные настройки через переменные окружения:

```bash
MAX_UPLOAD_BYTES=26214400
```

## CLI

```bash
python3 agent.py --brief "data/ТЗ_Fresh.xlsx"
python3 agent.py --brief "data/ТЗ_Fresh.xlsx" --output "output"
python3 agent.py --brief "data/ТЗ_Fresh.xlsx" --skip-api-check
```

## Окружение

Обязательно:

```bash
DEEPSEEK_API_KEY=...
```

Опционально (переопределяют дефолты):

```bash
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
TEMPLATE_PATH=templates/b2b_template.ipynb
NOTEBOOK_BLOCKS_DIR=templates/notebook_blocks
DICT_PATH=data/words_ok_groups_v2.xlsx
OUTPUT_DIR=output
LOG_DIR=logs
```

Подробные логи CLI пишутся в `logs/agent_YYYYmmdd_HHMMSS.log`. Путь можно
задать через `--log-file path/to/run.log`. Флаг `--skip-api-check` пропускает
предварительную проверку API и сразу запускает пайплайн.

## Архитектура

Центральный оркестратор — `src/pipeline.py`, функция `run_pipeline(...)`.
Выполняет 7 шагов и возвращает `PipelineResult` с извлечёнными полями,
датами, подобранными словами, regex-паттернами и путём к готовому ноутбуку.
`agent.py` — тонкая CLI-обёртка поверх него.

### Шаги пайплайна

| # | Шаг | Описание |
|---|-----|----------|
| 1 | Чтение Excel | Бриф читается и текст извлекается |
| 2 | Извлечение полей | Клиент, ИНН, период, регионы, товарные слова — через DeepSeek |
| 3 | Проверка качества | Оценка полноты и ясности брифа |
| 4 | Нормализация периода | Даты приводятся к рабочему формату |
| 5 | Сопоставление со словарём | Товарные слова проверяются по словарю |
| 6 | Построение regex | Генерация выражений для отбора клиентов |
| 7 | Сборка notebook | Шаблон заполняется и сохраняется в `.ipynb` |

## Notebook-блоки

Код подстановки маркеров живёт в `templates/notebook_blocks/`. Каждый файл
соответствует одному маркеру `##AGENT:...##` в шаблоне `templates/b2b_template.ipynb`.
`src/notebook_replacements.py` рендерит блоки через `string.Template`, а
`src/notebook_filler.py` заменяет ячейки в ноутбуке.

Чтобы добавить или переименовать маркер:

1. Добавить или обновить маркер в `templates/b2b_template.ipynb`.
2. Добавить соответствующий блок-файл в `templates/notebook_blocks/`.
3. Обновить `MARKER_TEMPLATES` в `src/notebook_replacements.py`.
4. Запустить тесты.

## Тесты

```bash
venv/bin/python -m pytest -q
venv/bin/python test_smoke_integration.py
```

Смоук-тест создаёт минимальный Excel-файл и мокирует LLM-вызовы — не требует
реальных брифов и ключей API.
