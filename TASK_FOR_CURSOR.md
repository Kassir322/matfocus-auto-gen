# Задача: Обновление AI Studio Automation под новый формат промптов

## Контекст проекта

Программа на Python для автоматизации генерации изображений в AI Studio через PyAutoGUI.
Использует координатный подход, процессную архитектуру, hotkeys для управления.

**Методология:** Следуй принципам из файла `Методология_разработки_скриптов_автоматизации.md`

## Проблема

Изменился формат файла с промптами и алгоритм работы.

### Старый формат (убрать поддержку):

```
Карточка 1 - Промпт 1: текст
Карточка 1 - Промпт 2: текст
Карточка 1 - Промпт 3: текст
```

### Новый формат (реализовать):

```
Карточка 1 лицо - Промпт 1: текст для лицевой стороны
Карточка 1 оборот - Промпт 1: текст для оборотной стороны
Карточка 1 лицо - Промпт 2: текст для второй пары
Карточка 1 оборот - Промпт 2: текст для второй пары
Карточка 2 лицо - Промпт 1: текст для второй карточки
Карточка 2 оборот - Промпт 1: текст для второй карточки
```

## Ключевое понимание структуры

**ВАЖНО:** Одна карточка содержит НЕСКОЛЬКО ПАР промптов (лицо + оборот).

```
Карточка 1
├── Пара 1
│   ├── лицо - Промпт 1 → генерация в формате 4:3
│   └── оборот - Промпт 1 → генерация в формате 3:2
├── Пара 2
│   ├── лицо - Промпт 2 → генерация в формате 4:3
│   └── оборот - Промпт 2 → генерация в формате 3:2
└── Пара 3
    ├── лицо - Промпт 3 → генерация в формате 4:3
    └── оборот - Промпт 3 → генерация в формате 3:2

Карточка 2
├── Пара 1
│   ├── лицо - Промпт 1
│   └── оборот - Промпт 1
...
```

## Алгоритм работы (детально)

### Для одной пары промптов:

```python
# Пример: Карточка 1, Пара 2 (промпт номер 2)

# ЛИЦЕВАЯ СТОРОНА (4:3)
1. Создать новый чат (ChatManager.create_new_chat_only())
2. Кликнуть в поле ввода промпта (PROMPT_INPUT)
3. Вставить промпт "Карточка 1 лицо - Промпт 2" через буфер обмена
4. Переименовать чат → "Карточка 1 - лицо - Промпт 2"
5. Кликнуть на FORMAT_SELECTOR (новая координата!)
6. Ввести "4:3" и нажать Enter
7. Вернуться к полю ввода промпта
8. Запустить генерацию (Ctrl+Enter)
9. Ждать GENERATION_WAIT секунд
10. (Опционально) Проверить что изображение сгенерировалось
11. Сохранить изображение → "Карточка_1_лицо_промпт_2_4x3.png"

# ОБОРОТНАЯ СТОРОНА (3:2)
12. Создать НОВЫЙ чат
13. Кликнуть в поле ввода промпта
14. Вставить промпт "Карточка 1 оборот - Промпт 2"
15. Переименовать чат → "Карточка 1 - оборот - Промпт 2"
16. Кликнуть на FORMAT_SELECTOR
17. Ввести "3:2" и нажать Enter
18. Вернуться к полю ввода
19. Запустить генерацию (Ctrl+Enter)
20. Ждать
21. Сохранить → "Карточка_1_оборот_промпт_2_3x2.png"

# Следующая пара
22. Перейти к Паре 3 (промпт номер 3) этой же карточки
23. Повторить шаги 1-21 для пары 3

# Следующая карточка
24. Когда все пары Карточки 1 обработаны → перейти к Карточке 2
```

## Технические требования

### 1. Парсер файла (`core/file_handler.py`)

**Новый regex:**

```python
pattern = r'Карточка (\d+) (лицо|оборот) - Промпт (\d+): (.+)'
# Группы: (номер_карточки, тип, номер_промпта, текст)
```

**Структура данных:**

```python
# Результат парсинга:
{
    1: [  # Карточка 1
        {  # Пара 1
            'лицо': 'текст промпта для лицевой стороны',
            'оборот': 'текст промпта для оборотной стороны'
        },
        {  # Пара 2
            'лицо': 'текст для второй лицевой',
            'оборот': 'текст для второй оборотной'
        },
        {  # Пара 3
            'лицо': '...',
            'оборот': '...'
        }
    ],
    2: [  # Карточка 2
        {'лицо': '...', 'оборот': '...'},
        {'лицо': '...', 'оборот': '...'}
    ]
}
```

**Проверки:**

