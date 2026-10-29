"""Background CLI -> real SDK requests, using an offline HTTP transport only."""
import base64
import json

import httpx
import pytest
from openai import OpenAI

from sites.aistudio import mode_multiformat_with_refs_api as mode
from utils import agent_cli, api_client, settings_store


def offline_client(requests):
    def respond(request):
        requests.append((request.url.path, request.headers.get("content-type", ""), request.read()))
        return httpx.Response(200, json={"data": [{"b64_json": base64.b64encode(b"returned-png").decode()}]})
    return OpenAI(api_key="sk-test-offline-only", base_url="https://example.invalid/v1",
                  http_client=httpx.Client(transport=httpx.MockTransport(respond)))


def settings():
    return {"API_PROVIDER": "chatgpt", "API_PROVIDER_WITH_REFS": "chatgpt",
            "API_MODEL_CHATGPT": "gpt-image-2.5-sunburst", "API_LOG_PROMPTS": False,
            "API_IMAGE_SIZE": "1024x1024"}


@pytest.mark.parametrize("reference", [False, True])
def test_cli_background_reaches_real_sdk_http_request(tmp_path, monkeypatch, reference):
    original = settings()
    monkeypatch.setattr(agent_cli, "load_settings", lambda: original)
    style = tmp_path / "style.png"
    style.write_bytes(b"style-reference")
    args = agent_cli._build_parser().parse_args([
        "agent-run-api", "--prompts", str(tmp_path / "prompts.txt"),
        "--output-base-dir", str(tmp_path / "output"), "--background", "transparent",
        *( ["--style-ref", str(style)] if reference else ["--no-style-ref"] )])
    runtime = agent_cli._settings_from_args(args)
    assert "API_IMAGE_BACKGROUND" not in original
    assert "API_IMAGE_BACKGROUND" not in settings_store.sanitize_for_storage(runtime)
    requests = []
    client = offline_client(requests)
    monkeypatch.setattr(mode, "write_log_line", lambda *_: None)
    saved = []
    monkeypatch.setattr(api_client, "save_image_bytes", lambda data, name: saved.append(data) or True)
    task = {"card_number": 990001, "card_name": "Test", "pair_number": 1,
            "side": "лицо", "prompt_text": "Isolated actor"}
    assert mode._generate_single_image_api(task, {"chatgpt": client}, runtime, object())
    assert saved == [b"returned-png"]
    assert len(requests) == 1
    path, content_type, body = requests[0]
    if reference:
        assert path == "/v1/images/edits"
        assert content_type.startswith("multipart/form-data")
        assert b'name="background"\r\n\r\ntransparent' in body
        assert b'name="output_format"\r\n\r\npng' in body
    else:
        assert path == "/v1/images/generations"
        payload = json.loads(body)
        assert payload["background"] == "transparent"
        assert payload["output_format"] == "png"
        assert payload["model"] == "gpt-image-2.5-sunburst"
    client.close()


@pytest.mark.parametrize("route", ["single", "style_and_content"])
def test_all_reference_paths_send_transparent_background(tmp_path, route):
    paths = [tmp_path / "style.png", tmp_path / "content.png"]
    for path in paths:
        path.write_bytes(b"reference")
    requests = []
    client = offline_client(requests)
    common = dict(client=client, prompt="Actor", provider="chatgpt",
                  model="gpt-image-2.5-sunburst", background="transparent")
    if route == "single":
        data, error = api_client.generate_image_with_reference(reference_image_path=str(paths[1]), **common)
    else:
        data, error = api_client.generate_image_with_references(
            style_reference_image_path=str(paths[0]), content_reference_image_path=str(paths[1]), **common)
    assert error is None
    assert data == b"returned-png"
    assert len(requests) == 1
    assert b'name="background"\r\n\r\ntransparent' in requests[0][2]
    client.close()


@pytest.mark.parametrize("background", [None, "opaque", "auto"])
def test_default_and_explicit_opaque_background_request(tmp_path, background):
    requests = []
    client = offline_client(requests)
    _, error = api_client.generate_image(client, "Actor", provider="chatgpt", background=background)
    assert error is None
    payload = json.loads(requests[0][2])
    if background is None:
        assert "background" not in payload
    else:
        assert payload["background"] == background
    assert "output_format" not in payload
    client.close()


def test_plan_exposes_background_without_calling_api(tmp_path, monkeypatch, capsys):
    prompts = tmp_path / "prompts.txt"
    prompts.write_text("Карточка 1 лицо Test - Промпт 1: Actor\n", encoding="utf-8")
    monkeypatch.setattr(agent_cli, "load_settings", settings)
    monkeypatch.setattr(api_client, "init_client", lambda *_a, **_kw: pytest.fail("Plan called an API client"))
    result = agent_cli.main(["agent-plan", "--prompts", str(prompts), "--output-base-dir", str(tmp_path),
                             "--background", "transparent", "--no-style-ref", "--json"])
    assert result == 0
    assert json.loads(capsys.readouterr().out)["image_background"] == "transparent"


def test_unsupported_provider_background_fails_before_request():
    class NoCalls:
        def __getattr__(self, name):
            pytest.fail("Unsupported provider called a client")
    data, error = api_client.generate_image(NoCalls(), "Actor", provider="nanobanana", background="transparent")
    assert data is None
    assert "ChatGPT" in error
    assert api_client.validate_image_background_settings({"API_IMAGE_BACKGROUND": "transparent"})
