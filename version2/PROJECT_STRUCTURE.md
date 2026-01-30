# Структура проекта v2

Описание папок и файлов в проекте v2.

---

## 1. Дерево папок

```
auto-gen-v2/
│
├── main.py                    # Точка входа
│
├── console/
│   ├── __init__.py
│   ├── menu.py                # Главное меню
│   └── hotkeys.py             # Горячие клавиши
│
├── sites/
│   └── aistudio/
│       ├── __init__.py
│       ├── helpers.py         # Общие функции для AI Studio
│       ├── mode_standard.py   # Стандартный режим генерации
│       ├── mode_multiformat.py        # Мультиформатный режим
│       └── mode_multiformat_with_refs.py  # Режим с референсами
│
├── utils/
│   ├── __init__.py
│   ├── process_manager.py     # Управление воркер-процессом
│   ├── settings.py            # Загрузка/сохранение настроек
│   ├── coordinates.py         # Загрузка/сохранение координат
│   └── logger.py              # Настройка логирования
│
├── data/
│   ├── settings.json          # Настройки пользователя
│   ├── coordinates.json       # Координаты элементов
│   ├── all_card_prompts.txt   # Файл с промптами (пример)
│   └── images/                # Папка для референсов
│       ├── лицо/
│       └── оборот/
│
├── logs/
│   └── auto-gen.log           # Логи работы
│
├── docs/                      # Документация
│   ├── PLAN_V2.md
│   ├── ALGO_standard.md
│   ├── ... (остальные md файлы)
│   └── USER_GUIDE.md
│
├── old_code/                  # Код v1 для справки
│   └── ... (копия v1)
│
├── requirements.txt           # Зависимости Python
└── README.md                  # Краткое описание проекта
```

---

## 2. Описание папок

### 2.1. Корень проекта

| Файл               | Назначение                                                |
| ------------------ | --------------------------------------------------------- |
| `main.py`          | Точка входа. Инициализация, запуск меню.                  |
| `requirements.txt` | Зависимости: `pyautogui`, `keyboard`, `Pillow`, `pywin32` |
| `README.md`        | Краткое описание для GitHub                               |

### 2.2. console/

Модули для работы с консольным интерфейсом.

| Файл         | Назначение                                 |
| ------------ | ------------------------------------------ |
| `menu.py`    | Отображение меню, выбор режима/сайта/файла |
| `hotkeys.py` | Регистрация горячих клавиш, обработчики    |

### 2.3. sites/

Папка для модулей разных сайтов. Каждый сайт — отдельная подпапка.

```
sites/
├── aistudio/     # Google AI Studio
├── midjourney/   # Midjourney (будущее)
└── dalle/        # DALL-E (будущее)
```

#### sites/aistudio/

| Файл                            | Назначение                                                      |
| ------------------------------- | --------------------------------------------------------------- |
| `helpers.py`                    | Общие функции: клики, вставка, проверка изображения, сохранение |
| `mode_standard.py`              | Алгоритм стандартного режима                                    |
| `mode_multiformat.py`           | Алгоритм мультиформатного режима                                |
| `mode_multiformat_with_refs.py` | Алгоритм режима с референсами                                   |

### 2.4. utils/

Утилиты общего назначения.

| Файл                 | Назначение                                |
| -------------------- | ----------------------------------------- |
| `process_manager.py` | Запуск/остановка воркер-процесса          |
| `settings.py`        | Чтение/запись `settings.json`             |
| `coordinates.py`     | Чтение/запись `coordinates.json`          |
| `logger.py`          | Настройка logging (формат, файл, консоль) |

### 2.5. data/

Пользовательские данные.

| Файл/Папка         | Назначение                      |
| ------------------ | ------------------------------- |
| `settings.json`    | Настройки пользователя          |
| `coordinates.json` | Координаты элементов интерфейса |
| `*.txt`            | Файлы с промптами               |
| `images/лицо/`     | Референсы для лицевой стороны   |
| `images/оборот/`   | Референсы для оборотной стороны |

### 2.6. logs/

Логи работы программы.

| Файл           | Назначение        |
| -------------- | ----------------- |
| `auto-gen.log` | Основной лог-файл |

### 2.7. docs/

Документация проекта.

### 2.8. old_code/

Полная копия кода v1 для справки при разработке.

---

