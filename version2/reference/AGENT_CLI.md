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

## Commands

Plan a batch without API calls:

```powershell
python main.py agent-plan --mode multiformat_with_refs --prompts data\style_probe.txt --start 1 --end 1 --json
```

Run a batch synchronously through API:

```powershell
python main.py agent-run-api --mode multiformat_with_refs --prompts data\style_probe.txt --start 1 --end 1 --json
```

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
- `errors` when `ok=false`

`agent-run-api --json` returns a single JSON object with:

- `ok`
- `command`
- `mode`
- `planned`
- `succeeded`
- `failed`
- `output_dir`
- `log_file`
- `images`
- `errors`
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

`multiformat_with_refs` looks for reference images under:

```text
data/images/<side>/
```

Missing references are valid. The mode should continue and generate without a reference when no matching image is found.

## Documentation Maintenance

When changing agent CLI behavior:

- update this file;
- update `version2/planning/V2_AUDIT_TRACKER.md`;
- update the `auto-gen-api-agent` Codex skill if workflow, commands, result fields, or prompt defaults changed;
- add or update focused tests around `utils/agent_cli.py` and API-mode result behavior.
- preserve the rule that Codex/agent execution cannot start browser generation.
