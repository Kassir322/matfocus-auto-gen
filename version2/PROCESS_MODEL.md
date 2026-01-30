# Модель процессов v2

Описание архитектуры управления процессами в v2: главный процесс, воркер и механизм жёсткой остановки.

---

## 1. Проблема v1

В v1 остановка работала через `stop_event`:

```python
# v1 - мягкая остановка
stop_event = multiprocessing.Event()

# В воркере периодически проверялось:
if stop_event.is_set():
    return  # Выход из функции
```

**Проблемы**:

- Проверка выполнялась не везде
- Воркер продолжал работу между проверками
- При длинном `time.sleep()` остановка задерживалась на секунды
- Иногда программа вообще не останавливалась

---

## 2. Решение v2: Жёсткий стоп

В v2 используется **принудительное завершение процесса**:

```python
# v2 - жёсткий стоп
worker_process.terminate()  # Мгновенное завершение
```

**Преимущества**:

- Мгновенная остановка (< 100ms)
- Не требует проверок внутри воркера
- Работает всегда, независимо от состояния воркера

---

## 3. Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                   ГЛАВНЫЙ ПРОЦЕСС                       │
│                                                         │
│  ┌─────────────────┐     ┌─────────────────────────┐   │
│  │  Console Menu   │────>│   Process Manager       │   │
│  │  (интерфейс)    │     │                         │   │
│  └─────────────────┘     │  - start_automation()   │   │
│                          │  - stop_automation()    │   │
│                          │  - worker_process       │   │
│  ┌─────────────────┐     └───────────┬─────────────┘   │
│  │ Hotkey Manager  │                 │                 │
│  │                 │                 │                 │
│  │ Esc → terminate │─────────────────┘                 │
│  └─────────────────┘                                   │
└─────────────────────────────────────────────────────────┘
                           │
                           │ multiprocessing.Process
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   ВОРКЕР ПРОЦЕСС                        │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  automation_worker(tasks, settings, coords, ...) │   │
│  │                                                   │   │
│  │  Цикл по карточкам:                              │   │
│  │    - Клики                                        │   │
│  │    - Ввод промптов                               │   │
│  │    - Ожидание генерации                          │   │
│  │    - Сохранение файлов                           │   │
│  │                                                   │   │
│  │  (НЕТ проверок stop_event!)                      │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Запуск воркера

```python
from multiprocessing import Process

def start_automation(tasks, settings, coordinates, relative_movements):
    """
    Запускает воркер-процесс для выполнения автоматизации.
    """
    global worker_process

    # Создаём новый процесс
    worker_process = Process(
        target=automation_worker,
        args=(tasks, settings, coordinates, relative_movements)
    )

    # Запускаем
    worker_process.start()

    print(f"[ПРОЦЕСС] Воркер запущен (PID: {worker_process.pid})")
```

---

## 5. Остановка воркера

```python
def stop_automation():
    """
    Принудительно завершает воркер-процесс.
    """
    global worker_process

    if worker_process is None:
        print("[ПРОЦЕСС] Воркер не запущен")
        return

    if not worker_process.is_alive():
        print("[ПРОЦЕСС] Воркер уже завершён")
        return

    # ЖЁСТКИЙ СТОП
    print(f"[ПРОЦЕСС] Завершение воркера (PID: {worker_process.pid})...")
    worker_process.terminate()

    # Ждём завершения (максимум 1 сек)
    worker_process.join(timeout=1.0)

    if worker_process.is_alive():
        # Если не завершился — убиваем
        worker_process.kill()
        worker_process.join(timeout=0.5)

    print("[ПРОЦЕСС] ✓ Воркер завершён")
    worker_process = None
```

---

## 6. Обработчик Esc

```python
import keyboard

def on_esc_pressed():
    """
    Обработчик нажатия Esc — мгновенная остановка.
    """
    print("\n🛑 Esc нажат — остановка автоматизации...")
    stop_automation()

# Регистрация горячей клавиши
keyboard.add_hotkey('esc', on_esc_pressed)
```

