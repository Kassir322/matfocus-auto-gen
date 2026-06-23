# Логирование v2

Актуальные правила логирования для текущего v2 runtime.

---

## 1. Два канала вывода

| Канал | Назначение |
| --- | --- |
| Файл в `logs/` | Полные шаги, теги, предупреждения и ошибки |
| Консоль | Только основные сообщения для пользователя |

Подробности остаются в файле. Консоль показывает только минимум.

---

## 2. Имя файла лога

Используется формат:

```text
logs/auto-gen_YYYY-MM-DD_HH-MM-SS.log
```

Пример:

```text
logs/auto-gen_2026-04-23_15-10-05.log
```

Важно:

- в текущей реализации browser-режимы создают лог-файл на запуск `run_mode()`;
- это значит, что за один lifetime процесса программы может появиться несколько файлов логов;
- это отличается от более старой формулировки “один лог на запуск всей программы”.

---

## 3. Консоль

В консоль выводятся:

- старт генерации;
- прогресс;
- завершение;
- блокирующие ошибки старта;
- сообщения об остановке.

Актуальный формат прогресса browser-режимов:

```text
Генерация X/Y из Z
```

Где:

- `X` — число успешных сохранений;
- `Y` — число уже выполненных попыток;
- `Z` — общее плановое число генераций/изображений.

---

## 4. Файл: теги

Используются теги:

- `[PLAN]`
- `[CARD]`
- `[PAIR]`
- `[SIDE]`
- `[GEN]`
- `[OK]`
- `[WARN]`
- `[ERROR]`
- `[REF]`
- `[STYLE_REF]`
- `[CONTENT_REF]`
- `[PROMPT_RAW_BEGIN]` / `[PROMPT_RAW_END]`
- `[PROMPT_SENT_BEGIN]` / `[PROMPT_SENT_END]`
- `[PROMPT_LENGTHS]`
- `[CHECK]`
- `[SUMMARY]`

Все строки пишутся с timestamp в начале.

Пример:

```text
2026-04-23 15:10:05 [PLAN] Режим: standard. Карточек: 10, генераций: 24
2026-04-23 15:10:06 [CARD] Карточка 1
2026-04-23 15:10:07 [GEN] Генерация: Карточка 1 - генерация 1
2026-04-23 15:10:31 [OK] Файл сохранён: Карточка_1_лицевая_промпт_1.png
2026-04-23 15:10:32 [WARN] Таймаут ожидания изображения: карточка 1, генерация 2
2026-04-23 15:11:20 [SUMMARY] Карточек: 10, генераций: 24/24
```

---

## 5. Что сейчас логируется фактически

Browser-режимы уже пишут:

- план запуска;
- файл промптов;
- старт карточек / пар / сторон;
- начало одной генерации;
- сохранение файла;
- предупреждения по пустым промптам, не найденным референсам и таймаутам ожидания;
- итоговую сводку.

API-режимы ведут отдельные свои логи по тому же общему принципу.

API runs also log prompt text when `API_LOG_PROMPTS=true`:

```text
[PROMPT_RAW_BEGIN] card=1 side=лицо pair=1
...
[PROMPT_RAW_END]
[PROMPT_SENT_BEGIN] card=1 side=лицо pair=1 provider=chatgpt model=gpt-image-2 reference_mode=style+content
...
[PROMPT_SENT_END]
```

- `PROMPT_RAW` is the prompt text parsed from the prompts file.
- `PROMPT_SENT` is the exact provider prompt after aspect-ratio prefix and style/content reference role instructions.
- When prompt logging is disabled with `API_LOG_PROMPTS=false` or `--no-log-prompts`, the log writes `[PROMPT_LENGTHS]` only.
- Logs must never include API keys, Authorization headers, file handles, base64 data, or image bytes.

---

## 6. Реализация

Текущий активный low-level слой для записи строки:

- `utils/log_writer.py`

Формат строки:

```text
YYYY-MM-DD HH:MM:SS <message>
```

Где `message` уже содержит тег, например:

```text
[PLAN] Режим: multiformat. Карточек: 5, пар: 10, изображений: 20
```

Legacy-заметка:

- `utils/logger.py` не является частью активного v2-контракта логирования;
- это compatibility/legacy-слой, не используемый основным runtime.
