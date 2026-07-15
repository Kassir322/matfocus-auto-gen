# Контракт агентского интерфейса

Приложение поддерживает только API-режим `multiformat_with_refs`.

## Команды

```powershell
python main.py agent-plan --prompts data\prompts.txt --start 1 --end 10 --output-base-dir "C:\путь\сгенерированные изображения" --json
python main.py agent-run-api --prompts data\prompts.txt --start 1 --end 10 --output-base-dir "C:\путь\сгенерированные изображения" --json
```

Обязательные аргументы: `--prompts`, `--output-base-dir`. Параметр `--mode`
не поддерживается. Дополнительно доступны `--style-ref`, `--no-style-ref`,
`--image-size`, размеры сторон, `--project-name` и `--no-log-prompts`.

`agent-plan --json` не вызывает API и возвращает план, размеры, провайдеры и
сводку референсов. `agent-run-api --json` возвращает итог запуска одним JSON.

Перед запуском агент обязан выполнять `agent-plan`, если пользователь явно не
попросил пропустить проверку.