---

## 7. Состояния процесса

```
[НЕ ЗАПУЩЕН] ──start_automation()──> [РАБОТАЕТ]
                                          │
                                          │ (автоматическое завершение
                                          │  или Esc)
                                          ▼
                                     [ЗАВЕРШЁН]
```

### Проверка состояния

```python
def get_worker_status():
    """
    Возвращает текущее состояние воркера.
    """
    if worker_process is None:
        return "not_started"

    if worker_process.is_alive():
        return "running"

    exit_code = worker_process.exitcode
    if exit_code == 0:
        return "finished_ok"
    elif exit_code == -15:  # SIGTERM
        return "terminated"
    elif exit_code == -9:   # SIGKILL
        return "killed"
    else:
        return f"finished_error_{exit_code}"
```

---

## 8. Что происходит при terminate()

### 8.1. На уровне ОС

```
terminate() → SIGTERM → Процесс завершается
```

### 8.2. Последствия

| Аспект                    | Что происходит            |
| ------------------------- | ------------------------- |
| Текущий клик              | Прерывается               |
| Незавершённое ожидание    | Прерывается               |
| Открытые файлы            | Закрываются (ОС)          |
| Буфер обмена              | Может остаться изменённым |
| Браузер                   | Остаётся открытым         |
| Несохранённое изображение | Не сохраняется            |

### 8.3. Что НЕ восстанавливается

- Буфер обмена (может содержать имя файла или промпт)
- Позиция курсора
- Фокус окна

---

## 9. Повторный запуск

```python
def start_automation(...):
    global worker_process

    # Проверяем, не запущен ли уже воркер
    if worker_process is not None and worker_process.is_alive():
        print("[ПРОЦЕСС] ⚠️ Воркер уже запущен!")
        print("[ПРОЦЕСС] Сначала остановите его (Esc)")
        return False

    # Создаём и запускаем новый процесс
    worker_process = Process(...)
    worker_process.start()
    return True
```

---

## 10. Логирование процесса

```python
import logging

def automation_worker(tasks, settings, coordinates, relative_movements):
    """
    Основная функция воркера.
    """
    # Настройка логгера для воркера
    logger = logging.getLogger("worker")

    logger.info(f"[WORKER] Запуск (PID: {os.getpid()})")
    logger.info(f"[WORKER] Задач: {len(tasks)}")

    try:
        for task in tasks:
            process_task(task, settings, coordinates, relative_movements)

        logger.info("[WORKER] ✓ Все задачи выполнены")

    except Exception as e:
        logger.error(f"[WORKER] ✗ Ошибка: {e}")

    logger.info("[WORKER] Завершение")
```

---

## 11. Отличия от v1

| Аспект                  | v1                    | v2            |
| ----------------------- | --------------------- | ------------- |
| Механизм остановки      | `stop_event.is_set()` | `terminate()` |
| Время остановки         | Секунды               | Мгновенно     |
| Требуется код в воркере | Да (проверки)         | Нет           |
| Graceful shutdown       | Да                    | Нет           |
| Гарантия остановки      | Нет                   | Да            |
| Горячая клавиша         | `Ctrl+Shift+Q`        | `Esc`         |

---

## 12. Ограничения

### 12.1. Нет graceful shutdown

Воркер не может:

- Сохранить промежуточные результаты
- Вывести финальную статистику
- Восстановить буфер обмена

### 12.2. Возможные артефакты

После terminate():

- Открытый диалог сохранения в браузере
- Курсор в неожиданной позиции
- Буфер обмена с промптом/именем файла

### 12.3. Решение

Перед повторным запуском:

1. Закройте открытые диалоги в браузере
2. Нажмите Esc в браузере (сбросить модальные окна)
3. Настройте окно (`Ctrl+Shift+V`)