- Если есть "лицо" но нет "оборот" для одного промпта → пропустить пару, залогировать warning
- Если есть "оборот" но нет "лицо" → пропустить пару, залогировать warning
- Пара считается полной только если есть оба промпта

### 2. Новый генератор (`core/multi_format_generator.py`)

Создать класс `MultiFormatGenerator` по аналогии с `ImageGenerator`.

**Ключевые методы:**

```python
class MultiFormatGenerator:
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.clipboard = ClipboardManager()
        self.logger = Logger()
        self.chat_manager = ChatManager()

    def select_image_format(self, format_ratio: str) -> bool:
        """
        Выбор формата изображения через UI.

        Args:
            format_ratio: "4:3" или "3:2"

        Returns:
            bool: успешность операции

        Алгоритм:
        1. Клик на FORMAT_SELECTOR координату
        2. Пауза BETWEEN_CLICKS
        3. Ввод format_ratio через pyautogui.write()
        4. Пауза BETWEEN_CLICKS
        5. Enter для подтверждения
        6. Пауза BETWEEN_CLICKS
        """
        pass

    def generate_single_side(self, card_number: int, pair_number: int,
                            side: str, prompt: str,
                            format_ratio: str, stop_event) -> bool:
        """
        Генерация одной стороны (лицо ИЛИ оборот).

        Args:
            card_number: номер карточки
            pair_number: номер пары промптов
            side: "лицо" или "оборот"
            prompt: текст промпта
            format_ratio: "4:3" или "3:2"
            stop_event: событие остановки

        Возвращает True если успешно.

        Алгоритм:
        1. Создать новый чат
        2. Ввести промпт
        3. Переименовать чат: f"Карточка {card_number} - {side} - Промпт {pair_number}"
        4. Выбрать формат (select_image_format)
        5. Вернуться к полю ввода
        6. Генерация (Ctrl+Enter)
        7. Ожидание
        8. Опциональная проверка изображения
        9. Сохранение: f"Карточка_{card_number}_{side}_промпт_{pair_number}_{format_ratio.replace(':', 'x')}.png"
        """
        pass

    def generate_pair(self, card_number: int, pair_number: int,
                     prompts_dict: dict, stop_event) -> int:
        """
        Генерация пары (лицо + оборот).

        Args:
            card_number: номер карточки
            pair_number: номер пары
            prompts_dict: {'лицо': 'текст', 'оборот': 'текст'}
            stop_event: событие остановки

        Returns:
            int: количество успешно созданных изображений (0, 1 или 2)

        Алгоритм:
        1. Генерация лицевой стороны (4:3)
        2. Пауза BETWEEN_GENERATIONS
        3. Генерация оборотной стороны (3:2)
        """
        pass

    def process_card(self, card_number: int, pairs_list: list,
                    stop_event) -> tuple:
        """
        Обработка всех пар одной карточки.

        Args:
            card_number: номер карточки
            pairs_list: список словарей с парами промптов
            stop_event: событие остановки

        Returns:
            tuple: (количество обработанных пар, количество созданных изображений)

        Алгоритм:
        - Проход по всем парам в pairs_list
        - Для каждой пары вызов generate_pair()
        - Пауза BETWEEN_CARDS после последней пары
        """
        pass

    def automation_worker(self, stop_event, start_card: int,
                         check_image_enabled: bool,
                         generation_wait: float,
                         cards_to_process: int):
        """
        Главный рабочий процесс (точка входа для Process).

        Использует обновлённый FileHandler для получения структуры
        с парами промптов.
        """
        pass
```

### 3. Координаты (`config/coordinates.py`)

**Добавить:**

```python
'FORMAT_SELECTOR': [0, 0],  # Выпадающий список выбора формата изображения
```

**Подсказка в list_coordinates():**

```python
if name == 'FORMAT_SELECTOR':
    coords_info.append(f"  {name}: {coord} - {status} [ДЛЯ МУЛЬТИФОРМАТНОГО РЕЖИМА]")
```

### 4. Настройки (`config/settings.py`)

**Добавить параметр:**

```python
'GENERATION_MODE': 'multi_format',  # Возможные значения: 'standard', 'multi_format'
```

**Новый метод:**

```python
def toggle_generation_mode(self):
    """Переключение между standard и multi_format"""
    current = self.settings['GENERATION_MODE']
    new_mode = 'multi_format' if current == 'standard' else 'standard'
    self.set('GENERATION_MODE', new_mode)

    mode_names = {
        'standard': 'Стандартный (старый алгоритм)',
        'multi_format': 'Мультиформатный (лицо 4:3 + оборот 3:2)'
    }
    print(f"✓ Режим изменён: {mode_names[new_mode]}")
```

**Обновить configure_generations_per_card():**

