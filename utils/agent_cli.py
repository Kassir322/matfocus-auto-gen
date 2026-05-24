"""Machine-readable CLI entrypoints for Codex/agent-driven API runs."""

import argparse
import contextlib
import io
import json
import os
import sys

from utils import api_client
from utils.generation_runner import can_start_generation_api
from utils.prompt_parsers import filter_tasks_by_range
from utils.settings_store import load_settings


SUPPORTED_MODES = {"standard", "multiformat", "multiformat_with_refs"}


def is_agent_command(argv: list[str] | None = None) -> bool:
    argv = argv if argv is not None else sys.argv[1:]
    return bool(argv) and argv[0] in {"agent-plan", "agent-run-api"}


def _mode_module(mode: str):
    if mode == "standard":
        from sites.aistudio import mode_standard_api as module
    elif mode == "multiformat":
        from sites.aistudio import mode_multiformat_api as module
    else:
        from sites.aistudio import mode_multiformat_with_refs_api as module
    return module


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python main.py")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("agent-plan", "agent-run-api"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--mode", required=True, choices=sorted(SUPPORTED_MODES))
        sub.add_argument("--prompts", required=True)
        sub.add_argument("--start", type=int, default=1)
        sub.add_argument("--end", type=int, default=None)
        sub.add_argument("--json", action="store_true")

    return parser


def _settings_from_args(args: argparse.Namespace) -> dict:
    settings = dict(load_settings())
    settings.update(
        {
            "CURRENT_SITE": "aistudio",
            "CURRENT_MODE": args.mode,
            "GENERATION_METHOD": "api",
            "PROMPTS_FILE": args.prompts,
            "START_FROM_CARD": args.start,
            "END_CARD": args.end,
            "SAVE_PROGRESS_TO_SETTINGS": False,
        }
    )
    return settings


def _base_error(command: str, message: str) -> dict:
    return {
        "ok": False,
        "command": command,
        "errors": [message],
    }


def _plan_result(args: argparse.Namespace, settings: dict) -> dict:
    module = _mode_module(args.mode)
    path = settings.get("PROMPTS_FILE") or ""
    if not path or not os.path.isfile(path):
        return _base_error(args.command, f"Файл промптов не найден: {path}")

    tasks = module.load_tasks_from_file(path)
    tasks = filter_tasks_by_range(tasks, int(settings.get("START_FROM_CARD", 1)), settings.get("END_CARD"))
    if not tasks:
        return _base_error(args.command, "Нет задач в выбранном диапазоне карточек.")

    plan_info = module.get_plan_info(tasks)
    provider = api_client.get_api_provider(settings, with_reference=False)
    model = api_client.get_api_model(settings, provider, with_reference=False)
    quality = api_client.get_api_quality(settings, provider)
    result = {
        "ok": True,
        "command": args.command,
        "site": "aistudio",
        "method": "api",
        "mode": args.mode,
        "prompts_file": path,
        "start_card": args.start,
        "end_card": args.end,
        "tasks_count": len(tasks),
        "plan": plan_info,
        "provider": provider,
        "model": model,
        "quality": quality or None,
        "image_size": settings.get("API_IMAGE_SIZE"),
    }
    if args.mode == "multiformat_with_refs":
        provider_with_refs = api_client.get_api_provider(settings, with_reference=True)
        result["provider_with_refs"] = provider_with_refs
        result["model_with_refs"] = api_client.get_api_model(settings, provider_with_refs, with_reference=True)
    return result


def _run_result(args: argparse.Namespace, settings: dict) -> dict:
    ok, err = can_start_generation_api(settings)
    if not ok:
        return _base_error(args.command, err or "Запуск API-генерации невозможен.")

    module = _mode_module(args.mode)
    tasks = module.load_tasks_from_file(settings.get("PROMPTS_FILE") or "")
    api_client.reset_session_folder()
    result = module.run_mode(tasks, settings)
    if not isinstance(result, dict):
        output_dir = api_client.get_session_output_folder()
        result = {
            "ok": False,
            "mode": args.mode,
            "planned": 0,
            "succeeded": 0,
            "failed": 0,
            "output_dir": output_dir,
            "log_file": None,
            "images": [],
            "errors": ["API-режим не вернул машинный результат."],
        }
    result["command"] = args.command
    return result


def _emit(result: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False))
        return
    if result.get("ok"):
        print("OK")
    else:
        print("ERROR")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    settings = _settings_from_args(args)

    if args.command == "agent-plan":
        result = _plan_result(args, settings)
    else:
        if args.json:
            progress = io.StringIO()
            with contextlib.redirect_stdout(progress):
                result = _run_result(args, settings)
            captured = progress.getvalue()
            if captured:
                result["console_output"] = captured
        else:
            result = _run_result(args, settings)

    _emit(result, args.json)
    return 0 if result.get("ok") else 1
