---
name: Esc только в browser режиме
overview: Сделать так, чтобы Esc останавливал воркер только при браузерной генерации; при API-режиме Esc не обрабатывать, чтобы пользователь мог пользоваться компьютером (в т.ч. нажимать Esc в других приложениях) без остановки фоновой API-генерации.
todos: []
isProject: false
---

# Esc только для браузерного режима

## Текущее поведение

- В [ui/hotkeys.py](ui/hotkeys.py) глобально зарегистрирован хоткей: `keyboard.add_hotkey("esc", self.on_esc_stop_worker)`.
- `on_esc_stop_worker` всегда вызывает `process_control.stop_worker()` — воркер завершается по Esc в любом режиме.

## Идея решения

При нажатии Esc проверять **тип текущего запущенного воркера** (api / browser). Если запущен API-воркер — не вызывать `stop_worker()` (Esc «не срабатывает»). Если браузерный — вызывать как сейчас.

Тип воркера известен только в момент запуска в [main.py](main.py) (и при желании в [ui/console_menu.py](ui/console_menu.py)), поэтому его нужно сохранять в `process_control` при `start_worker` и сбрасывать при `stop_worker`.

## Изменения по файлам

### 1. [utils/process_control.py](utils/process_control.py)

- Добавить глобальную переменную `_current_worker_type: str | None` (`"api"` | `"browser"` | `None`).
- В `start_worker(target_fn, args=(), worker_type=None)`:
  - принять опциональный аргумент `worker_type` (по умолчанию `"browser"` для обратной совместимости);
  - при успешном запуске процесса записывать `_current_worker_type = worker_type`.
- В `stop_worker()` после завершения процесса обнулять `_current_worker_type`.
- Добавить функцию `get_current_worker_type() -> str | None`, возвращающую текущий тип или `None`, если воркер не запущен.

### 2. [main.py](main.py)

- При вызове API-воркеров: `process_control.start_worker(worker, (settings,), worker_type="api")`.
- При вызове браузерных воркеров: `process_control.start_worker(..., worker_type="browser")`.

### 3. [ui/hotkeys.py](ui/hotkeys.py)

- В `on_esc_stop_worker()` в начале: если `process_control.get_current_worker_type() == "api"`, выйти без вызова `stop_worker()` (ничего не печатать — Esc просто игнорируется в API-режиме).
- Иначе вызывать `process_control.stop_worker()` как сейчас.

### 4. [ui/console_menu.py](ui/console_menu.py)

- В вызове `process_control.start_worker(...)` добавить `worker_type="browser"` (там только браузерная генерация).

### 5. [utils/process_manager.py](utils/process_manager.py) (опционально)

- При вызове `process_control.start_worker(...)` передать `worker_type="browser"` для единообразия (используется в тестах).

## Поведение после изменений

| Режим генерации           | Esc                                                                                            |
| ------------------------- | ---------------------------------------------------------------------------------------------- |
| API-воркер запущен        | Не обрабатывается (программа не реагирует, пользователь может использовать Esc в других окнах) |
| Браузерный воркер запущен | Жёсткая остановка воркера (как сейчас)                                                         |
| Воркер не запущен         | `stop_worker()` выведет «Воркер не запущен» (как сейчас)                                       |

Ctrl+Esc (убить консоль) не меняется и работает всегда.

## Документация и подсказки

- Обновить текст в консоли/README, где написано «Esc — остановка»: уточнить, что в API-режиме Esc не останавливает (например в [main.py](main.py) строка 105, [ui/console.py](ui/console.py), сообщения в режимах в `sites/aistudio/mode_*_api.py`). Это можно сделать в том же таске или отдельно мелким правками.