```python
def configure_generations_per_card(self):
    if self.settings['GENERATION_MODE'] == 'multi_format':
        print("⚠️ Недоступно в мультиформатном режиме")
        print("   Количество изображений = количество пар * 2")
        return
    # ... остальной код
```

### 5. Process Manager (`utils/process_manager.py`)

**Обновить start_automation():**

```python
def start_automation(self, settings_manager):
    generation_mode = settings_manager.get('GENERATION_MODE')

    # Проверка координат в зависимости от режима
    critical_coords = ['PROMPT_INPUT', 'IMAGE_LOCATION', 'NEW_CHAT_BUTTON', 'CHAT_NAME_INPUT']

    if generation_mode == 'multi_format':
        critical_coords.append('FORMAT_SELECTOR')

    # ... проверки

    # Выбор генератора
    if generation_mode == 'multi_format':
        from core.multi_format_generator import MultiFormatGenerator
        generator = MultiFormatGenerator(settings_manager)

        self.automation_process = Process(
            target=generator.automation_worker,
            args=(self.stop_event, start_card, check_image_enabled,
                  generation_wait, cards_to_process)
        )
    else:
        # Стандартный режим (ImageGenerator)
        from core.image_generator import ImageGenerator
        generator = ImageGenerator(settings_manager)
        # ... старый код
```

### 6. Hotkeys (`ui/hotkeys.py`)

**Добавить:**

```python
keyboard.add_hotkey('ctrl+7', self.settings_manager.toggle_generation_mode)
```

### 7. Console UI (`ui/console.py`)

**Обновить show_instructions():**

```python
print("  Ctrl+7 - ПЕРЕКЛЮЧИТЬ РЕЖИМ ГЕНЕРАЦИИ ⭐")
```

**Обновить show_current_settings():**

```python
generation_mode = settings_manager.get('GENERATION_MODE')
mode_names = {
    'standard': 'Стандартный (множественные генерации)',
    'multi_format': 'Мультиформатный (лицо 4:3 + оборот 3:2)'
}

print(f"  🎯 РЕЖИМ: {mode_names.get(generation_mode, generation_mode)}")

if generation_mode == 'multi_format':
    print(f"  Пар промптов на карточку: зависит от файла")
    print(f"  Изображений на пару: 2 (лицо + оборот)")
else:
    print(f"  Генераций на карточку: {settings_manager.get('GENERATIONS_PER_CARD')}")

# Проверка FORMAT_SELECTOR для multi_format
if generation_mode == 'multi_format':
    if COORDINATES.get('FORMAT_SELECTOR', (0, 0)) == (0, 0):
        print("  ❌ FORMAT_SELECTOR не задан! Обязателен для этого режима!")
```

## Примеры использования

### Пример 1: Файл с 2 карточками по 2 пары

```
Карточка 1 лицо - Промпт 1: Африка с высоты
Карточка 1 оборот - Промпт 1: Саванна
Карточка 1 лицо - Промпт 2: Баобаб
Карточка 1 оборот - Промпт 2: Лес
Карточка 2 лицо - Промпт 1: Антарктида
Карточка 2 оборот - Промпт 1: Пингвины
Карточка 2 лицо - Промпт 2: Лёд
Карточка 2 оборот - Промпт 2: Тюлень
```

**Результат:**

- Карточка 1: 4 изображения (2 пары × 2 стороны)
- Карточка 2: 4 изображения (2 пары × 2 стороны)
- Всего: 8 чатов создано, 8 изображений

**Названия файлов:**

```
Карточка_1_лицо_промпт_1_4x3.png
Карточка_1_оборот_промпт_1_3x2.png
Карточка_1_лицо_промпт_2_4x3.png
Карточка_1_оборот_промпт_2_3x2.png
Карточка_2_лицо_промпт_1_4x3.png
Карточка_2_оборот_промпт_1_3x2.png
Карточка_2_лицо_промпт_2_4x3.png
Карточка_2_оборот_промпт_2_3x2.png
```

**Названия чатов:**

```
Карточка 1 - лицо - Промпт 1
Карточка 1 - оборот - Промпт 1
Карточка 1 - лицо - Промпт 2
Карточка 1 - оборот - Промпт 2
Карточка 2 - лицо - Промпт 1
Карточка 2 - оборот - Промпт 1
Карточка 2 - лицо - Промпт 2
Карточка 2 - оборот - Промпт 2
```

### Пример 2: Неполная пара (обработка ошибок)

```
Карточка 1 лицо - Промпт 1: Текст
Карточка 1 оборот - Промпт 1: Текст
Карточка 1 лицо - Промпт 2: Текст
# Карточка 1 оборот - Промпт 2 ОТСУТСТВУЕТ!
Карточка 2 лицо - Промпт 1: Текст
Карточка 2 оборот - Промпт 1: Текст
```