## 3. Описание ключевых файлов

### 3.1. main.py

```python
"""
Точка входа в программу v2.
"""
from console.menu import show_main_menu
from console.hotkeys import register_hotkeys
from utils.logger import setup_logging
from utils.settings import load_settings
from utils.coordinates import load_coordinates

def main():
    # Настройка логирования
    setup_logging()

    # Загрузка данных
    settings = load_settings()
    coordinates, relative_movements = load_coordinates()

    # Регистрация горячих клавиш
    register_hotkeys()

    # Показать главное меню
    show_main_menu(settings, coordinates, relative_movements)

if __name__ == "__main__":
    main()
```

### 3.2. sites/aistudio/helpers.py

```python
"""
Общие функции для работы с AI Studio.
"""
import pyautogui
import time

def click(x, y, delay=0.5):
    """Клик по координатам с задержкой."""
    pyautogui.click(x, y)
    time.sleep(delay)

def paste_text(text):
    """Вставка текста через буфер обмена."""
    pyperclip.copy(text)
    pyautogui.hotkey('ctrl', 'v')

def wait_until_image_ready(image_location, timeout, interval, ...):
    """Ожидание генерации изображения."""
    ...

def save_image(image_location, to_save_option, filename):
    """Сохранение изображения через контекстное меню."""
    ...
```

### 3.3. sites/aistudio/mode_standard.py

```python
"""
Стандартный режим генерации.
"""
from .helpers import click, paste_text, save_image, wait_until_image_ready

def load_tasks_from_file(filepath):
    """Загрузка задач из файла промптов."""
    ...

def get_plan_info(tasks, settings):
    """Получение сводки для отображения."""
    ...

def run_mode(tasks, settings, coordinates, relative_movements):
    """Запуск генерации."""
    ...
```

### 3.4. utils/process_manager.py

```python
"""
Управление воркер-процессом.
"""
from multiprocessing import Process

worker_process = None

def start_automation(target_func, args):
    """Запуск воркера."""
    global worker_process
    worker_process = Process(target=target_func, args=args)
    worker_process.start()

def stop_automation():
    """Жёсткая остановка воркера."""
    global worker_process
    if worker_process and worker_process.is_alive():
        worker_process.terminate()
        worker_process.join(timeout=1.0)
```

---

## 4. Зависимости (requirements.txt)

```
pyautogui>=0.9.54
keyboard>=0.13.5
Pillow>=10.0.0
pyperclip>=1.8.2
pywin32>=306
```

---

## 5. Принципы организации

### 5.1. Разделение ответственности

| Уровень    | Ответственность                            |
| ---------- | ------------------------------------------ |
| `main.py`  | Инициализация, запуск                      |
| `console/` | Взаимодействие с пользователем             |
| `sites/`   | Логика автоматизации для конкретных сайтов |
| `utils/`   | Общие утилиты                              |
| `data/`    | Пользовательские данные                    |

### 5.2. Независимость модулей

- `mode_*.py` не импортируют друг друга
- `helpers.py` не зависит от режимов
- `utils/` не зависит от `sites/`

### 5.3. Добавление нового сайта

1. Создать папку `sites/newsite/`
2. Создать `helpers.py` с функциями для этого сайта
3. Создать `mode_*.py` для каждого режима
4. Добавить сайт в меню выбора

### 5.4. Добавление нового режима

1. Создать файл `sites/aistudio/mode_newmode.py`
2. Реализовать функции `load_tasks_from_file`, `get_plan_info`, `run_mode`
3. Добавить режим в меню выбора

---

## 6. Файлы данных

### 6.1. settings.json

```json
{
	"PROMPTS_FILE": "data/all_card_prompts.txt",
	"START_FROM_CARD": 1,
	"END_CARD": null,
	"GENERATION_WAIT": 20.0,
	"CHECK_IMAGE_GENERATED": true,
	"IMAGE_WAIT_INTERVAL": 2.0,
	"FACE_ASPECT_RATIO": "4:3",
	"BACK_ASPECT_RATIO": "3:2"
}
```

### 6.2. coordinates.json

```json
{
  "coordinates": {
    "PROMPT_INPUT": [1234, 567],
    "IMAGE_LOCATION": [890, 123],
    ...
  },
  "relative_movements": {
    "TO_SAVE_OPTION": [50, 120]
  }
}
```
