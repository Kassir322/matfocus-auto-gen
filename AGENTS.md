# AGENTS.md

## Purpose

This repository contains a Windows automation app for generating images in Google AI Studio.
The active product is the v2 runtime in the repository root. `old_code/` is a legacy v1 reference copy.

This file is meant to help coding agents avoid breaking the current architecture and avoid confusing v2 with legacy layers.

## Current Runtime Contract

- Main entrypoint: `main.py`
- Codex/agent CLI contract:
  - implementation: `utils/agent_cli.py`
  - documentation: `version2/reference/AGENT_CLI.md`
  - preferred mode for Codex-driven generation: `multiformat_with_refs`
  - allowed execution method for Codex agents: API only
  - forbidden for Codex agents: browser generation, hotkeys, console menu driving, pyautogui/browser automation
  - preferred prompt style/line pattern: follow `data/countries_clear_nanobanana_prompts.txt`
- Active UI layer:
  - `ui/hotkeys.py`
  - `ui/console.py`
  - `ui/console_menu.py`
- Active runtime/process layer:
  - `utils/process_control.py`
  - `utils/generation_runner.py`
- Active storage layer:
  - `utils/settings_store.py`
  - `utils/coordinates_store.py`
- Active site implementation:
  - `sites/aistudio/`

Do not treat `utils/process_manager.py` as the main process model. It is a legacy compatibility shim.

## Legacy Boundaries

- `old_code/` is v1 reference code. Do not “sync back” changes from there unless explicitly requested.
- Root-level `config/` and `core/` still exist for legacy compatibility and some older tests.
- If changing active v2 runtime code, prefer root `main.py`, `ui/`, `utils/`, `sites/aistudio/`.
- If touching legacy shims, mark them clearly as legacy and avoid expanding their responsibility.

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
- Browser automation depends on `keyboard`, `pyautogui`, `pygetwindow`.
- Some local environments may not have test/runtime dependencies installed.
- A real prompts file is often configured via `data/settings.json`.
- In `multiformat_with_refs`, generation without a reference image is currently valid behavior.
- For Codex style-probe workflows, prefer `python main.py agent-plan ... --json` and `python main.py agent-run-api ... --json` over hotkeys/menu automation.
- Codex agents must not start browser generation. Agent-facing commands must force `GENERATION_METHOD=api` and use API-mode modules only.
- Codex-created probe prompts should normally use `multiformat_with_refs` and the `Карточка N лицо/оборот ... - Промпт M:` format shown in `data/countries_clear_nanobanana_prompts.txt`.

## Editing Guidance

- Prefer small, local changes over broad refactors unless explicitly requested.
- Do not rewrite active v2 code back toward the older `config/` + `core/` architecture.
- When cleaning structure, separate active runtime code from legacy compatibility code.
- Update `version2/planning/V2_AUDIT_TRACKER.md` when a change closes or changes an audited finding.
- Update `version2/reference/AGENT_CLI.md` whenever the Codex/agent CLI behavior, JSON contract, preferred mode, or prompt format changes.
- Preserve user data files in `data/`, generated outputs in `generated_images/`, and logs unless the user explicitly asks otherwise.

## Verification Guidance

- Prefer targeted verification over broad legacy test runs.
- The old `tests/test_suite.py` is mostly a legacy compatibility suite.
- Prefer adding or running focused checks for the active v2 contract when changing v2 runtime structure.

## Good First Read For Agents

1. `main.py`
2. `ui/hotkeys.py`
3. `utils/process_control.py`
4. `utils/generation_runner.py`
5. `version2/planning/V2_AUDIT_TRACKER.md`
