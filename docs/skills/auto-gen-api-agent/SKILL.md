---
name: auto-gen-api-agent
description: Use when Codex needs to run, plan, or inspect small API-based image generation batches through the O:\git\matfocus-auto-gen project, especially style-probe workflows where Codex creates or selects a prompts .txt file, calls `python main.py agent-plan` or `python main.py agent-run-api`, reads the JSON result, and reports generated image paths/logs without manually using hotkeys or the console menu.
---

# Auto Gen API Agent

Use this skill to operate the `auto-gen` application's machine-readable API CLI. The goal is to let Codex run small style-probe generations, collect results, and help the user choose/fix visual direction before large production runs.

The active auto-gen repo is `O:\git\matfocus-auto-gen`. The old `O:\Yandex.Disk\auto-gen` checkout is obsolete and must not be used for running commands, reading current app docs, or editing the application.

The repo documentation for this workflow is `O:\git\matfocus-auto-gen\version2\reference\AGENT_CLI.md`. Read it when command behavior, prompt format, JSON fields, or defaults matter.

## Core Rules

- Work in the active repo: `O:\git\matfocus-auto-gen`.
- Keep a duplicate of this skill's `SKILL.md` inside the program workspace when working on the skill or its workflow, normally under `O:\git\matfocus-auto-gen\docs\skills\auto-gen-api-agent\SKILL.md` unless the repo already uses another explicit skill-mirror path.
- Before changing or relying on duplicated skill instructions, compare the skill-folder copy and the program-workspace copy by modification time and content. Treat the more intentionally updated copy as authoritative; if unclear, ask the user instead of overwriting either direction.
- After updating the authoritative copy, synchronize the other copy so both contain the same current instructions. Sometimes the program-workspace copy is the newest source and must be copied back into `C:\Users\kas\.codex\skills\auto-gen-api-agent\SKILL.md`; sometimes the skill-folder copy is newest and must be copied into the program workspace.
- Use only the agent CLI for this workflow; do not drive hotkeys, console menu input, or browser automation.
- Run only API generation modes. Browser generation is forbidden for this skill, even if `data/settings.json` uses `GENERATION_METHOD=browser` or the user mentions browser automation.
- Never use pyautogui, hotkeys, or the console menu as a workaround for agent generation.
- For long or full `agent-run-api` generation runs, start the process in a separate visible PowerShell window instead of the Codex tool terminal, so the user can close that window to stop generation if needed. Keep using normal synchronous tool calls for `agent-plan` and for very small quick probes when the user clearly expects immediate completion inside the chat.
- Always use `multiformat_with_refs` for generation runs through this skill. Do not switch to `standard` or `multiformat`, even for quick tests, independent samples, or when the user does not provide reference images. Missing references are valid and the runtime will continue without them.
- For consistent style across a batch, use one global style reference with `--style-ref <path>` or `API_STYLE_REFERENCE_IMAGE`. Prefer `O:\git\matfocus-auto-gen\data\style_refs\default.png` when creating a durable local style sample.
- Treat the global style reference as style-only: it should transfer palette, line quality, rendering finish, texture, and detail level, not subject, object layout, or composition.
- Style references are supported only in API `multiformat_with_refs` and require `API_PROVIDER_WITH_REFS=chatgpt`; `agent-plan`/`agent-run-api` should fail before generation if this is not true.
- API prompt logging is on by default. Use `--no-log-prompts` only when the user does not want full raw/sent prompt text in the run log; the log will still keep prompt lengths.
- Follow the prompt line/style pattern from existing parser-compatible examples when creating probe prompts.
- Save new project-specific prompt `.txt` files inside the current product/project workspace, normally under `...\Рабочие файлы\...`, not inside the auto-gen application checkout such as `data\`. Pass that project prompt file to the CLI with `--prompts` as an absolute path when running from the auto-gen repo.
- Prefer small probes: 1-10 images unless the user explicitly asks for more.
- For reference-based face/back card generation, place reference images in the repo data folders before planning or running:
  - face/front references go in `O:\git\matfocus-auto-gen\data\images\лицо`;
  - back/reverse references go in `O:\git\matfocus-auto-gen\data\images\оборот`.
  Use the runtime lookup filename format `{card_number}_{side}.{ext}`, for example `20_лицо.jpg` or `20_оборот.png`. The optional long format is `{side}_{card_number}_{safe_card_name}.{ext}`. Do not rely on source names like `карточка_20_лицо.jpg`: keep them only as human-readable duplicates if useful, but create the runtime lookup filename too. Update any machine-readable generation queue or manifest so `reference_paths` point to these copied files, not to a project scratch folder.
- Content/object references remain separate from the global style reference. When both are used, ChatGPT receives image 1 as the style reference and image 2 as the content reference.
- Treat `data/settings.json` as the API/provider/model/key source. Do not print API keys.
- Do not print full prompts from logs into the chat unless the user explicitly asks for prompt debugging. Never expose API keys, Authorization headers, base64, image bytes, or file handles.
- Agent runs are isolated by design: `agent-run-api` applies overrides in memory and should not change `data/settings.json` or advance `START_FROM_CARD`.
- Agent runs may override API request size with `--image-size`, `--face-image-size`, and `--back-image-size`. Pass the requested size through to the provider API; do not enforce a local whitelist for ChatGPT sizes. These flags control only provider API request size; do not perform local resize, crop, padding, blur-fill, canvas expansion, or other post-processing on returned image files.
- Agent runs must always pass `--output-base-dir`. Use the ready project output folder `...\Рабочие файлы\сгенерированные изображения`; the runtime creates timestamped wave folders inside it. This override is in-memory only and does not edit `data/settings.json`.
- Agent runs should set the output project folder suffix with `--project-name` whenever the user's project context is known; this applies in memory only and does not edit `data/settings.json`. Determine the project name from the chat context or source project directory, not from the prompts `.txt` filename. If a source path ends with a generic folder like `Рабочие файлы`, use the parent folder name; for example `O:\Yandex.Disk\0РГАНИЗОВАННЫЕ\история древнего мира\Рабочие файлы` means project name `история древнего мира`. Without the flag, the runtime uses `OUTPUT_PROJECT_NAME` from settings and writes to `generated_images/YYYY-MM-DD_HH-MM-SS_<project>`.
- Save any prompts file as UTF-8 in the project workspace.
- After a run, parse the final JSON and report `output_dir`, `log_file`, `images`, `succeeded`, `failed`, and `errors`.
- Do not create separate contact sheets, comparison sheets, summary collages, or other derived overview images unless the user explicitly asks for that file. They waste time and tokens in the normal probe workflow. When visual review is needed, show the relevant generated images directly in the chat with Markdown image tags.
- When useful, show or list local generated images in the final response with Markdown image tags using absolute paths. Do not visually inspect, open, compare, describe, rank, or analyze generated images unless the user explicitly asks for image analysis or visual comparison. Exception: when the user asks to find/use reference images and generate from them, visual inspection is required; compare the generated image against the reference and independently assess whether the result successfully preserved the important reference features.
- Do not use Wikipedia or Wikimedia Commons as direct image-download sources for reference images; those downloads are unreliable in this environment. If a reference image is needed, search for another source first, such as OpenStax, NASA, PhyloPic, museum/archive/public-domain collections, official project pages, or a locally created controlled reference when appropriate.

## Workflow

1. Use `multiformat_with_refs` as the mode for every generation run through this skill, even when no reference images are provided. If a user asks for `standard` or `multiformat`, explain that this workflow is locked to `multiformat_with_refs` and continue in `multiformat_with_refs` unless they ask to stop.
2. Create or choose a prompts `.txt` file that matches the existing project format and keep it in the product/project workspace, normally under `...\Рабочие файлы\...`. Do not create project prompt batches inside the auto-gen repo's `data\` folder.
3. If the task needs reference images, look for downloadable non-Wikipedia/non-Wikimedia sources first; do not spend attempts on Wikimedia direct image URLs.
4. For reference-based face/back card generation, copy every selected reference into `data\images\лицо` or `data\images\оборот` according to the side being generated, then update the queue/manifest `reference_paths` to those destination files.
5. Run `agent-plan --json` first unless the user explicitly wants an immediate run.
6. If the plan is valid and the batch is small, run `agent-run-api --json` with `--output-base-dir`. Do not run browser generation.
7. Parse the JSON result. If `ok=false`, summarize `errors` and point to `console_output` or `log_file` if present.
8. Do not inspect generated images by default. Without an explicit user request for analysis, only report run metadata and list/show generated image paths. If the user explicitly asks to analyze, compare, rank, or choose a style, then inspect only the necessary generated images. If the task involves finding/adding reference images and generating from those references, inspect the reference and generated output, compare them, and report an independent success/failure assessment focused on the reference-dependent features.
9. If the user approves a style direction, write the style notes/prompt pattern where the current task expects them. Do not invent a permanent location unless the user asks.

## Style References

- Use `--style-ref <path>` for one batch-wide style reference in API `multiformat_with_refs`.
- Use `--no-style-ref` when `API_STYLE_REFERENCE_IMAGE` is set in `data/settings.json` but the current run should ignore it.
- Use `--no-log-prompts` when full prompt bodies should not be written to the run log. The log still records raw and sent prompt lengths.
- In `agent-plan --json`, check `references_summary` and the top-level style/content counters before running generation.
- In `agent-run-api --json`, prompt bodies are not returned in JSON; they are written only to the run log when prompt logging is enabled.

## Commands

Plan without API calls:

```powershell
python main.py agent-plan --mode multiformat_with_refs --prompts "C:\path\to\Рабочие файлы\style_probe.txt" --start 1 --end 1 --output-base-dir "C:\path\to\Рабочие файлы\сгенерированные изображения" --json
```

Plan with a global style reference:

```powershell
python main.py agent-plan --mode multiformat_with_refs --prompts "C:\path\to\Рабочие файлы\style_probe.txt" --start 1 --end 1 --output-base-dir "C:\path\to\Рабочие файлы\сгенерированные изображения" --style-ref data\style_refs\default.png --json
```

Run synchronously through API:

```powershell
python main.py agent-run-api --mode multiformat_with_refs --prompts "C:\path\to\Рабочие файлы\style_probe.txt" --start 1 --end 1 --output-base-dir "C:\path\to\Рабочие файлы\сгенерированные изображения" --json
```

Run with a global style reference:

```powershell
python main.py agent-run-api --mode multiformat_with_refs --prompts "C:\path\to\Рабочие файлы\style_probe.txt" --start 1 --end 1 --output-base-dir "C:\path\to\Рабочие файлы\сгенерированные изображения" --style-ref data\style_refs\default.png --json
```

Run with full prompt bodies suppressed in the log:

```powershell
python main.py agent-run-api --mode multiformat_with_refs --prompts "C:\path\to\Рабочие файлы\style_probe.txt" --start 1 --end 1 --output-base-dir "C:\path\to\Рабочие файлы\сгенерированные изображения" --style-ref data\style_refs\default.png --no-log-prompts --json
```

Run a long generation in a user-closeable PowerShell window:

```powershell
Start-Process powershell -ArgumentList '-NoExit', '-Command', 'Set-Location "O:\git\matfocus-auto-gen"; python main.py agent-run-api --mode multiformat_with_refs --prompts "C:\path\to\Рабочие файлы\style_probe.txt" --start 1 --end 77 --output-base-dir "C:\path\to\Рабочие файлы\сгенерированные изображения" --project-name "project_name" --json'
```

Run with explicit API request sizes:

```powershell
python main.py agent-run-api --mode multiformat_with_refs --prompts "C:\path\to\Рабочие файлы\style_probe.txt" --start 1 --end 1 --output-base-dir "C:\path\to\Рабочие файлы\сгенерированные изображения" --face-image-size 1024x1024 --back-image-size 1536x1024 --json
```

Run with an explicit output project folder suffix:

```powershell
python main.py agent-run-api --mode multiformat_with_refs --prompts "C:\path\to\Рабочие файлы\style_probe.txt" --start 1 --end 1 --output-base-dir "C:\path\to\Рабочие файлы\сгенерированные изображения" --project-name countries --json
```

CLI-supported modes. This skill must still run only `multiformat_with_refs`:

```text
standard
multiformat
multiformat_with_refs
```

Expected JSON fields:

```json
{
  "ok": true,
  "command": "agent-run-api",
  "mode": "multiformat_with_refs",
  "planned": 3,
  "succeeded": 3,
  "failed": 0,
  "project_name": "countries",
  "output_base_dir": "C:/path/to/Рабочие файлы/сгенерированные изображения",
  "references_summary": {
    "style_reference_path": "data/style_refs/default.png",
    "style_reference_enabled": true,
    "prompt_logging_enabled": true,
    "content_refs_found": 1,
    "content_refs_missing": 0,
    "tasks_with_style_ref": 1,
    "tasks_with_content_ref": 1,
    "tasks_with_both_refs": 1
  },
  "output_dir": "C:/path/to/Рабочие файлы/сгенерированные изображения/2026-06-14_18-30-00_countries",
  "log_file": "logs/auto-gen_....log",
  "images": ["generated_images/2026-06-14_18-30-00_countries/image.png"],
  "errors": []
}
```

## Prompt File Formats

Use existing parser formats exactly.

Standard format exists in the parser but must not be used by this skill:

```text
Карточка 1 - Промпт 1: concise visual prompt variant A
Карточка 1 - Промпт 2: concise visual prompt variant B
```

Preferred `multiformat_with_refs`/multiformat format:

```text
Карточка 1 лицо Австрия - Промпт 1: Modern semi-flat polished vector illustration for an educational geography card game. Clean friendly shapes, soft volume, gentle shadows, subtle gradients, neat contours, simplified details, readable silhouettes, warm accents, pleasant stylish colors, no harsh neon colors. A calm airy composition inspired by Austria: upper and left areas stay light, quiet, and open with a soft atmospheric background. All main objects form one compact lower-right cluster: a small alpine music box, edelweiss flowers, and a slice of layered cake. The objects are large, readable, and balanced like a polished cutout illustration. No text, no readable words, no labels, no signs, no letters, no flags, no UI elements, no logos, no arrows, no photorealism, no 3D render, no painterly texture, no clutter.
Карточка 1 оборот Австрия - Промпт 1: Modern semi-flat polished vector illustration for an educational geography card game. Clean friendly shapes, soft volume, gentle shadows, subtle gradients, neat contours, simplified details, readable silhouettes, warm accents, pleasant stylish colors, no harsh neon colors. A panoramic country scene inspired by Austria, centered on a large recognizable view of Schonbrunn Palace with Vienna gardens. The main landmark sits in the foreground or middle ground, with simplified background elements receding into soft perspective. No text, no readable words, no labels, no signs, no letters, no flags, no UI elements, no logos, no arrows, no photorealism, no 3D render, no painterly texture, no clutter.
```

For style probes, make prompt variants intentionally different along one or two axes only: medium, palette, line quality, lighting, texture, framing, or level of realism. Keep the subject constant enough that style differences are easy to judge.

## Failure Handling

- If `agent-plan` returns no tasks, fix the prompt file format before running generation.
- If `agent-plan` or `agent-run-api` reports missing `--output-base-dir`, rerun with the ready project output base folder `...\Рабочие файлы\сгенерированные изображения`.
- If `agent-run-api` reports missing API key or invalid key format, stop and tell the user which provider is missing; do not expose existing key values.
- If some images fail, report `succeeded/failed`, show successful outputs, and suggest a smaller retry only for failed variants.
- If output paths are relative, resolve them against the repo root before showing image Markdown.
- If the command exits nonzero but prints JSON, trust the JSON first and summarize `errors`.

## Good Final Response Shape

For a completed probe, keep the response short:

- state how many images succeeded;
- provide the output folder and log file;
- show or list the generated images;
- summarize visible style differences only if images were inspected;
- propose the next concrete style iteration or say which prompt variant looks most promising when evidence supports it.
