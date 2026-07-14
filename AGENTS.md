# AGENTS.md

## Purpose

This repository contains an API-only application for generating card images.

This file is meant to help coding agents preserve the active v2 architecture.

## Current Runtime Contract

- Main entrypoint: `main.py`
- Codex/agent CLI contract:
  - implementation: `utils/agent_cli.py`
  - documentation: `version2/reference/AGENT_CLI.md`
  - preferred mode for Codex-driven generation: `multiformat_with_refs`
  - allowed execution method for Codex agents: API only
  - preferred prompt style/line pattern: follow `data/countries_clear_nanobanana_prompts.txt`
- Active UI layer: `ui/console_menu.py`
- Active runtime layer: `utils/generation_runner.py`
- Active storage layer: `utils/settings_store.py`
- Active site implementation: `sites/aistudio/mode_multiformat_with_refs_api.py`

The only supported mode is `multiformat_with_refs` through API. Browser
automation, coordinates, hotkeys, and process workers are intentionally absent.

## Source Of Truth

Use this priority order when facts conflict:

1. Current runnable code in the repository root
2. `version2/reference/AGENT_CLI.md` for Codex/agent CLI workflows
3. `version2/planning/V2_AUDIT_TRACKER.md`
4. Other `version2/` planning/reference docs
5. Older README sections

Some docs in `README.md` and `version2/` are historically useful but partially outdated.

## Important Project Files

- Settings: `data/settings.json`
- Coordinates: `data/coordinates.json`
- Logs: `logs/`
- Generated images: `generated_images/`
- Main audit tracker: `version2/planning/V2_AUDIT_TRACKER.md`
- Codex agent CLI docs: `version2/reference/AGENT_CLI.md`

## Practical Notes

- The project is Windows-first.
- Some local environments may not have test/runtime dependencies installed.
- A real prompts file is often configured via `data/settings.json`.
- `OUTPUT_BASE_DIR` controls the base image output directory and defaults to `generated_images`; timestamped run folders are created inside it.
- Generation without a content reference image remains valid behavior.
- For Codex style-probe workflows, prefer `python main.py agent-plan ... --json` and `python main.py agent-run-api ... --json` over hotkeys/menu automation.
- Codex agent CLI commands must pass `--output-base-dir`; for project work use the ready folder `...\Рабочие файлы\сгенерированные изображения`, with timestamped wave folders created inside it.
- Agent-facing commands use API modules only.
- Codex-created probe prompts should normally use `multiformat_with_refs` and the `Карточка N лицо/оборот ... - Промпт M:` format shown in `data/countries_clear_nanobanana_prompts.txt`.

## Editing Guidance

- Prefer small, local changes over broad refactors unless explicitly requested.
- Keep the active function-based v2 architecture; do not introduce a parallel
  settings, coordinates, or process-management layer.
- Update `version2/planning/V2_AUDIT_TRACKER.md` when a change closes or changes an audited finding.
- Update `version2/reference/AGENT_CLI.md` whenever the Codex/agent CLI behavior, JSON contract, preferred mode, or prompt format changes.
- Preserve user data files in `data/`, generated outputs in `generated_images/`, and logs unless the user explicitly asks otherwise.

## Verification Guidance

- Prefer targeted checks for the active v2 contract when changing runtime structure.

## Good First Read For Agents

1. `main.py`
2. `ui/hotkeys.py`
3. `utils/generation_runner.py`
4. `sites/aistudio/mode_multiformat_with_refs_api.py`
5. `version2/planning/V2_AUDIT_TRACKER.md`
