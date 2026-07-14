"""Focused checks for the active v2 settings/coordinates storage contract."""

import json
import os

from utils import coordinates_store
from utils import generation_runner
from utils import settings_store
from utils.paths import REPO_ROOT


def test_apply_defaults_fills_missing_fields_and_recomputes_cards_to_process():
    """Settings defaults should fill gaps and derive CARDS_TO_PROCESS from the range."""
    settings = {
        "START_FROM_CARD": 4,
        "END_CARD": 9,
    }

    result = settings_store.apply_defaults(settings)

    assert result is settings
    assert settings["CURRENT_SITE"] == "aistudio"
    assert settings["CURRENT_MODE"] == "standard"
    assert settings["API_MODEL_WITH_REFS"] == "gemini-2.5-flash-image"
    assert settings["API_PROVIDER"] == "nanobanana"
    assert settings["API_PROVIDER_WITH_REFS"] == "nanobanana"
    assert settings["API_MODEL_CHATGPT"] == "gpt-image-2"
    assert settings["API_STYLE_REFERENCE_IMAGE"] == ""
    assert settings["API_LOG_PROMPTS"] is True
    assert settings["API_CHATGPT_RATE_LIMIT_PROFILE"] == "tier3"
    assert settings["API_CHATGPT_MAX_WORKERS"] == 50
    assert settings["API_CHATGPT_RATE_LIMIT_IPM"] == 50
    assert settings["API_CHATGPT_RATE_LIMIT_TPM"] == 800000
    assert settings["PROMPTS_FILE"] == str(REPO_ROOT / "data" / "all_card_prompts.txt")
    assert settings["OUTPUT_BASE_DIR"] == str(REPO_ROOT / "generated_images")
    assert settings["BACK_ASPECT_RATIO"] == "16:9"
    assert settings["CARDS_TO_PROCESS"] == 6


def test_save_and_load_settings_use_json_store_with_defaults(tmp_path, monkeypatch):
    """Settings should persist through data/settings.json and regain missing defaults on load."""
    settings_path = tmp_path / "settings.json"
    monkeypatch.setattr(settings_store, "SETTINGS_PATH", str(settings_path))

    settings_store.save_settings(
        {
            "CURRENT_MODE": "multiformat_with_refs",
            "START_FROM_CARD": 2,
            "END_CARD": 4,
            "PROMPTS_FILE": "data/custom.txt",
        }
    )

    loaded = settings_store.load_settings()

    assert loaded["CURRENT_MODE"] == "multiformat_with_refs"
    assert loaded["PROMPTS_FILE"] == str(REPO_ROOT / "data" / "custom.txt")
    assert loaded["CARDS_TO_PROCESS"] == 3
    assert loaded["API_MODEL_WITH_REFS"] == "gemini-2.5-flash-image"
    assert loaded["API_PROVIDER"] == "nanobanana"
    assert loaded["OUTPUT_BASE_DIR"] == str(REPO_ROOT / "generated_images")
    assert loaded["GENERATION_METHOD"] == "browser"


def test_apply_defaults_uses_legacy_api_key_only_in_memory(monkeypatch):
    """Legacy API_KEY may populate runtime compatibility fields, but not storage."""
    monkeypatch.setattr(settings_store, "ENV_PATH", "missing-test.env")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    settings = {
        "API_KEY": "AIzaSyLEGACY_KEY_12345678901234567890",
    }

    settings_store.apply_defaults(settings)

    assert settings["API_KEY_NANOBANANA"] == "AIzaSyLEGACY_KEY_12345678901234567890"
    assert settings["API_KEY"] == settings["API_KEY_NANOBANANA"]


def test_env_keys_populate_legacy_fields_in_memory(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "AIzaSyENV_GOOGLE_KEY_123456789012345")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env-openai-key-1234567890")
    settings = {}

    settings_store.apply_defaults(settings)

    assert settings["API_KEY_NANOBANANA"] == "AIzaSyENV_GOOGLE_KEY_123456789012345"
    assert settings["API_KEY"] == "AIzaSyENV_GOOGLE_KEY_123456789012345"
    assert settings["API_KEY_CHATGPT"] == "sk-env-openai-key-1234567890"


