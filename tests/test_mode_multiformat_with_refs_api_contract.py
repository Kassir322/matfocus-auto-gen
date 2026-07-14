"""Focused checks for multiformat_with_refs API reference metadata."""

from sites.aistudio import mode_multiformat_with_refs_api
from utils import api_client


def _style_settings(style_path, log_prompts=True):
    return {
        "API_PROVIDER": "nanobanana",
        "API_PROVIDER_WITH_REFS": "chatgpt",
        "API_MODEL_CHATGPT": "gpt-image-2",
        "API_STYLE_REFERENCE_IMAGE": str(style_path),
        "API_LOG_PROMPTS": log_prompts,
        "FACE_ASPECT_RATIO": "4:3",
        "BACK_ASPECT_RATIO": "16:9",
        "API_IMAGE_SIZE": "auto",
        "API_TIMEOUT": 60.0,
    }


def test_prepare_task_provider_metadata_routes_global_style_reference_to_refs_provider(tmp_path):
    style_path = tmp_path / "style.png"
    style_path.write_bytes(b"style")
    task = {
        "card_number": 1,
        "card_name": "Test",
        "pair_number": 1,
        "side": "лицо",
        "prompt_text": "Prompt",
    }

    chatgpt_tasks, other_tasks = mode_multiformat_with_refs_api._prepare_task_provider_metadata(
        [task],
        _style_settings(style_path),
    )

    assert chatgpt_tasks == [task]
    assert other_tasks == []
    assert task["_with_reference"] is True
    assert task["_reference_mode"] == api_client.REFERENCE_MODE_STYLE
    assert task["_style_reference_path"] == str(style_path)
    assert task["_content_reference_path"] is None
    assert task["_planned_provider"] == api_client.PROVIDER_CHATGPT


def test_prepare_task_provider_metadata_marks_style_and_content_when_both_refs_exist(tmp_path, monkeypatch):
    monkeypatch.setattr(
        mode_multiformat_with_refs_api,
        "repo_path",
        lambda *parts: tmp_path.joinpath(*parts),
    )
    style_path = tmp_path / "style.png"
    content_dir = tmp_path / "data" / "images" / "лицо"
    content_dir.mkdir(parents=True)
    content_path = content_dir / "1_лицо.png"
    style_path.write_bytes(b"style")
    content_path.write_bytes(b"content")
    task = {
        "card_number": 1,
        "card_name": "Test",
        "pair_number": 1,
        "side": "лицо",
        "prompt_text": "Prompt",
    }

    mode_multiformat_with_refs_api._prepare_task_provider_metadata([task], _style_settings(style_path))

    assert task["_reference_mode"] == api_client.REFERENCE_MODE_STYLE_AND_CONTENT
    assert task["_style_reference_path"] == str(style_path)
    assert task["_content_reference_path"] == str(content_path)


def test_generate_single_image_api_uses_style_reference_and_logs_sent_prompt(tmp_path, monkeypatch):
    style_path = tmp_path / "style.png"
    style_path.write_bytes(b"style")
    settings = _style_settings(style_path)
    task = {
        "card_number": 1,
        "card_name": "Test",
        "pair_number": 1,
        "side": "лицо",
        "prompt_text": "draw a lighthouse",
    }
    log_lines = []
    captured = {}

    monkeypatch.setattr(
        mode_multiformat_with_refs_api,
        "write_log_line",
        lambda _log_file, line: log_lines.append(line),
    )
    monkeypatch.setattr(mode_multiformat_with_refs_api.api_client, "save_image_bytes", lambda *_args, **_kwargs: True)

    def fake_generate(**kwargs):
        captured.update(kwargs)
        return b"png", None

    monkeypatch.setattr(mode_multiformat_with_refs_api.api_client, "generate_image_with_references", fake_generate)

    ok = mode_multiformat_with_refs_api._generate_single_image_api(
        task,
        {api_client.PROVIDER_CHATGPT: object()},
        settings,
        log_file=object(),
    )

    assert ok is True
    assert captured["style_reference_image_path"] == str(style_path)
    assert captured["content_reference_image_path"] is None
    assert captured["sent_prompt"].startswith("ar - 4:3. Reference image 1 is the STYLE REFERENCE only.")
    assert captured["sent_prompt"].endswith("draw a lighthouse")
    assert any(line.startswith("[PROMPT_RAW_BEGIN]") for line in log_lines)
    assert any(line.startswith("[PROMPT_SENT_BEGIN]") and "reference_mode=style" in line for line in log_lines)
    assert "draw a lighthouse" in log_lines
    assert not any("sk-" in line for line in log_lines)


def test_generate_single_image_api_hides_prompt_when_logging_disabled(tmp_path, monkeypatch):
    style_path = tmp_path / "style.png"
    style_path.write_bytes(b"style")
    settings = _style_settings(style_path, log_prompts=False)
    task = {
        "card_number": 1,
        "card_name": "Test",
        "pair_number": 1,
        "side": "лицо",
        "prompt_text": "draw a hidden lighthouse",
    }
    log_lines = []

    monkeypatch.setattr(
        mode_multiformat_with_refs_api,
        "write_log_line",
        lambda _log_file, line: log_lines.append(line),
    )
    monkeypatch.setattr(mode_multiformat_with_refs_api.api_client, "save_image_bytes", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        mode_multiformat_with_refs_api.api_client,
        "generate_image_with_references",
        lambda **_kwargs: (b"png", None),
    )

    ok = mode_multiformat_with_refs_api._generate_single_image_api(
        task,
        {api_client.PROVIDER_CHATGPT: object()},
        settings,
        log_file=object(),
    )

    assert ok is True
    assert any(line.startswith("[PROMPT_LENGTHS]") for line in log_lines)
    assert not any("[PROMPT_RAW_BEGIN]" in line for line in log_lines)
    assert not any("draw a hidden lighthouse" == line for line in log_lines)
