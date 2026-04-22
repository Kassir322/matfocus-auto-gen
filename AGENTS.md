# AGENTS.md

## Purpose

This repository contains a Windows automation app for generating images in Google AI Studio.
The active product is the v2 runtime in the repository root. `old_code/` is a legacy v1 reference copy.

This file is meant to help coding agents avoid breaking the current architecture and avoid confusing v2 with legacy layers.

## Current Runtime Contract

- Main entrypoint: `main.py`
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
2. `version2/planning/V2_AUDIT_TRACKER.md`
3. Other `version2/` planning/reference docs
4. Older README sections

Some docs in `README.md` and `version2/` are historically useful but partially outdated.

## Important Project Files

- Settings: `data/settings.json`
- Coordinates: `data/coordinates.json`
- Logs: `logs/`
- Generated images: `generated_images/`
- Main audit tracker: `version2/planning/V2_AUDIT_TRACKER.md`

## Practical Notes

- The project is Windows-first.
- Browser automation depends on `keyboard`, `pyautogui`, `pygetwindow`.
- Some local environments may not have test/runtime dependencies installed.
- A real prompts file is often configured via `data/settings.json`.
- In `multiformat_with_refs`, generation without a reference image is currently valid behavior.

## Editing Guidance

- Prefer small, local changes over broad refactors unless explicitly requested.
- Do not rewrite active v2 code back toward the older `config/` + `core/` architecture.
- When cleaning structure, separate active runtime code from legacy compatibility code.
- Update `version2/planning/V2_AUDIT_TRACKER.md` when a change closes or changes an audited finding.
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
