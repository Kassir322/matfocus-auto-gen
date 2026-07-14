import json

import main
from ui import console_menu
from utils import agent_cli, settings_store
from utils.generation_runner import MODE_NAME, load_tasks


def _prompts(path):
    path.write_text("Карточка 1 лицо Тест - Промпт 1: лицо\nКарточка 1 оборот Тест - Промпт 1: оборот\n", encoding="utf-8")


def test_agent_plan_has_fixed_mode_and_no_mode_argument(tmp_path, monkeypatch, capsys):
    prompts = tmp_path / "prompts.txt"
    _prompts(prompts)
    monkeypatch.setattr(agent_cli, "load_settings", lambda: {"API_PROVIDER": "nanobanana", "API_PROVIDER_WITH_REFS": "nanobanana"})
    code = agent_cli.main(["agent-plan", "--prompts", str(prompts), "--output-base-dir", str(tmp_path / "output"), "--json"])
    result = json.loads(capsys.readouterr().out)
    assert code == 0
    assert result["mode"] == MODE_NAME
    assert result["plan"]["images_planned"] == 2


def test_agent_cli_rejects_removed_mode_argument(tmp_path):
    prompts = tmp_path / "prompts.txt"
    _prompts(prompts)
    try:
        agent_cli.main(["agent-plan", "--mode", "standard", "--prompts", str(prompts), "--output-base-dir", str(tmp_path)])
    except SystemExit as error:
        assert error.code == 2
    else:
        raise AssertionError("--mode должен быть удалён")


def test_settings_drop_removed_browser_fields(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"CURRENT_MODE": "standard", "GENERATION_METHOD": "browser", "PROMPTS_FILE": "x.txt"}), encoding="utf-8")
    monkeypatch.setattr(settings_store, "SETTINGS_PATH", str(path))
    monkeypatch.setattr(settings_store, "ENV_PATH", str(tmp_path / ".env"))
    settings = settings_store.load_settings()
    assert "CURRENT_MODE" not in settings
    assert "GENERATION_METHOD" not in settings
    assert settings["PROMPTS_FILE"].endswith("x.txt")


def test_menu_runs_api_directly(monkeypatch):
    monkeypatch.setattr(console_menu, "can_start_generation_api", lambda _settings: (True, None))
    monkeypatch.setattr(console_menu, "run_api", lambda _settings: {"succeeded": 2, "failed": 0})
    console_menu.start_generation({"PROMPTS_FILE": "prompts.txt"})


def test_main_without_arguments_opens_menu(monkeypatch):
    called = []
    monkeypatch.setattr(main.sys, "argv", ["main.py"])
    monkeypatch.setattr("ui.console_menu.show_main_menu", lambda settings: called.append(settings))
    monkeypatch.setattr("utils.settings_store.load_settings", lambda: {"PROMPTS_FILE": "x"})
    assert main.main() == 0
    assert called == [{"PROMPTS_FILE": "x"}]


def test_load_tasks_parses_only_face_and_back_format(tmp_path):
    prompts = tmp_path / "prompts.txt"
    _prompts(prompts)
    assert len(load_tasks({"PROMPTS_FILE": str(prompts), "START_FROM_CARD": 1, "END_CARD": 1})) == 2
