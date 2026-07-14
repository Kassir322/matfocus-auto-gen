# MatFocus API Image Generator

Программа пакетно генерирует изображения для карточек через API. Поддерживается
только формат `multiformat_with_refs`: лицо и оборот карточки, контентные
референсы и общий стилевой референс.

## Запуск

```powershell
pip install -r requirements.txt
python main.py
```

Агентский запуск:

```powershell
python main.py agent-plan --prompts data\prompts.txt --output-base-dir "C:\путь\сгенерированные изображения" --json
python main.py agent-run-api --prompts data\prompts.txt --output-base-dir "C:\путь\сгенерированные изображения" --json
```

`--mode` больше не поддерживается. Остановка интерактивного запуска — `Ctrl+C`.

## Структура

- `sites/aistudio/mode_multiformat_with_refs_api.py` — единственный режим.
- `utils/agent_cli.py` — машинные команды.
- `ui/console_menu.py` — API-меню.
- `data/images/лицо` и `data/images/оборот` — контентные референсы.

Ключи задаются через `GOOGLE_API_KEY` и `OPENAI_API_KEY` либо локальный `.env`.