def test_env_file_does_not_override_process_env(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "GOOGLE_API_KEY=AIzaSyFILE_GOOGLE_KEY_123456789012345\n"
        "OPENAI_API_KEY=sk-file-openai-key-1234567890\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(settings_store, "ENV_PATH", str(env_path))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-process-openai-key-1234567890")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    loaded = settings_store.load_settings()

    assert loaded["API_KEY_NANOBANANA"] == "AIzaSyFILE_GOOGLE_KEY_123456789012345"
    assert loaded["API_KEY_CHATGPT"] == "sk-process-openai-key-1234567890"


def test_save_settings_does_not_write_secret_fields(tmp_path, monkeypatch):
    settings_path = tmp_path / "settings.json"
    monkeypatch.setattr(settings_store, "SETTINGS_PATH", str(settings_path))

    settings_store.save_settings(
        {
            "API_KEY": "AIzaSyLEGACY_KEY_12345678901234567890",
            "API_KEY_NANOBANANA": "AIzaSyNEW_KEY_1234567890123456789012",
            "API_KEY_CHATGPT": "sk-test-chatgpt-key-1234567890",
            "SAVE_PROGRESS_TO_SETTINGS": False,
        }
    )

    saved = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "API_KEY" not in saved
    assert "API_KEY_NANOBANANA" not in saved
    assert "API_KEY_CHATGPT" not in saved
    assert "SAVE_PROGRESS_TO_SETTINGS" not in saved


