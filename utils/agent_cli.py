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
        sub.add_argument("--image-size", default=None)
        sub.add_argument("--face-image-size", default=None)
        sub.add_argument("--back-image-size", default=None)
        sub.add_argument("--output-base-dir", default=None)
        sub.add_argument("--project-name", default=None)
        style_group = sub.add_mutually_exclusive_group()
        style_group.add_argument("--style-ref", default=None)
        style_group.add_argument("--no-style-ref", action="store_true")
        sub.add_argument("--no-log-prompts", action="store_true")
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
    if getattr(args, "image_size", None):
        settings["API_IMAGE_SIZE"] = args.image_size
    if getattr(args, "face_image_size", None):
        settings["API_FACE_IMAGE_SIZE"] = args.face_image_size
    if getattr(args, "back_image_size", None):
        settings["API_BACK_IMAGE_SIZE"] = args.back_image_size
    if getattr(args, "output_base_dir", None):
        settings["OUTPUT_BASE_DIR"] = args.output_base_dir
    if getattr(args, "project_name", None):
        settings["OUTPUT_PROJECT_NAME"] = args.project_name
    if getattr(args, "style_ref", None):
        settings["API_STYLE_REFERENCE_IMAGE"] = args.style_ref
    if getattr(args, "no_style_ref", False):
        settings["API_STYLE_REFERENCE_IMAGE"] = ""
    if getattr(args, "no_log_prompts", False):
        settings["API_LOG_PROMPTS"] = False
    return settings


def _validate_args(args: argparse.Namespace, settings: dict) -> str | None:
    if args.command in {"agent-plan", "agent-run-api"} and not str(getattr(args, "output_base_dir", "") or "").strip():
        return "Для agent CLI требуется --output-base-dir."

    style_ref = str(settings.get("API_STYLE_REFERENCE_IMAGE", "") or "").strip()
    style_flag_used = bool(getattr(args, "style_ref", None) or getattr(args, "no_style_ref", False))
    if style_flag_used and args.mode != "multiformat_with_refs":
        return "--style-ref/--no-style-ref поддерживаются только для mode=multiformat_with_refs."
    if style_ref and args.mode != "multiformat_with_refs":
        return "API_STYLE_REFERENCE_IMAGE поддерживается только для mode=multiformat_with_refs."
    if args.mode == "multiformat_with_refs":
        module = _mode_module(args.mode)
        if hasattr(module, "validate_style_reference_settings"):
            return module.validate_style_reference_settings(settings)
    return None


def _base_error(command: str, message: str) -> dict:
    return {
        "ok": False,
        "command": command,
        "errors": [message],
    }


def _plan_result(args: argparse.Namespace, settings: dict) -> dict:
    validation_error = _validate_args(args, settings)
    if validation_error:
        return _base_error(args.command, validation_error)

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
    image_size = api_client.resolve_image_size(settings)
    face_image_size = api_client.resolve_image_size(settings, "лицо")
    back_image_size = api_client.resolve_image_size(settings, "оборот")
    image_size = api_client.normalize_image_size_for_provider(provider, image_size)[0] or image_size
    face_image_size = api_client.normalize_image_size_for_provider(provider, face_image_size)[0] or face_image_size
    back_image_size = api_client.normalize_image_size_for_provider(provider, back_image_size)[0] or back_image_size
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
        "image_size": image_size,
        "face_image_size": face_image_size,
        "back_image_size": back_image_size,
        "output_base_dir": api_client.resolve_output_base_dir(settings),
        "output_dir": api_client.build_session_output_folder(settings),
        "project_name": api_client.resolve_output_project_name(settings),
    }
    if args.mode == "multiformat_with_refs":
        provider_with_refs = api_client.get_api_provider(settings, with_reference=True)
        result["provider_with_refs"] = provider_with_refs
        result["model_with_refs"] = api_client.get_api_model(settings, provider_with_refs, with_reference=True)
        if hasattr(module, "get_references_summary"):
            references_summary = module.get_references_summary(tasks, settings)
            result["references_summary"] = references_summary
            result.update(references_summary)
    return result


def _run_result(args: argparse.Namespace, settings: dict) -> dict:
    validation_error = _validate_args(args, settings)
    if validation_error:
        return _base_error(args.command, validation_error)

    ok, err = can_start_generation_api(settings)
    if not ok:
        return _base_error(args.command, err or "Запуск API-генерации невозможен.")

    module = _mode_module(args.mode)
    tasks = module.load_tasks_from_file(settings.get("PROMPTS_FILE") or "")
    api_client.reset_session_folder()
    result = module.run_mode(tasks, settings)
    if not isinstance(result, dict):
        output_dir = api_client.get_session_output_folder(settings)
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
    result.setdefault("output_base_dir", api_client.resolve_output_base_dir(settings))
    result.setdefault("project_name", api_client.resolve_output_project_name(settings))
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
