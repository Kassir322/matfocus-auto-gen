# Контракт агентского интерфейса

Приложение поддерживает только API-режим `multiformat_with_refs`.

## Команды

```powershell
python main.py agent-plan --prompts data\prompts.txt --start 1 --end 10 --output-base-dir "C:\путь\сгенерированные изображения" --json
python main.py agent-run-api --prompts data\prompts.txt --start 1 --end 10 --output-base-dir "C:\путь\сгенерированные изображения" --json
```

Обязательные аргументы: `--prompts`, `--output-base-dir`. Параметр `--mode`
не поддерживается. Дополнительно доступны `--style-ref`, `--no-style-ref`,
`--image-size`, размеры сторон, `--project-name`, `--no-log-prompts` и
`--background transparent|opaque|auto`.

`agent-plan --json` не вызывает API и возвращает план, размеры, провайдеры и
сводку референсов. `agent-run-api --json` возвращает итог запуска одним JSON.

Перед запуском агент обязан выполнять `agent-plan`, если пользователь явно не
попросил пропустить проверку.

## Фон изображения

`--background transparent` передаёт настоящий параметр Images API
`background="transparent"` и `output_format="png"` при создании изображения,
редактировании по одному референсу и редактировании по нескольким референсам.
Текст промпта сам по себе не заменяет этот параметр. При `opaque` или `auto`
передаётся выбранное значение. Без флага прежний запрос не меняется.

Параметр доступен только для ChatGPT: `API_PROVIDER` и
`API_PROVIDER_WITH_REFS` должны быть `chatgpt`. Неподдерживаемый провайдер
отклоняется до запроса, параметр не игнорируется. Значение применяется только
в памяти текущей команды; `data/settings.json` не изменяется. План и итог
содержат `image_background`; журнал запроса содержит `background`.

```powershell
python main.py agent-plan --prompts "C:\project\prompts.txt" --start 1 --end 1 --output-base-dir "C:\project\images" --no-style-ref --background transparent --json
python main.py agent-run-api --prompts "C:\project\prompts.txt" --start 1 --end 1 --output-base-dir "C:\project\images" --no-style-ref --background transparent --json
```

Поддержка параметра сверена 29 октября 2026 с официальными схемами
[создания изображения](https://developers.openai.com/api/reference/python/resources/images/methods/generate)
и [редактирования изображения](https://developers.openai.com/api/reference/resources/images/methods/edit).
Схема указывает прозрачность у `gpt-image-2.5-sunburst` и требует PNG либо WebP.
Проверка передачи параметра не доказывает качество конкретного результата:
после генерации нужно отдельно проверить настоящий альфа-канал, а не
нарисованную шахматную подложку. Программа не удаляет фон и не изменяет
полученный файл после ответа API.
