# Описание программы AI Studio Automation (для custom skill в Claude)

Краткое описание функционала, форматов данных и режимов. Claude может опираться на этот документ при ответах по проекту.

---

## 1. Назначение программы

Автоматизация генерации изображений на сайте **AI Studio**. Программа управляет браузером через координаты (pyautogui): клики, вставка текста, сохранение картинок. Работает в фоне с горячими клавишами; генерация запускается в подпроцессе.

**Режимы запуска:**
- `python main.py` — основной режим с горячими клавишами (генерация, настройка окна, план)
- `python main.py --v2` или `--menu` — консольное меню (выбор сайта, режима, файла промптов, план, запуск)

**Поддерживаемый сайт:** `aistudio` (другие сайты не поддерживаются).

---

## 2. Режимы генерации

| Режим | Назначение | Сайт |
|-------|------------|------|
| `standard` | Несколько изображений на одну карточку; каждый промпт — отдельный чат | aistudio |
| `multiformat` | Пары «лицо + оборот» с разными aspect ratio | aistudio |
| `multiformat_with_refs` | Как multiformat + референсное изображение перед промптом | aistudio |

---

## 3. Форматы файлов промптов

### 3.1. Режим standard

```
Карточка {N} - Промпт {M}: текст промпта
```

Regex: `^Карточка (\d+) - Промпт (\d+): (.+)$`

**Примеры:**
```
Карточка 1 - Промпт 1: A cute cat on a windowsill
Карточка 1 - Промпт 2: A fluffy kitten playing with yarn
Карточка 2 - Промпт 1: A majestic lion in the savanna
```

### 3.2. Режимы multiformat и multiformat_with_refs

```
Карточка {N} {сторона} {название} - Промпт {M}: текст промпта
```

Regex: `^Карточка (\d+) (лицо|оборот) ([^-]+) - Промпт (\d+): (.+)$`

Группы: номер карточки, сторона (лицо|оборот), название карточки, номер пары, текст промпта.

**Примеры:**
```
Карточка 63 лицо Нефть - Промпт 1: Oil derrick in a desert landscape
Карточка 63 оборот Нефть - Промпт 1: Molecular structure of petroleum
Карточка 20 лицо Балтийское море - Промпт 1: Waves crashing on sandy shore
Карточка 20 оборот Балтийское море - Промпт 1: Map of Baltic Sea region
```

---

## 4. Референсные изображения (только multiformat_with_refs)

**Папки:**
```
data/images/лицо/
data/images/оборот/
```

**Формат имени файла:**
```
{сторона}_{номер_карточки}_{safe_card_name}.{png|jpg}
```

Где `safe_card_name` — название карточки с заменой пробелов на `_` и удалением спецсимволов (`*`, `?`, `"`, `<`, `>`, `|`).

**Примеры:**
```
лицо_63_Нефть.png
оборот_20_Балтийское_море.jpg
```

Название карточки в имени референса должно совпадать с названием в файле промптов (после преобразования).

---

## 5. Имена сохраняемых файлов

| Режим | Формат | Пример |
|-------|--------|--------|
| standard | `Карточка_{N}_лицевая_промпт_{G}.png` | `Карточка_1_лицевая_промпт_1.png` |
| multiformat | `Карточка_{N}_{side}_промпт_{P}.png` | `Карточка_63_лицо_промпт_1.png` |
| multiformat_with_refs | `Карточка_{N}_{safe_name}_{side}_промпт_{P}.png` | `Карточка_63_Нефть_лицо_промпт_1.png` |

Имена чатов в AI Studio:
- standard: `Карточка {N} - генерация {G}`
- multiformat / multiformat_with_refs: `Карточка {N} - {card_name} - {side} - Промпт {P}`

---

## 6. Структура проекта (ключевое)

```
main.py                    # Точка входа (hotkeys или --menu)
sites/aistudio/
  mode_standard.py         # Режим standard
  mode_multiformat.py      # Режим multiformat
  mode_multiformat_with_refs.py  # Режим с референсами
  helpers.py               # Клики, вставка текста, сохранение изображения
ui/
  console_menu.py          # Консольное меню (выбор режима, файла, план)
  hotkeys.py               # Горячие клавиши
utils/
  generation_runner.py     # Воркеры для каждого режима
  coordinates_store.py     # Загрузка координат
  settings_store.py        # Настройки (PROMPTS_FILE, FACE_ASPECT_RATIO и т.д.)
version2/reference/        # Документация (форматы, алгоритмы, API)
```

---

## 7. Основные настройки (SETTINGS)

- `CURRENT_SITE`, `CURRENT_MODE` — выбранный сайт и режим
- `PROMPTS_FILE` — путь к файлу промптов
- `FACE_ASPECT_RATIO`, `BACK_ASPECT_RATIO` — соотношения сторон (например, `4:3`, `3:2`)
- `GENERATION_WAIT` — таймаут ожидания генерации
- `START_FROM_CARD`, `END_CARD` — диапазон карточек

---

## 8. Референсная документация

| Тема | Файл |
|------|------|
| Указатель документов | `version2/reference/DOCS_INDEX.md` |
| Режимы (кратко) | `version2/reference/MODES_REFERENCE.md` |
| Формат промптов standard | `version2/reference/PROMPTS_standard_format.md` |
| Формат промптов multiformat | `version2/reference/PROMPTS_multiformat_format.md` |
| Референсы | `version2/reference/REFERENCES_format.md` |
| Имена чатов и файлов | `version2/reference/NAMING_RULES.md` |
| Алгоритмы | `version2/reference/ALGO_*.md` |
