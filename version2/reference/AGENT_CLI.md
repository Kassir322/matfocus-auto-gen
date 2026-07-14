# Codex Agent CLI Contract

This document is the source of truth for Codex-facing generation workflows in the active v2 runtime.
Keep it updated together with any change to `utils/agent_cli.py`, API-mode return values, prompt formats, or agent-facing behavior.

## Preferred Workflow

- Prefer `multiformat_with_refs` for Codex-driven product work and style probes.
- Use `standard` only for quick isolated square-image experiments.
- Use `multiformat` only when the user explicitly wants face/back prompts without reference lookup.
- Codex agents may run only API generation modes through this contract.
- Browser generation is forbidden for Codex agents, even if `data/settings.json` currently says `GENERATION_METHOD=browser` or the user asks to use the agent workflow with browser automation.
- Do not drive hotkeys, console menu input, pyautogui, or browser automation from Codex. Use the agent CLI commands.
- `utils/agent_cli.py` must force `GENERATION_METHOD=api` and route only to `sites/aistudio/*_api.py` modules.
- Run `agent-plan --json` before generation unless the user explicitly asks to skip planning.
- Agent runs must stay isolated from `data/settings.json`: command-line overrides are applied in memory and must not advance `START_FROM_CARD`.
- API keys are not stored in `data/settings.json`. Use `OPENAI_API_KEY` for ChatGPT/OpenAI and `GOOGLE_API_KEY` for nanobanana/Google; a local root `.env` may define the same variables and is not committed.
- Non-agent output defaults to `generated_images/<timestamp>_<project>`.
- Agent commands must pass `--output-base-dir VALUE`. The output folder is then named `<VALUE>/<timestamp>_<project>`. For project work, Codex agents should pass the ready base folder `...\Рабочие файлы\сгенерированные изображения`.
- The project name comes from `OUTPUT_PROJECT_NAME` in `data/settings.json`, or from the agent's `--project-name` override.
- `multiformat_with_refs` can use one global style reference in addition to per-card content references.
- Codex agents should pass the style reference explicitly with `--style-ref PATH` or disable it with `--no-style-ref`; do not rely on machine-local defaults for project work.
- API prompt logging is enabled by default and writes the exact provider prompt to the run log, not to the JSON result.

## Commands

Plan a batch without API calls:

```powershell
python main.py agent-plan --mode multiformat_with_refs --prompts data\style_probe.txt --start 1 --end 1 --output-base-dir "C:\path\to\Рабочие файлы\сгенерированные изображения" --json
```

Run a batch synchronously through API:

```powershell
python main.py agent-run-api --mode multiformat_with_refs --prompts data\style_probe.txt --start 1 --end 1 --output-base-dir "C:\path\to\Рабочие файлы\сгенерированные изображения" --json
```

Optional API request size overrides:

```powershell
python main.py agent-run-api --mode multiformat_with_refs --prompts data\style_probe.txt --start 1 --end 1 --output-base-dir "C:\path\to\Рабочие файлы\сгенерированные изображения" --face-image-size 1024x1024 --back-image-size 1536x1024 --json
```

- `--image-size VALUE` applies one API request size to the whole run.
- `--face-image-size VALUE` applies only to `лицо` tasks.
- `--back-image-size VALUE` applies only to `оборот` tasks.
- For `multiformat` and `multiformat_with_refs`, side-specific values take priority over `--image-size`, which takes priority over `API_IMAGE_SIZE`.
- The program does not whitelist ChatGPT size values; any non-empty value is passed to the provider API as the request `size`.
- These flags control only the size parameter sent to the provider API. They must not trigger local resize, crop, padding, blur-fill, canvas expansion, or any other post-processing of the returned image file.

Optional project-name override:

```powershell
python main.py agent-run-api --mode multiformat_with_refs --prompts data\style_probe.txt --start 1 --end 1 --output-base-dir "C:\path\to\Рабочие файлы\сгенерированные изображения" --project-name countries --json
```

