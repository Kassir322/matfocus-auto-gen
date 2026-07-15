# Интеграция API

Режим `multiformat_with_refs` использует `API_PROVIDER` для задач без
референса и `API_PROVIDER_WITH_REFS` для задач со стилевым или контентным
референсом. Поддерживаются `nanobanana` и `chatgpt`.

Ключи читаются из `GOOGLE_API_KEY` и `OPENAI_API_KEY` либо локального `.env`.
Они не записываются в `data/settings.json`.