**Поведение:**

- Карточка 1, Пара 1: ✓ генерируется
- Карточка 1, Пара 2: ⚠️ пропускается с warning "Пара 2 неполная"
- Карточка 2, Пара 1: ✓ генерируется

## Проверки и валидация

### При запуске в multi_format режиме:

```python
# В ProcessManager.start_automation()

if generation_mode == 'multi_format':
    # 1. Проверить FORMAT_SELECTOR
    if COORDINATES.get('FORMAT_SELECTOR', (0, 0)) == (0, 0):
        print("[ГЛАВНЫЙ] ОШИБКА: FORMAT_SELECTOR не настроен!")
        print("   Используйте Ctrl+0 для настройки координаты")
        print("   FORMAT_SELECTOR - выпадающий список выбора формата (справа от промпта)")
        return

    # 2. Проверить файл промптов
    file_handler = FileHandler(settings_manager)
    pairs_data = file_handler.load_prompts()

    if not pairs_data:
        print("[ГЛАВНЫЙ] ОШИБКА: Нет валидных пар промптов в файле!")
        return

    # 3. Показать статистику
    total_pairs = sum(len(pairs) for pairs in pairs_data.values())
    print(f"[ГЛАВНЫЙ] Найдено пар промптов: {total_pairs}")
    print(f"[ГЛАВНЫЙ] Будет создано изображений: {total_pairs * 2}")
```

### В FileHandler при парсинге:

```python
# Проверка полноты пар
for card_num in prompts_by_card:
    pairs = prompts_by_card[card_num]
    for pair_num, pair_dict in pairs.items():
        if 'лицо' not in pair_dict:
            logger.warning(f"Карточка {card_num}, Пара {pair_num}: отсутствует 'лицо'")
        if 'оборот' not in pair_dict:
            logger.warning(f"Карточка {card_num}, Пара {pair_num}: отсутствует 'оборот'")

        # Пара считается невалидной если не хватает одной из сторон
        if 'лицо' not in pair_dict or 'оборот' not in pair_dict:
            # Не добавляем эту пару в финальный результат
            continue
```

## Обратная совместимость

**Сохранить старый режим `standard`:**

- Оставить `ImageGenerator` без изменений
- Оставить старый `FileHandler.load_prompts()` или добавить метод `load_prompts_old_format()`
- Переключение через `GENERATION_MODE`

**Не трогать:**

- `core/image_generator.py` (старый генератор)
- `core/chat_manager.py` (используется обоими режимами)
- `utils/clipboard.py` (используется обоими)
- `utils/logger.py` (используется обоими)

## План реализации (поэтапно)

### Этап 1: Парсер

1. Обновить `FileHandler.load_prompts()` для нового формата
2. Протестировать на примере файла
3. Убедиться что структура данных правильная

### Этап 2: Базовый генератор

1. Создать `MultiFormatGenerator` с методом `select_image_format()`
2. Реализовать `generate_single_side()` без проверок
3. Протестировать на одной стороне одной пары

### Этап 3: Полный цикл

1. Реализовать `generate_pair()`
2. Реализовать `process_card()`
3. Протестировать на одной карточке с 2 парами

### Этап 4: Интеграция

1. Добавить координату FORMAT_SELECTOR
2. Обновить настройки (GENERATION_MODE)
3. Обновить ProcessManager для выбора генератора
4. Добавить hotkey Ctrl+7

### Этап 5: UI и проверки

1. Обновить консольный интерфейс
2. Добавить валидацию при запуске
3. Улучшить логирование
4. Финальное тестирование

## Критически важно НЕ ошибиться

1. **Одна карточка = МНОГО пар**, а не одна пара
2. **Пара = лицо + оборот**, оба промпта разные
3. **Каждая сторона в отдельном чате**
4. **Лицо всегда 4:3, оборот всегда 3:2**
5. **Порядок: все пары Карточки 1, потом все пары Карточки 2**

## Тестовый файл для проверки

```
Карточка 1 лицо - Промпт 1: Test front 1
Карточка 1 оборот - Промпт 1: Test back 1
Карточка 1 лицо - Промпт 2: Test front 2
Карточка 1 оборот - Промпт 2: Test back 2
```

**Ожидаемый результат:**

- 4 чата создано
- 4 изображения: 2 в формате 4:3 (лицо), 2 в формате 3:2 (оборот)
- Файлы: `Карточка_1_лицо_промпт_1_4x3.png`, `Карточка_1_оборот_промпт_1_3x2.png`, etc.

---

**Приоритет: Правильность > Скорость**

Лучше медленно но верно, чем быстро и неправильно.
Следуй методологии пошагового наращивания функционала.
