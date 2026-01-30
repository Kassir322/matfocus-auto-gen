# Формат файла промптов для режимов multiformat / multiformat_with_refs

Описание формата входного текстового файла для мультиформатных режимов генерации.

---

## 1. Общее описание

Файл промптов для режимов `multiformat` и `multiformat_with_refs` содержит промпты с указанием:

- Номера карточки
- **Стороны** (лицо / оборот)
- **Названия карточки** (пользовательского)
- Номера промпта (пары)

Каждая карточка состоит из **пар** — лицевая и оборотная сторона.

---

## 2. Формат строки

```
Карточка {номер} {сторона} {название} - Промпт {номер_пары}: {текст промпта}
```

Регулярное выражение:

```regex
^Карточка (\d+) (лицо|оборот) ([^-]+) - Промпт (\d+): (.+)$
```

Группы:

1. `(\d+)` — номер карточки
2. `(лицо|оборот)` — сторона карточки
3. `([^-]+)` — название карточки (до первого `-`)
4. `(\d+)` — номер промпта (пары)
5. `(.+)` — текст промпта

---

## 3. Примеры валидных строк

```
Карточка 63 лицо Нефть - Промпт 1: Oil derrick in a desert landscape, industrial style
Карточка 63 оборот Нефть - Промпт 1: Molecular structure of petroleum, scientific diagram
Карточка 63 лицо Нефть - Промпт 2: Oil barrel with black gold flowing
Карточка 63 оборот Нефть - Промпт 2: Oil refinery at sunset, industrial photography

Карточка 20 лицо Балтийское море - Промпт 1: Waves crashing on sandy shore, blue tones
Карточка 20 оборот Балтийское море - Промпт 1: Map of Baltic Sea region, vintage style
```

---

## 4. Правила парсинга

### 4.1. Пустые строки

- Пустые строки игнорируются.

### 4.2. Невалидные строки

- Строки, не соответствующие формату, **пропускаются** с предупреждением.

### 4.3. Группировка в пары

Промпты группируются по:

1. Номеру карточки
2. Номеру промпта (пары)

Каждая пара содержит максимум 2 записи: одну для "лицо" и одну для "оборот".

### 4.4. Неполные пары

Если для пары есть только "лицо" или только "оборот":

- Пара **сохраняется** с `None` для отсутствующей стороны.
- При генерации отсутствующая сторона **пропускается**.
- Логируется предупреждение.

---

## 5. Результат парсинга

Парсер возвращает словарь:

```python
{
    card_number: {
        "name": str,          # Название карточки
        "pairs": [            # Список пар, отсортированных по номеру
            {
                "лицо": str | None,    # Промпт для лицевой стороны
                "оборот": str | None   # Промпт для оборотной стороны
            },
            ...
        ]
    },
    ...
}
```

Пример:

```python
{
    63: {
        "name": "Нефть",
        "pairs": [
            {
                "лицо": "Oil derrick in a desert landscape, industrial style",
                "оборот": "Molecular structure of petroleum, scientific diagram"
            },
            {
                "лицо": "Oil barrel with black gold flowing",
                "оборот": "Oil refinery at sunset, industrial photography"
            }
        ]
    },
    20: {
        "name": "Балтийское море",
        "pairs": [
            {
                "лицо": "Waves crashing on sandy shore, blue tones",
                "оборот": "Map of Baltic Sea region, vintage style"
            }
        ]
    }
}
```

---

## 6. Название карточки

- Название берётся **из первой встреченной строки** для данного номера карточки.
- Если названия в разных строках для одной карточки различаются — используется первое, выводится предупреждение.
- Пробелы по краям обрезаются (`.strip()`).

---

## 7. Код парсера