def test_save_secret_updates_env_file_atomically(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("OTHER=value\nOPENAI_API_KEY=old\n", encoding="utf-8")
    monkeypatch.setattr(settings_store, "ENV_PATH", str(env_path))

    settings_store.save_secret("chatgpt", "sk-new-openai-key-1234567890")

    text = env_path.read_text(encoding="utf-8")
    assert "OTHER=value" in text
    assert "OPENAI_API_KEY=sk-new-openai-key-1234567890" in text
    assert os.environ["OPENAI_API_KEY"] == "sk-new-openai-key-1234567890"


def test_update_start_card_keeps_end_card_range_valid(tmp_path, monkeypatch):
    """Auto-advance should also lift END_CARD when the range would invert."""
    settings_path = tmp_path / "settings.json"
    monkeypatch.setattr(settings_store, "SETTINGS_PATH", str(settings_path))

    settings_store.save_settings(
        {
            "START_FROM_CARD": 1,
            "END_CARD": 1,
        }
    )

    settings_store.update_start_card(2)
    loaded = settings_store.load_settings()

    assert loaded["START_FROM_CARD"] == 2
    assert loaded["END_CARD"] == 2
    assert loaded["CARDS_TO_PROCESS"] == 1


def test_load_coordinates_returns_two_separate_dicts_with_defaults(tmp_path, monkeypatch):
    """Coordinates storage should load `coordinates` and `relative_movements` separately."""
    coordinates_path = tmp_path / "coordinates.json"
    monkeypatch.setattr(coordinates_store, "COORDINATES_PATH", str(coordinates_path))
    coordinates_path.write_text(
        json.dumps(
            {
                "coordinates": {
                    "PROMPT_INPUT": [11, 22],
                    "PROMPT_INPUT_AFTER_IMAGE": [33, 44],
                },
                "relative_movements": {
                    "TO_SAVE_OPTION": [55, 66],
                },
            }
        ),
        encoding="utf-8",
    )

    coordinates, relative_movements = coordinates_store.load_coordinates()

    assert coordinates["PROMPT_INPUT"] == (11, 22)
    assert coordinates["PROMPT_INPUT_AFTER_IMAGE"] == (33, 44)
    assert relative_movements["TO_SAVE_OPTION"] == (55, 66)
    assert "TO_SAVE_OPTION" not in coordinates


def test_load_coordinates_falls_back_to_zero_points_for_invalid_shape(tmp_path, monkeypatch):
    """Malformed coordinates.json data should fall back to safe `(0, 0)` defaults."""
    coordinates_path = tmp_path / "coordinates.json"
    monkeypatch.setattr(coordinates_store, "COORDINATES_PATH", str(coordinates_path))
    coordinates_path.write_text(
        json.dumps(
            {
                "coordinates": ["bad-structure"],
                "relative_movements": {
                    "TO_SAVE_OPTION": "bad-value",
                },
            }
        ),
        encoding="utf-8",
    )

    coordinates, relative_movements = coordinates_store.load_coordinates()

    assert coordinates == coordinates_store.DEFAULT_COORDINATES
    assert relative_movements == coordinates_store.DEFAULT_RELATIVE_MOVEMENTS


def test_set_coordinate_updates_selected_dictionary_and_saves(tmp_path, monkeypatch):
    """set_coordinate should update either coordinates or relative_movements by key name."""
    coordinates_path = tmp_path / "coordinates.json"
    monkeypatch.setattr(coordinates_store, "COORDINATES_PATH", str(coordinates_path))

    coordinates = dict(coordinates_store.DEFAULT_COORDINATES)
    relative_movements = dict(coordinates_store.DEFAULT_RELATIVE_MOVEMENTS)

    coordinates_store.set_coordinate(
        "PROMPT_INPUT_AFTER_IMAGE",
        101,
        202,
        coordinates,
        relative_movements,
    )
    coordinates_store.set_coordinate(
        "TO_SAVE_OPTION",
        7,
        8,
        coordinates,
        relative_movements,
    )

    loaded_coordinates, loaded_relative_movements = coordinates_store.load_coordinates()

    assert loaded_coordinates["PROMPT_INPUT_AFTER_IMAGE"] == (101, 202)
    assert loaded_relative_movements["TO_SAVE_OPTION"] == (7, 8)


def test_repo_rooted_runtime_paths_do_not_follow_current_directory(tmp_path, monkeypatch):
    from sites.aistudio import mode_standard_api
    from utils import api_client

    monkeypatch.chdir(tmp_path)

    assert settings_store.SETTINGS_PATH == str(REPO_ROOT / "data" / "settings.json")
    assert coordinates_store.COORDINATES_PATH == str(REPO_ROOT / "data" / "coordinates.json")
    assert api_client.resolve_output_base_dir({"OUTPUT_BASE_DIR": "generated_images"}) == str(REPO_ROOT / "generated_images")
    assert mode_standard_api._get_log_filepath().startswith(str(REPO_ROOT / "logs"))


def test_browser_worker_passes_coordinates_and_relative_movements_separately(monkeypatch):
    """Browser workers should forward two coordinate dictionaries separately to run_mode."""
    tasks = [{"card_number": 3, "prompt": "test"}]
    received = {}

    monkeypatch.setattr(
        "sites.aistudio.mode_standard.load_tasks_from_file",
        lambda path: list(tasks),
    )

    def fake_run_mode(passed_tasks, settings, coordinates, relative_movements):
        received["tasks"] = passed_tasks
        received["coordinates"] = coordinates
        received["relative_movements"] = relative_movements

    monkeypatch.setattr("sites.aistudio.mode_standard.run_mode", fake_run_mode)

    settings = {
        "PROMPTS_FILE": "data/prompts.txt",
        "START_FROM_CARD": 3,
        "END_CARD": 3,
    }
    coordinates = {"PROMPT_INPUT": (1, 2)}
    relative_movements = {"TO_SAVE_OPTION": (3, 4)}

    generation_runner.run_standard_worker(settings, coordinates, relative_movements)

    assert received["tasks"] == tasks
    assert received["coordinates"] is coordinates
    assert received["relative_movements"] is relative_movements
