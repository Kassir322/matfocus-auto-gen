# AGENTS.md

## Назначение

Репозиторий содержит API-приложение для пакетной генерации изображений
карточек. Единственный поддерживаемый формат — `multiformat_with_refs`.

## Актуальная архитектура

- Точка входа: `main.py`.
- Машинный интерфейс: `utils/agent_cli.py`; контракт —
  `docs/reference/AGENT_CLI.md`.
- Меню: `ui/console_menu.py`.
- Запуск: `utils/generation_runner.py`.
- Настройки: `utils/settings_store.py`, локальный `data/settings.json` и
  образец `data/settings.example.json`.
- API-реализация: `sites/aistudio/mode_multiformat_with_refs_api.py`.

Программа работает только через API.

## Источники истины

При конфликте сведений используйте следующий порядок:

1. Работающий код в корне репозитория.
2. `docs/reference/AGENT_CLI.md` для машинных команд.
3. Остальные актуальные справочники в `docs/reference/`.
4. `docs/PROJECT_STATUS.md` для истории и ближайших планов.
5. `README.md` и `MANUAL.md` для краткого запуска.

## Важные файлы

- Локальные настройки: `data/settings.json`; образец: `data/settings.example.json`.
- Журналы запусков: `logs/`.
- Результаты: `generated_images/`.
- Журнал развития: `docs/PROJECT_STATUS.md`.
- Контракт машинного интерфейса: `docs/reference/AGENT_CLI.md`.

## Правила работы

- Сохраняйте функцию единственного API-режима; не добавляйте параллельные
  слои настроек или управления процессами.
- Для агентского запуска используйте `agent-plan`, затем `agent-run-api`.
- Передавайте `--output-base-dir`; для проектов используйте папку
  `...\Рабочие файлы\сгенерированные изображения`.
- Отсутствие контентного референса допустимо.
- Не изменяйте пользовательские данные в `data/`, результаты и журналы без
  явного запроса.
- После каждого содержательного изменения кода, документации или планов
  обновляйте `docs/PROJECT_STATUS.md`: состояние, планы и историю.
- При изменении команд, JSON-контракта или формата промптов обновляйте
  `docs/reference/AGENT_CLI.md`.

## Проверка

Предпочитайте целевые проверки актуального API-контракта.

## Первое чтение

1. `main.py`
2. `utils/agent_cli.py`
3. `utils/generation_runner.py`
4. `sites/aistudio/mode_multiformat_with_refs_api.py`
5. `docs/PROJECT_STATUS.md`
