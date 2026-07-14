# Настройки API-генератора

Настройки хранятся в `data/settings.json`. Секреты не записывайте в этот файл:
используйте `GOOGLE_API_KEY`, `OPENAI_API_KEY` или локальный `.env`.

## Основные параметры

| Параметр | Назначение |
| --- | --- |
| `PROMPTS_FILE` | Путь к файлу промптов. |
| `START_FROM_CARD`, `END_CARD` | Диапазон карточек. |
| `OUTPUT_BASE_DIR` | Базовая папка результатов. |
| `OUTPUT_PROJECT_NAME` | Суффикс папки запуска. |
| `FACE_ASPECT_RATIO`, `BACK_ASPECT_RATIO` | Соотношения сторон лица и оборота. |
| `API_IMAGE_SIZE` | Размер изображения для API. |
| `API_STYLE_REFERENCE_IMAGE` | Путь к общему стилевому референсу. |
| `API_LOG_PROMPTS` | Запись исходного и отправленного промпта в журнал. |
| `API_TIMEOUT` | Ожидание ответа API в секундах. |

## Провайдеры и параллельность

- `API_PROVIDER` используется без референса.
- `API_PROVIDER_WITH_REFS` используется при контентном или стилевом референсе.
- Модели задаются `API_MODEL`, `API_MODEL_WITH_REFS` и `API_MODEL_CHATGPT`.
- Для ChatGPT доступны `API_CHATGPT_QUALITY`, параметры параллельности и
  лимитов `API_CHATGPT_*`.

Параметры команд `agent-plan` и `agent-run-api` имеют приоритет только в
текущем запуске и не изменяют `data/settings.json`.
