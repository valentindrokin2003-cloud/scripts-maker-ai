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
    → notebook_filler   → output/{name}_script.ipynb
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

Шаблон содержит маркеры `##AGENT:xx##` в комментариях. `notebook_filler.py` ищет ячейку по маркеру и заменяет её содержимое целиком.

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
`date_resolver.py` парсит `analysis_period` ("6 месяцев до даты запроса") и вычисляет даты относительно `today`.
```python
# ##AGENT:date_filter##
words_finadv = words_finadv[
    (~words_finadv['c_nazn'].isNull())
    & (words_finadv['short_dt'] >= '2025-10-17')
    & (words_finadv['short_dt'] <= '2026-03-17')
]
```

### 4. `##AGENT:lst_sbersov##`
`words_matcher.py` ищет совпадения `product_words` со словами в `words_ok_groups_v2.xlsx`.
Берёт только слова из файла-словаря. Если совпадений нет — список пустой.
```python
# ##AGENT:lst_sbersov##
lst_sbersov = ['Панель', 'Фасад']

df_sbersov_spark = spark.createDataFrame(pd.DataFrame(lst_sbersov, columns=['word']))
```

### 5. `##AGENT:list_words##`
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

### 6. `##AGENT:regions##`
```python
# ##AGENT:regions##
regions = ['Московская область', 'Москва', 'Республика Башкортостан']
```
Если список пустой — фильтрация по регионам не применяется (поведение шаблона сохраняется).

### 7. `##AGENT:okved_list##`
```python
# ##AGENT:okved_list##
okved_list = ['45.23', '46.11', '46.12']
```

### 8. `##AGENT:exclusions##`
```python
# ##AGENT:exclusions##
df = pd.DataFrame(data=['7722406860', '9107000761'], columns=['inn'])
```
Если `exclusions` пустой — `df = pd.DataFrame(data=[], columns=['inn'])`.

### 9. `##AGENT:revenue##`
```python
# ##AGENT:revenue##
start_rev = 100_000_000
end_rev = 222_500_000_000
revenue_filtered = revenue_2022_2023.filter(F.col('revenue') >= start_rev)
```

### 10. `##AGENT:trans_thresholds##`
```python
# ##AGENT:trans_thresholds##
trans_sum_ust_down = 10_000_000
trans_cnt_ust_down = 3
```

---

## Два вызова Claude

### Вызов 1 — Извлечение полей (brief_extractor.py)

- **Модель:** `claude-sonnet-4-6`
- **Входные данные:** всё содержимое Excel в виде текста (все листы)
- **Системный промпт:** описание задачи + JSON-схема с типами и описаниями полей
- **Ответ:** JSON строго по схеме BriefData
- **Валидация:** проверка обязательных полей (`name`, `inn_client`, `analysis_period`); при отсутствии — ошибка с понятным сообщением

### Вызов 2 — Генерация regex (regex_generator.py)

- **Модель:** `claude-sonnet-4-6`
- **Входные данные:** `product_words` + шаблон паттерна + пример
- **Системный промпт:** правила генерации — стемминг русских слов, оба порядка для многословных фраз, только русские строчные
- **Ответ:** JSON-массив строк (regex паттерны)

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
| Не найдено обязательное поле (`name`, `inn_client`) | Остановка с сообщением об ошибке |
| Поле не указано в брифе (`exclusions`, `regions`) | Пустое значение по умолчанию |
| `revenue_max` не указан | Дефолт `222_500_000_000` |
| Совпадений в `words_ok_groups_v2.xlsx` нет | `lst_sbersov = []` |
| Маркер `##AGENT:xx##` не найден в шаблоне | Предупреждение, остальные ячейки заполняются |

---

## Зависимости

```
anthropic
nbformat
openpyxl
pandas
python-dateutil
```