- `--project-name VALUE` overrides `OUTPUT_PROJECT_NAME` in memory for the current agent command only.
- The effective project name is sanitized for Windows folder names and used in `<output-base-dir>/YYYY-MM-DD_HH-MM-SS_<project>`.
- Codex agents should determine `VALUE` from the user's project context, not from the prompts `.txt` filename. If the source project path ends with a generic work folder such as `Рабочие файлы`, use its parent folder name; for example `O:\Yandex.Disk\0РГАНИЗОВАННЫЕ\история древнего мира\Рабочие файлы` should use `история древнего мира`.

Required agent output base directory:

```powershell
python main.py agent-run-api --mode multiformat_with_refs --prompts data\style_probe.txt --start 1 --end 1 --output-base-dir "C:\path\to\Рабочие файлы\сгенерированные изображения" --json
```

- `--output-base-dir VALUE` overrides `OUTPUT_BASE_DIR` in memory for the current agent command only.
- `VALUE` is the ready base output directory. The runtime creates a timestamped wave folder inside it.
- `agent-plan` and `agent-run-api` both return a machine error when `--output-base-dir` is omitted.
- `OUTPUT_BASE_DIR` defaults to `generated_images` for non-agent/runtime settings.

Optional global style reference override:

```powershell
python main.py agent-run-api --mode multiformat_with_refs --prompts data\style_probe.txt --start 1 --end 1 --output-base-dir "C:\path\to\Рабочие файлы\сгенерированные изображения" --style-ref data\style_refs\default.png --json
```

- `--style-ref PATH` overrides `API_STYLE_REFERENCE_IMAGE` in memory for the current agent command only.
- If `--style-ref` is omitted, `multiformat_with_refs` uses `API_STYLE_REFERENCE_IMAGE` from settings.
- `--no-style-ref` disables any configured style reference for the current command only.
- `--style-ref` and `--no-style-ref` are valid only with `multiformat_with_refs`.
- Style references require `API_PROVIDER_WITH_REFS=chatgpt`; invalid settings fail before API calls.

Optional prompt logging override:

```powershell
python main.py agent-run-api --mode multiformat_with_refs --prompts data\style_probe.txt --start 1 --end 1 --output-base-dir "C:\path\to\Рабочие файлы\сгенерированные изображения" --no-log-prompts --json
```

- By default, `API_LOG_PROMPTS=true` logs raw prompts and exact provider prompts to the run log.
- `--no-log-prompts` disables full prompt text logging for the current command and logs prompt lengths only.
- Prompt text is written only to the log file, not to the JSON result.

## ChatGPT API Rate Profile

Current local settings are tuned for OpenAI Tier 3 on `gpt-image-2`:

- `API_CHATGPT_RATE_LIMIT_PROFILE=tier3`
- `API_CHATGPT_MAX_WORKERS=50`
- `API_CHATGPT_RATE_LIMIT_IPM=50`
- `API_CHATGPT_RATE_LIMIT_WINDOW_SECONDS=60`
- `API_CHATGPT_RATE_LIMIT_TPM=800000`
- `API_CHATGPT_MONTHLY_USAGE_LIMIT_USD=1000`

The runtime limiter uses the IPM/window values to gate launches. TPM and monthly usage limit are stored for visibility; they are not a hard runtime stop.

## Configuration Portability

- `data/settings.json` is a tracked safe defaults file and must not contain `API_KEY`, `API_KEY_NANOBANANA`, or `API_KEY_CHATGPT`.
- Agent-specific paths and ranges must be passed explicitly: `--prompts`, `--output-base-dir`, `--style-ref` or `--no-style-ref`, `--start`, `--end`, `--project-name`, `--face-image-size`, and `--back-image-size`.
- Relative app paths are resolved from the repository root, not from the current PowerShell directory.
- `data/images/<side>/` remains the content-reference lookup location.

Supported modes:

```text
standard
multiformat
multiformat_with_refs
```

## JSON Result Contract

`agent-plan --json` returns a single JSON object with:

