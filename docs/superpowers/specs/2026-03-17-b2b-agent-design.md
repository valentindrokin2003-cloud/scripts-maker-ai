# B2B Script Agent — Design Spec
**Date:** 2026-03-17

## Overview

CLI-агент, который читает Excel-бриф (ТЗ) по подбору B2B-контрагентов и автоматически заполняет шаблон Jupyter-ноутбука (`b2b_template.ipynb`), подставляя все параметры из брифа.

**Запуск:**
```bash
python agent.py --brief "data/ТЗ_Fresh.xlsx"
# → output/OOO_Fresh_script.ipynb
```

---

## Архитектура

### Файловая структура

```
scripts-maker-ai/
├── agent.py                    # CLI точка входа
├── src/
│   ├── excel_parser.py         # чтение Excel → текст/структура
│   ├── brief_extractor.py      # Claude вызов 1 → BriefData (JSON)
│   ├── date_resolver.py        # "6 месяцев до даты запроса" → конкретные даты
│   ├── words_matcher.py        # поиск слов брифа в words_ok_groups_v2.xlsx
│   ├── regex_generator.py      # Claude вызов 2 → list_words (regex паттерны)
│   └── notebook_filler.py      # заполнение шаблона .ipynb через nbformat
├── templates/
│   └── b2b_template.ipynb      # шаблон с маркерами ##AGENT:xx##
├── data/
│   └── words_ok_groups_v2.xlsx # словарь допустимых слов
└── output/                     # результирующие ноутбуки
```

### Поток данных

```
Excel-бриф (любая структура)
    → excel_parser      → сырой текст всех ячеек
    → brief_extractor   → BriefData (Claude, вызов 1)
    → date_resolver     → конкретные даты start/end
    → words_matcher     → lst_sbersov (детерминировано)
    → regex_generator   → list_words (Claude, вызов 2)
    → notebook_filler   → output/{name_safe}_script.ipynb
```

---

## BriefData — промежуточная структура

Все поля извлекаются Claude из Excel в виде JSON:

| Поле | Строка в Excel | Тип | Дефолт |
|---|---|---|---|
| `name` | "Название компании заказчика" | str | — обязательное |
| `inn_client` | "ИНН заказчика" | List[str] | — обязательное |
| `analysis_period` | "Анализируемый период" | str | — обязательное |
| `product_words` | "Потребляемая продукция" | List[str] | `[]` |
| `regions` | "Регион" | List[str] | `[]` (все регионы) |
| `okved_list` | "Вид бизнеса" | List[str] | `[]` (все ОКВЭД) |
| `exclusions` | "Исключения" | List[str] | `[]` |
| `revenue_min` | "Объем выручки" (нижняя граница) | int | `100_000_000` |
| `revenue_max` | "Объем выручки" (верхняя граница) | int\|null | `222_500_000_000` |
| `trans_sum_min` | "Минимальный объем потребления целевой продукции" | int | `10_000_000` |
| `trans_cnt_min` | "Минимальная частота потребления целевой продукции" | int | `3` |

---

## Маппинг ячеек ноутбука

Шаблон содержит маркеры `##AGENT:xx##` в первой строке-комментарии ячейки. `notebook_filler.py` находит ячейку по маркеру и заменяет её содержимое целиком сгенерированным кодом. Итого **11 маркеров**.

### 1. `##AGENT:name##`
```python
# ##AGENT:name##
name = 'OOO_Fresh'
```

### 2. `##AGENT:inn_client##`
```python
# ##AGENT:inn_client##
inn_client = ['5009138436']
```

### 3. `##AGENT:date_filter##`
`date_resolver.py` парсит `analysis_period` и вычисляет даты относительно `today`.
Поддерживаемые форматы (см. раздел "date_resolver"):
```python
# ##AGENT:date_filter##
words_finadv = words_finadv[
    (~words_finadv['c_nazn'].isNull())
    & (words_finadv['short_dt'] >= '2025-10-17')
    & (words_finadv['short_dt'] <= '2026-03-17')
]
```

