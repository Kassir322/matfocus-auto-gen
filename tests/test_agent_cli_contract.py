"""Focused checks for Codex/agent API CLI commands."""

import json

from utils import agent_cli
from sites.aistudio import mode_standard_api


def _write_standard_prompts(path):
    path.write_text(
        "Карточка 1 - Промпт 1: first prompt\n"
        "Карточка 1 - Промпт 2: second prompt\n",
        encoding="utf-8",
    )


def _base_settings(prompts_path):
    return {
        "CURRENT_SITE": "aistudio",
        "CURRENT_MODE": "standard",
        "PROMPTS_FILE": str(prompts_path),
        "START_FROM_CARD": 10,
        "END_CARD": 20,
        "GENERATION_METHOD": "api",
        "API_PROVIDER": "nanobanana",
        "API_PROVIDER_WITH_REFS": "nanobanana",
        "API_KEY": "AIzaSyDUMMY_KEY_FOR_TESTS_123456789012345",
        "API_KEY_NANOBANANA": "AIzaSyDUMMY_KEY_FOR_TESTS_123456789012345",
        "API_IMAGE_SIZE": "1K",
        "API_TIMEOUT": 60.0,
        "SAVE_PROGRESS_TO_SETTINGS": True,
    }


def test_agent_plan_json_uses_prompts_without_api_calls(tmp_path, monkeypatch):
    prompts_path = tmp_path / "prompts.txt"
    _write_standard_prompts(prompts_path)

    monkeypatch.setattr(agent_cli, "load_settings", lambda: _base_settings(prompts_path))
    monkeypatch.setattr(agent_cli.api_client, "init_client", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("API called")))

    result = agent_cli._plan_result(
        type(
            "Args",
            (),
            {
                "command": "agent-plan",
                "mode": "standard",
                "prompts": str(prompts_path),
                "start": 1,
                "end": 1,
            },
        )(),
        agent_cli._settings_from_args(
            type(
                "Args",
                (),
                {
                    "mode": "standard",
                    "prompts": str(prompts_path),
                    "start": 1,
                    "end": 1,
                },
            )()
        ),
    )

    assert result["ok"] is True
    assert result["command"] == "agent-plan"
    assert result["tasks_count"] == 2
    assert result["plan"]["images_planned"] == 2


def test_agent_settings_force_api_even_when_base_settings_are_browser(tmp_path, monkeypatch):
    prompts_path = tmp_path / "prompts.txt"
    _write_standard_prompts(prompts_path)
    base_settings = _base_settings(prompts_path)
    base_settings["GENERATION_METHOD"] = "browser"

    monkeypatch.setattr(agent_cli, "load_settings", lambda: base_settings)

    settings = agent_cli._settings_from_args(
        type(
            "Args",
            (),
            {
                "mode": "standard",
                "prompts": str(prompts_path),
                "start": 1,
                "end": 1,
            },
        )()
    )

    assert settings["GENERATION_METHOD"] == "api"
    assert settings["SAVE_PROGRESS_TO_SETTINGS"] is False


def test_agent_run_api_json_is_isolated_from_settings_progress(tmp_path, monkeypatch, capsys):
    prompts_path = tmp_path / "prompts.txt"
    output_dir = tmp_path / "generated"
    log_path = tmp_path / "agent.log"
    _write_standard_prompts(prompts_path)
    saved_progress = []

    monkeypatch.setattr(agent_cli, "load_settings", lambda: _base_settings(prompts_path))
    monkeypatch.setattr(agent_cli, "can_start_generation_api", lambda settings: (True, None))
    monkeypatch.setattr(mode_standard_api, "_get_log_filepath", lambda: str(log_path))
    monkeypatch.setattr(mode_standard_api.time, "sleep", lambda *args, **kwargs: None)
    monkeypatch.setattr(mode_standard_api.api_client, "check_api_key_format", lambda api_key, provider="nanobanana": (True, None))
    monkeypatch.setattr(mode_standard_api.api_client, "init_client", lambda api_key, provider="nanobanana": object())
    monkeypatch.setattr(mode_standard_api.api_client, "get_session_output_folder", lambda: str(output_dir))
    monkeypatch.setattr(mode_standard_api.api_client, "fetch_openai_costs", lambda *args, **kwargs: (None, "disabled"))
    monkeypatch.setattr("utils.settings_store.update_start_card", lambda card_number: saved_progress.append(card_number))

    def fake_generate(task, client, settings, log_file):
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"image_{task['generation_number']}.png").write_bytes(b"png")
        return True

    monkeypatch.setattr(mode_standard_api, "_generate_single_image_api", fake_generate)

    exit_code = agent_cli.main(
        [
            "agent-run-api",
            "--mode",
            "standard",
            "--prompts",
            str(prompts_path),
            "--start",
            "1",
            "--end",
            "1",
            "--json",
        ]
    )

    rendered = capsys.readouterr().out.strip()
    result = json.loads(rendered)
    assert exit_code == 0
    assert result["ok"] is True
    assert result["command"] == "agent-run-api"
    assert result["planned"] == 2
    assert result["succeeded"] == 2
    assert len(result["images"]) == 2
    assert result["log_file"] == str(log_path)
    assert saved_progress == []


def test_agent_run_api_missing_prompts_returns_machine_error(tmp_path, monkeypatch, capsys):
    missing_path = tmp_path / "missing.txt"
    monkeypatch.setattr(agent_cli, "load_settings", lambda: _base_settings(missing_path))

    exit_code = agent_cli.main(
        [
            "agent-run-api",
            "--mode",
            "standard",
            "--prompts",
            str(missing_path),
            "--start",
            "1",
            "--end",
            "1",
            "--json",
        ]
    )

    result = json.loads(capsys.readouterr().out.strip())
    assert exit_code == 1
    assert result["ok"] is False
    assert result["command"] == "agent-run-api"
    assert result["errors"]