- `ok`
- `command`
- `site`
- `method`
- `mode`
- `prompts_file`
- `start_card`
- `end_card`
- `tasks_count`
- `plan`
- provider/model fields
- `image_size`
- `face_image_size`
- `back_image_size`
- `output_base_dir`
- `output_dir`
- `project_name`
- for `multiformat_with_refs`: `references_summary`
- for `multiformat_with_refs`: top-level reference summary fields (`style_reference_path`, `style_reference_enabled`, `prompt_logging_enabled`, `content_refs_found`, `content_refs_missing`, `tasks_with_style_ref`, `tasks_with_content_ref`, `tasks_with_both_refs`)
- `errors` when `ok=false`

`agent-run-api --json` returns a single JSON object with:

- `ok`
- `command`
- `mode`
- `planned`
- `succeeded`
- `failed`
- `output_dir`
- `output_base_dir`
- `project_name`
- `log_file`
- `images`
- `errors`
- for `multiformat_with_refs`: `references_summary`
- optional `console_output`

If the process exits nonzero but prints JSON, parse the JSON first and report `errors`.

## Preferred Prompt Format

For `multiformat_with_refs`, prompt files should follow the same line format and style preamble pattern as `data/countries_clear_nanobanana_prompts.txt`.

Line format:

```text
Карточка N лицо Card Name - Промпт M: prompt text
Карточка N оборот Card Name - Промпт M: prompt text
```

Preferred style preamble:

```text
Modern semi-flat polished vector illustration for an educational geography card game. Clean friendly shapes, soft volume, gentle shadows, subtle gradients, neat contours, simplified details, readable silhouettes, warm accents, pleasant stylish colors, no harsh neon colors.
```

Typical face-side composition:

```text
A calm airy composition inspired by <subject>: upper and left areas stay light, quiet, and open with a soft atmospheric background. All main objects form one compact lower-right cluster: <object 1>, <object 2>, and <object 3>. The objects are large, readable, and balanced like a polished cutout illustration.
```

Typical back-side composition:

```text
A panoramic country scene inspired by <subject>, centered on a large recognizable view of <main landmark or scene>. The main landmark sits in the foreground or middle ground, with simplified background elements receding into soft perspective.
```

Required negative tail for this style family:

```text
No text, no readable words, no labels, no signs, no letters, no flags, no UI elements, no logos, no arrows, no photorealism, no 3D render, no painterly texture, no clutter.
```

For style probes, create a small number of variants that change only one or two style/composition variables at a time. Keep the subject and prompt family consistent so the user can compare style rather than content.

## Reference Images

`multiformat_with_refs` has two reference roles in API mode:

- **Style reference**: one global image for visual language only. It controls palette, line quality, detail level, shading, texture, contrast, and overall finish. It must not be treated as subject/layout/content.
- **Content reference**: per-card/per-side images used to preserve a face, object, shape, structure, landmark, or other recognizable subject detail.

The global style reference is configured with `--style-ref PATH` or `API_STYLE_REFERENCE_IMAGE`.

Content references still use the existing lookup folders:

```text
data/images/<side>/
```

Missing content references are valid. The mode should continue and generate without a content reference when no matching image is found.

When both style and content references are available for a ChatGPT task, the OpenAI edit request receives image 1 as the style reference and image 2 as the content reference. The generated provider prompt includes explicit role instructions for those images.

Prompt logs use this block shape when full prompt logging is enabled:

```text
[PROMPT_RAW_BEGIN] card=1 side=лицо pair=1
...
[PROMPT_RAW_END]
[PROMPT_SENT_BEGIN] card=1 side=лицо pair=1 provider=chatgpt model=gpt-image-2 reference_mode=style+content
...
[PROMPT_SENT_END]
```

## Documentation Maintenance

When changing agent CLI behavior:

- update this file;
- update `version2/planning/V2_AUDIT_TRACKER.md`;
- update the `auto-gen-api-agent` Codex skill if workflow, commands, result fields, or prompt defaults changed;
- add or update focused tests around `utils/agent_cli.py` and API-mode result behavior.
- preserve the rule that Codex/agent execution cannot start browser generation.