### 4. `##AGENT:date_filter2##`
Второй фильтр по датам для `words_finadv_upd_` (используется в логике `already_clients`).
Генерируется с теми же датами, что и `##AGENT:date_filter##`.
```python
# ##AGENT:date_filter2##
words_finadv_upd_ = words_finadv_upd[
    (words_finadv_upd['short_dt'] >= '2025-10-17')
    & (words_finadv_upd['short_dt'] <= '2026-03-17')
]
```

### 5. `##AGENT:lst_sbersov##`
`words_matcher.py` ищет совпадения `product_words` в `words_ok_groups_v2.xlsx`.
Логика matching описана в разделе "words_matcher". Если совпадений нет — список пустой.
```python
# ##AGENT:lst_sbersov##
lst_sbersov = ['Панель', 'Фасад']

df_sbersov_spark = spark.createDataFrame(pd.DataFrame(lst_sbersov, columns=['word']))
```

### 6. `##AGENT:list_words##`
Claude генерирует regex на основе `product_words` по шаблону:
`r'\bСТЕМ1\w{0,3}[-/ ]*СТЕМ2\w{0,3}\b'` — для каждой фразы оба порядка слов.
```python
# ##AGENT:list_words##
list_words = [
    r'\bфасадн\w{0,3}[-/ ]*кассет\w{0,3}\b',
    r'\bкассет\w{0,3}[-/ ]*фасадн\w{0,3}\b',
    r'\bалюмини\w{0,3}[-/ ]*панел\w{0,3}\b',
    r'\bпанел\w{0,3}[-/ ]*алюмини\w{0,3}\b',
]
```

### 7. `##AGENT:regions##`
```python
# ##AGENT:regions##
regions = ['Московская область', 'Москва', 'Республика Башкортостан']
```
Если список пустой — фильтрация по регионам не применяется.
Ячейка с ручным `txt =` (fuzzy region matching) в шаблоне заменяется этим маркером целиком — ручной ввод текста не нужен.

### 8. `##AGENT:okved_list##`
Агент генерирует **два варианта** кода в зависимости от того, пустой ли `okved_list`:

**Если `okved_list` непустой** — фильтр применяется явно:
```python
# ##AGENT:okved_list##
okved_list = ['45.23', '46.11', '46.12']
okved_ = okved_part\
    .filter(F.col('okved_original_version') == 2)\
    .filter(F.col('okved').isin(okved_list))\
    .drop_duplicates(subset=['inn'])\
    .select('inn', 'okved')
```

**Если `okved_list` пустой** — все ОКВЭД:
```python
# ##AGENT:okved_list##
okved_list = []
okved_ = okved_part\
    .filter(F.col('okved_original_version') == 2)\
    .drop_duplicates(subset=['inn'])\
    .select('inn', 'okved')
```

### 9. `##AGENT:exclusions##`
Переменная переименована в `df_exclusions` (в оригинальном шаблоне `df` — слишком общее имя, переиспользуется в других секциях).
```python
# ##AGENT:exclusions##
df_exclusions = pd.DataFrame(data=['7722406860', '9107000761'], columns=['inn'])
```
Если `exclusions` пустой:
```python
# ##AGENT:exclusions##
df_exclusions = pd.DataFrame(data=[], columns=['inn'])
```
**Примечание:** шаблон и последующие ячейки, использующие `df` для исключений, также переименовываются в `df_exclusions` при подготовке шаблона.

### 10. `##AGENT:revenue##`
`end_rev` определяется для документирования верхней границы, но фильтр применяет только нижнюю — это соответствует оригинальному поведению ноутбука.
```python
# ##AGENT:revenue##
start_rev = 100_000_000
end_rev = 222_500_000_000  # верхняя граница (не применяется в фильтре)
revenue_filtered = revenue_2022_2023.filter(F.col('revenue') >= start_rev)
```

### 11. `##AGENT:trans_thresholds##`
```python
# ##AGENT:trans_thresholds##
trans_sum_ust_down = 10_000_000
trans_cnt_ust_down = 3
```

---

## Два вызова Claude

### Вызов 1 — Извлечение полей (brief_extractor.py)

- **Модель:** `claude-sonnet-4-6`
- **Входные данные:** всё содержимое Excel в виде текста (все листы, все ячейки)
- **Системный промпт:** описание задачи + JSON-схема с типами и описаниями полей
- **Ответ:** JSON строго по схеме BriefData
- **Валидация:** проверка обязательных полей (`name`, `inn_client`, `analysis_period`); при отсутствии — ошибка с понятным сообщением