```python
import re
from collections import defaultdict

def parse_multiformat_prompts(file_path):
    """
    Парсит файл промптов мультиформатного формата.

    Аргументы:
        file_path: путь к текстовому файлу

    Возвращает:
        dict: {card_number: {"name": str, "pairs": [{"лицо": str|None, "оборот": str|None}, ...]}}
    """
    # Регулярное выражение для парсинга
    pattern = re.compile(r'^Карточка (\d+) (лицо|оборот) ([^-]+) - Промпт (\d+): (.+)$')

    # Временное хранилище: {card_num: {"name": str, "pairs_dict": {pair_num: {"лицо": str, "оборот": str}}}}
    temp_data = {}

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
                side = match.group(2)           # "лицо" или "оборот"
                card_name = match.group(3).strip()
                pair_num = int(match.group(4))
                prompt_text = match.group(5).strip()

                # Инициализируем карточку, если первый раз
                if card_num not in temp_data:
                    temp_data[card_num] = {
                        "name": card_name,
                        "pairs_dict": defaultdict(lambda: {"лицо": None, "оборот": None})
                    }

                # Проверяем совпадение названия
                if temp_data[card_num]["name"] != card_name:
                    print(f"⚠️ Строка {line_num}: название '{card_name}' отличается от '{temp_data[card_num]['name']}'")

                # Сохраняем промпт
                temp_data[card_num]["pairs_dict"][pair_num][side] = prompt_text
            else:
                # Невалидная строка
                print(f"⚠️ Строка {line_num} не распознана: {line[:50]}...")

    # Формируем результат
    result = {}
    for card_num in sorted(temp_data.keys()):
        card_data = temp_data[card_num]
        pairs_dict = card_data["pairs_dict"]

        # Сортируем пары по номеру
        sorted_pairs = [pairs_dict[k] for k in sorted(pairs_dict.keys())]

        # Проверяем неполные пары
        for i, pair in enumerate(sorted_pairs, start=1):
            if pair["лицо"] is None:
                print(f"⚠️ Карточка {card_num}, пара {i}: отсутствует лицевая сторона")
            if pair["оборот"] is None:
                print(f"⚠️ Карточка {card_num}, пара {i}: отсутствует оборотная сторона")

        result[card_num] = {
            "name": card_data["name"],
            "pairs": sorted_pairs
        }

    return result
```

---

## 8. Подсчёт статистики

```python
def get_multiformat_stats(parsed_data):
    """
    Возвращает статистику по распарсенным данным.
    """
    total_cards = len(parsed_data)
    total_pairs = sum(len(card["pairs"]) for card in parsed_data.values())

    # Подсчёт сторон
    face_count = 0
    back_count = 0
    incomplete_pairs = 0

    for card in parsed_data.values():
        for pair in card["pairs"]:
            if pair["лицо"] is not None:
                face_count += 1
            if pair["оборот"] is not None:
                back_count += 1
            if pair["лицо"] is None or pair["оборот"] is None:
                incomplete_pairs += 1

    return {
        "total_cards": total_cards,
        "total_pairs": total_pairs,
        "total_images": face_count + back_count,
        "face_count": face_count,
        "back_count": back_count,
        "incomplete_pairs": incomplete_pairs
    }
```

Пример вывода:

```
[PLAN] Загружено карточек: 50
[PLAN] Найдено пар: 100
[PLAN] Будет создано изображений: 200 (лицо: 100, оборот: 100)
[PLAN] Неполных пар: 0
```

---

## 9. Ошибки и предупреждения

| Ситуация                       | Поведение                            |
| ------------------------------ | ------------------------------------ |
| Файл не найден                 | Исключение `FileNotFoundError`       |
| Файл пустой                    | Возвращается пустой словарь `{}`     |
| Невалидная строка              | Пропускается с предупреждением       |
| Разные названия одной карточки | Используется первое, предупреждение  |
| Неполная пара                  | Сохраняется с `None`, предупреждение |
| Дублирующаяся сторона пары     | Последняя перезаписывает предыдущую  |

---

## 10. Пример файла

```
Карточка 63 лицо Нефть - Промпт 1: Oil derrick in a desert landscape, industrial style
Карточка 63 оборот Нефть - Промпт 1: Molecular structure of petroleum, scientific diagram
Карточка 63 лицо Нефть - Промпт 2: Oil barrel with black gold flowing
Карточка 63 оборот Нефть - Промпт 2: Oil refinery at sunset, industrial photography

Карточка 20 лицо Балтийское море - Промпт 1: Waves crashing on sandy shore, blue tones
Карточка 20 оборот Балтийское море - Промпт 1: Map of Baltic Sea region, vintage style

Карточка 21 лицо Кораблестроение - Промпт 1: Ship hull under construction, shipyard
```

Результат:

- Карточка 63: 2 полных пары (4 изображения)
- Карточка 20: 1 полная пара (2 изображения)
- Карточка 21: 1 **неполная** пара (только лицо, 1 изображение)
- **Итого**: 3 карточки, 4 пары, 7 изображений, 1 неполная пара

---

## 11. Различия от standard формата

| Аспект                | standard                  | multiformat               |
| --------------------- | ------------------------- | ------------------------- |
| Сторона               | Не указывается            | Обязательно (лицо/оборот) |
| Название карточки     | По умолчанию "Карточка N" | Указывается явно          |
| Структура             | Список промптов           | Список пар {лицо, оборот} |
| Генерации на карточку | N промптов                | N пар × 2 стороны         |
