# Формат файла промптов для режима standard

Описание формата входного текстового файла для стандартного режима генерации.

---

## 1. Общее описание

Файл промптов для режима `standard` содержит список промптов, привязанных к номерам карточек. Каждая карточка может иметь **несколько промптов** (несколько генераций).

---

## 2. Формат строки

```
Карточка {номер} - Промпт {номер_промпта}: {текст промпта}
```

Регулярное выражение:

```regex
^Карточка (\d+) - Промпт (\d+): (.+)$
```

Группы:

1. `(\d+)` — номер карточки
2. `(\d+)` — номер промпта внутри карточки
3. `(.+)` — текст промпта

---

## 3. Примеры валидных строк

```
Карточка 1 - Промпт 1: A cute cat sitting on a windowsill
Карточка 1 - Промпт 2: A fluffy kitten playing with yarn
Карточка 2 - Промпт 1: A majestic lion in the savanna
Карточка 3 - Промпт 1: A colorful parrot on a branch
Карточка 3 - Промпт 2: A flying eagle over mountains
Карточка 3 - Промпт 3: A penguin family on ice
```

---

## 4. Правила парсинга

### 4.1. Пустые строки

- Пустые строки игнорируются.
- Строки, содержащие только пробелы, игнорируются.

### 4.2. Невалидные строки

- Строки, не соответствующие формату, **пропускаются**.
- Логируется предупреждение: `"⚠️ Строка {N} не распознана: {текст}"`

### 4.3. Порядок строк

- Строки **не обязаны** идти по порядку номеров карточек.
- Промпты **группируются** по номеру карточки при парсинге.
- Внутри карточки промпты **сортируются** по номеру промпта.

### 4.4. Дубликаты

- Если встретились два промпта с одинаковым номером для одной карточки — **последний перезаписывает предыдущий**.

---

## 5. Результат парсинга

Парсер возвращает словарь:

```python
{
    card_number: {
        "name": str,        # Название карточки (по умолчанию "Карточка {N}")
        "prompts": [str, str, ...]  # Список промптов, отсортированных по номеру
    },
    ...
}
```

Пример:

```python
{
    1: {
        "name": "Карточка 1",
        "prompts": [
            "A cute cat sitting on a windowsill",
            "A fluffy kitten playing with yarn"
        ]
    },
    2: {
        "name": "Карточка 2",
        "prompts": [
            "A majestic lion in the savanna"
        ]
    },
    3: {
        "name": "Карточка 3",
        "prompts": [
            "A colorful parrot on a branch",
            "A flying eagle over mountains",
            "A penguin family on ice"
        ]
    }
}
```

---

## 6. Название карточки

В стандартном формате название карточки **не указывается явно**. Используется формат по умолчанию:

```
"Карточка {номер}"
```

Если требуется пользовательское название — используйте режим `multiformat` (см. PROMPTS_multiformat_format.md).

---

## 7. Код парсера

```python
import re
from collections import defaultdict

def parse_standard_prompts(file_path):
    """
    Парсит файл промптов стандартного формата.

    Аргументы:
        file_path: путь к текстовому файлу

    Возвращает:
        dict: {card_number: {"name": str, "prompts": [str, ...]}}
    """
    # Регулярное выражение для парсинга
    pattern = re.compile(r'^Карточка (\d+) - Промпт (\d+): (.+)$')

    # Временное хранилище: {card_num: {prompt_num: prompt_text}}
    temp_data = defaultdict(dict)

    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()

            # Пропускаем пустые строки
            if not line:
                continue

            # Пытаемся распарсить
            match = pattern.match(line)

            if match:
                card_num = int(match.group(1))
                prompt_num = int(match.group(2))
                prompt_text = match.group(3).strip()

                # Сохраняем промпт
                temp_data[card_num][prompt_num] = prompt_text
            else:
                # Невалидная строка
                print(f"⚠️ Строка {line_num} не распознана: {line[:50]}...")

    # Формируем результат
    result = {}
    for card_num in sorted(temp_data.keys()):
        prompts_dict = temp_data[card_num]
        # Сортируем промпты по номеру
        sorted_prompts = [prompts_dict[k] for k in sorted(prompts_dict.keys())]

        result[card_num] = {
            "name": f"Карточка {card_num}",
            "prompts": sorted_prompts
        }

    return result
```

---

## 8. Подсчёт статистики

После парсинга можно вывести сводку:

```python
def get_stats(parsed_data):
    """
    Возвращает статистику по распарсенным данным.
    """
    total_cards = len(parsed_data)
    total_prompts = sum(len(card["prompts"]) for card in parsed_data.values())

    return {
        "total_cards": total_cards,
        "total_prompts": total_prompts,
        "card_range": (min(parsed_data.keys()), max(parsed_data.keys())) if parsed_data else (0, 0)
    }
```

Пример вывода:

```
[PLAN] Загружено карточек: 50
[PLAN] Всего промптов: 127
[PLAN] Диапазон номеров: 1-50
```

---

## 9. Ошибки и предупреждения

| Ситуация               | Поведение                        |
| ---------------------- | -------------------------------- |
| Файл не найден         | Исключение `FileNotFoundError`   |
| Файл пустой            | Возвращается пустой словарь `{}` |
| Все строки невалидны   | Возвращается пустой словарь `{}` |
| Невалидная строка      | Пропускается с предупреждением   |
| Некорректная кодировка | Исключение `UnicodeDecodeError`  |

---

## 10. Пример файла

```
Карточка 1 - Промпт 1: A minimalist illustration of a sunrise over mountains, soft pastel colors
Карточка 1 - Промпт 2: The same sunrise scene but with a bird flying across

Карточка 2 - Промпт 1: A vintage-style poster of a steam locomotive
Карточка 2 - Промпт 2: The locomotive approaching a station, passengers waiting

Карточка 3 - Промпт 1: An abstract geometric pattern in blue and gold
```

Результат:

- Карточка 1: 2 промпта
- Карточка 2: 2 промпта
- Карточка 3: 1 промпт
- **Итого**: 3 карточки, 5 генераций