### Вызов 2 — Генерация regex (regex_generator.py)

- **Модель:** `claude-sonnet-4-6`
- **Входные данные:** `product_words` + шаблон паттерна + пример
- **Системный промпт:** правила генерации — стемминг русских слов, оба порядка для многословных фраз, только русские строчные, только шаблон `\b...\w{0,3}[-/ ]*...\w{0,3}\b`
- **Ответ:** JSON-массив строк (regex паттерны)
- **Валидация после ответа:** каждый паттерн проверяется через `re.compile(pattern)` в Python. Если паттерн невалидный — он отбрасывается с предупреждением. Если весь список пустой — `list_words = []` (ноутбук не упадёт, просто ничего не найдёт).

---

## words_matcher.py — логика поиска слов

`words_ok_groups_v2.xlsx` содержит несколько листов или колонок, каждая из которых — тематическая группа слов. Алгоритм:

1. Прочитать все значения из всех листов и всех колонок файла в один плоский список строк `dict_words`.
2. Для каждого слова/фразы из `product_words` выполнить нечёткое сравнение (`fuzzywuzzy.process.extractBests`) со всеми словами в `dict_words`.
3. Порог совпадения: `score >= 80`.
4. Возвращать только те слова, которые нашлись в `dict_words` (оригинальное написание из словаря, не из брифа).
5. Дедупликация результата.

---

## date_resolver.py — форматы анализируемого периода

Поддерживаемые фразы (Claude в вызове 1 нормализует `analysis_period` в одну из форм):

| Фраза в брифе | Нормализованная форма | Поведение |
|---|---|---|
| "6 месяцев до даты запроса" | `"last_N_months:6"` | `end=today`, `start=today-6 months` |
| "3 месяца до даты запроса" | `"last_N_months:3"` | `end=today`, `start=today-3 months` |
| "год до даты запроса" | `"last_N_months:12"` | `end=today`, `start=today-12 months` |
| "квартал до даты запроса" | `"last_N_months:3"` | `end=today`, `start=today-3 months` |
| "с 01.01.2025 по 31.12.2025" | `"range:2025-01-01:2025-12-31"` | фиксированные даты |
| Любой другой формат | `"last_N_months:6"` | дефолт 6 месяцев + предупреждение |

`date_resolver.py` принимает нормализованную форму и возвращает `(start_date: str, end_date: str)` в формате `YYYY-MM-DD`.

---

## Именование выходного файла

`name` из брифа санируется перед использованием как имя файла:
- Пробелы → `_`
- Кириллица остаётся как есть
- Удаляются символы: `/ \ : * ? " < > |`
- Пример: `"ООО Фреш"` → `"ООО_Фреш"` → файл `output/ООО_Фреш_script.ipynb`

---

## Именование таблиц

Фиксированные значения уже заданы в шаблоне ноутбука:
```python
User_prefix = 'dvo_none'
User_postfix = 'b2b'
Jira_task = f'{name}'
```
Результирующие имена таблиц формируются автоматически, например:
`arnsdpsbx_team_monetization_prt_adhoc.dvo_none_b2b_OOO_Fresh_already_clients`

Агент не трогает эти ячейки — они остаются в шаблоне как есть.

---

## Обработка ошибок

| Ситуация | Поведение |
|---|---|
| Не найдено обязательное поле (`name`, `inn_client`, `analysis_period`) | Остановка с сообщением об ошибке |
| Поле не указано в брифе (`exclusions`, `regions`, `okved_list`) | Пустое значение по умолчанию |
| `revenue_max` не указан | Дефолт `222_500_000_000` |
| Совпадений в `words_ok_groups_v2.xlsx` нет | `lst_sbersov = []` |
| Невалидный regex от Claude в `list_words` | Отброшен с предупреждением; если все невалидны — `list_words = []` |
| Нечитаемый формат `analysis_period` | Дефолт "последние 6 месяцев" + предупреждение |
| Маркер `##AGENT:xx##` не найден в шаблоне | Предупреждение, остальные ячейки заполняются |

---

## Зависимости

```
anthropic
nbformat
openpyxl
pandas
python-dateutil
fuzzywuzzy
python-Levenshtein
```
