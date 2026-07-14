"""Машинные команды единственного API-режима."""

import argparse
import contextlib
import io
import json
import os
import sys

from sites.aistudio import mode_multiformat_with_refs_api as mode_module
from utils import api_client
from utils.generation_runner import MODE_NAME, can_start_generation_api, load_tasks
from utils.paths import resolve_app_path
from utils.settings_store import load_settings


def is_agent_command(argv: list[str] | None = None) -> bool:
    argv = argv if argv is not None else sys.argv[1:]
    return bool(argv) and argv[0] in {"agent-plan", "agent-run-api"}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python main.py")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("agent-plan", "agent-run-api"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--prompts", required=True)
        sub.add_argument("--start", type=int, default=1)
        sub.add_argument("--end", type=int, default=None)
        sub.add_argument("--image-size", default=None)
        sub.add_argument("--face-image-size", default=None)
        sub.add_argument("--back-image-size", default=None)
        sub.add_argument("--output-base-dir", required=True)
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
            "PROMPTS_FILE": resolve_app_path(args.prompts),
            "START_FROM_CARD": args.start,
            "END_CARD": args.end,
            "SAVE_PROGRESS_TO_SETTINGS": False,
        }
    )
    for argument, key in (
        ("image_size", "API_IMAGE_SIZE"),
        ("face_image_size", "API_FACE_IMAGE_SIZE"),
        ("back_image_size", "API_BACK_IMAGE_SIZE"),
    ):
        value = getattr(args, argument, None)
        if value:
            settings[key] = value
    settings["OUTPUT_BASE_DIR"] = resolve_app_path(args.output_base_dir)
    if args.project_name:
        settings["OUTPUT_PROJECT_NAME"] = args.project_name
    if args.style_ref:
        settings["API_STYLE_REFERENCE_IMAGE"] = resolve_app_path(args.style_ref)
    if args.no_style_ref:
        settings["API_STYLE_REFERENCE_IMAGE"] = ""
    if args.no_log_prompts:
        settings["API_LOG_PROMPTS"] = False
    return settings


def _error(command: str, message: str) -> dict:
    return {"ok": False, "command": command, "mode": MODE_NAME, "errors": [message]}


def _plan_result(args: argparse.Namespace, settings: dict) -> dict:
    style_error = mode_module.validate_style_reference_settings(settings)
    if style_error:
        return _error(args.command, style_error)
    path = settings.get("PROMPTS_FILE") or ""
    if not os.path.isfile(path):
        return _error(args.command, f"Файл промптов не найден: {path}")
    tasks = load_tasks(settings)
    if not tasks:
        return _error(args.command, "Нет задач в выбранном диапазоне карточек.")

    provider = api_client.get_api_provider(settings, with_reference=False)
    provider_with_refs = api_client.get_api_provider(settings, with_reference=True)
    result = {
        "ok": True,
        "command": args.command,
        "method": "api",
        "mode": MODE_NAME,
        "prompts_file": path,
        "start_card": args.start,
        "end_card": args.end,
        "tasks_count": len(tasks),
        "plan": mode_module.get_plan_info(tasks),
        "provider": provider,
        "model": api_client.get_api_model(settings, provider, with_reference=False),
        "provider_with_refs": provider_with_refs,
        "model_with_refs": api_client.get_api_model(settings, provider_with_refs, with_reference=True),
        "quality": api_client.get_api_quality(settings, provider) or None,
        "image_size": api_client.resolve_image_size(settings),
        "face_image_size": api_client.resolve_image_size(settings, "лицо"),
        "back_image_size": api_client.resolve_image_size(settings, "оборот"),
        "output_base_dir": api_client.resolve_output_base_dir(settings),
        "output_dir": api_client.build_session_output_folder(settings),
        "project_name": api_client.resolve_output_project_name(settings),
    }
    result.update(mode_module.get_references_summary(tasks, settings))
    return result


def _run_result(args: argparse.Namespace, settings: dict) -> dict:
    ok, error = can_start_generation_api(settings)
    if not ok:
        return _error(args.command, error or "Запуск API-генерации невозможен.")
    api_client.reset_session_folder()
    result = mode_module.run_mode(load_tasks(settings), settings)
    result["command"] = args.command
    result.setdefault("mode", MODE_NAME)
    result.setdefault("output_base_dir", api_client.resolve_output_base_dir(settings))
    result.setdefault("project_name", api_client.resolve_output_project_name(settings))
    return result


def _emit(result: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    settings = _settings_from_args(args)
    if args.command == "agent-plan":
        result = _plan_result(args, settings)
    elif args.json:
        progress = io.StringIO()
        with contextlib.redirect_stdout(progress):
            result = _run_result(args, settings)
        if progress.getvalue():
            result["console_output"] = progress.getvalue()
    else:
        result = _run_result(args, settings)
    _emit(result, args.json)
    return 0 if result.get("ok") else 1
