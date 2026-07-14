# MatFocus API Image Generator

Программа пакетно генерирует изображения карточек через API. Поддерживается
только `multiformat_with_refs`: лицо и оборот, контентные референсы и
необязательный общий стилевой референс.

## Запуск

```powershell
pip install -r requirements.txt
python main.py
```

Команда открывает API-меню: выбор промптов, диапазона карточек, настроек,
папки результатов и стилевого референса. Остановка — `Ctrl+C`.

Для машинного запуска сначала создайте план, затем выполните генерацию:

```powershell
python main.py agent-plan --prompts data\prompts.txt --output-base-dir "C:\путь\сгенерированные изображения" --json
python main.py agent-run-api --prompts data\prompts.txt --output-base-dir "C:\путь\сгенерированные изображения" --json
```

Обязательны `--prompts` и `--output-base-dir`; параметр `--mode` отсутствует.
Ключи задаются через `GOOGLE_API_KEY` и `OPENAI_API_KEY` либо локальный `.env`.

## Документация

- `MANUAL.md` — краткая работа с меню.
- `version2/reference/AGENT_CLI.md` — контракт машинных команд.
- `version2/reference/REFERENCES_format.md` — референсы.
- `docs/PROJECT_STATUS.md` — состояние, планы и история развития.
