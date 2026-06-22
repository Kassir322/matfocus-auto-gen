"""Focused checks for provider-specific API helpers."""

import base64

from utils import api_client


def test_chatgpt_prompt_prepends_aspect_ratio():
    prompt = api_client.build_prompt("draw a lighthouse", api_client.PROVIDER_CHATGPT, "4:3")
    assert prompt == "ar - 4:3. draw a lighthouse"


def test_get_api_key_prefers_provider_specific_field_over_legacy():
    settings = {
        "API_KEY": "AIzaSyLEGACY_KEY_12345678901234567890",
        "API_KEY_NANOBANANA": "AIzaSyNEW_KEY_1234567890123456789012",
        "API_KEY_CHATGPT": "sk-test-chatgpt-key-1234567890",
    }

    assert api_client.get_api_key(settings, api_client.PROVIDER_NANOBANANA) == settings["API_KEY_NANOBANANA"]
    assert api_client.get_api_key(settings, api_client.PROVIDER_CHATGPT) == settings["API_KEY_CHATGPT"]


def test_chatgpt_key_validation_accepts_non_google_key():
    valid, error = api_client.check_api_key_format("sk-test-chatgpt-key-1234567890", provider=api_client.PROVIDER_CHATGPT)
    assert valid is True
    assert error == ""


class _FakeImageItem:
    b64_json = base64.b64encode(b"fake-png").decode("ascii")


class _FakeImageResponse:
    data = [_FakeImageItem()]


class _FakeImages:
    def __init__(self):
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeImageResponse()

    def edit(self, **kwargs):
        self.calls.append(kwargs)
        assert kwargs["image"].read() == b"reference"
        return _FakeImageResponse()


class _FakeOpenAIClient:
    def __init__(self):
        self.images = _FakeImages()


def test_chatgpt_reference_generation_uses_image_edit(tmp_path):
    reference_path = tmp_path / "ref.png"
    reference_path.write_bytes(b"reference")
    client = _FakeOpenAIClient()

    image_bytes, error = api_client.generate_image_with_reference(
        client=client,
        prompt="draw a lighthouse",
        reference_image_path=str(reference_path),
        model="gpt-image-2",
        aspect_ratio="4:3",
        provider=api_client.PROVIDER_CHATGPT,
        quality="medium",
    )

    assert error is None
    assert image_bytes == b"fake-png"
    assert len(client.images.calls) == 1
    call = client.images.calls[0]
    assert call["model"] == "gpt-image-2"
    assert call["prompt"] == "ar - 4:3. draw a lighthouse"
    assert call["size"] == "auto"
    assert call["quality"] == "medium"


def test_chatgpt_generation_uses_explicit_supported_image_size():
    client = _FakeOpenAIClient()

    image_bytes, error = api_client.generate_image(
        client=client,
        prompt="draw a lighthouse",
        model="gpt-image-2",
        aspect_ratio="4:3",
        image_size="1536x1024",
        provider=api_client.PROVIDER_CHATGPT,
        quality="low",
    )

    assert error is None
    assert image_bytes == b"fake-png"
    assert client.images.calls[0]["size"] == "1536x1024"


def test_chatgpt_generation_passes_legacy_image_size_to_api():
    client = _FakeOpenAIClient()

    image_bytes, error = api_client.generate_image(
        client=client,
        prompt="draw a lighthouse",
        model="gpt-image-2",
        aspect_ratio="4:3",
        image_size="2K",
        provider=api_client.PROVIDER_CHATGPT,
        quality="low",
    )

    assert error is None
    assert image_bytes == b"fake-png"
    assert client.images.calls[0]["size"] == "2K"


def test_chatgpt_generation_passes_arbitrary_image_size_to_api():
    client = _FakeOpenAIClient()

    image_bytes, error = api_client.generate_image(
        client=client,
        prompt="draw a lighthouse",
        model="gpt-image-2",
        aspect_ratio="4:3",
        image_size="21:10",
        provider=api_client.PROVIDER_CHATGPT,
        quality="low",
    )

    assert error is None
    assert image_bytes == b"fake-png"
    assert client.images.calls[0]["size"] == "21:10"


def test_nanobanana_image_size_is_not_normalized_to_chatgpt_values():
    image_size, error = api_client.normalize_image_size_for_provider(api_client.PROVIDER_NANOBANANA, "2K")

    assert error is None
    assert image_size == "2K"


def test_session_output_folder_includes_project_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(api_client, "datetime", type("FakeDateTime", (), {"now": staticmethod(lambda: _FakeNow())}))

    api_client.reset_session_folder()
    output_dir = api_client.get_session_output_folder({"OUTPUT_PROJECT_NAME": "countries"})

    assert output_dir == "generated_images\\2026-06-14_18-30-00_countries"


def test_session_output_folder_sanitizes_project_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(api_client, "datetime", type("FakeDateTime", (), {"now": staticmethod(lambda: _FakeNow())}))

    api_client.reset_session_folder()
    output_dir = api_client.get_session_output_folder({"OUTPUT_PROJECT_NAME": "  Моя  игра: cards/refs?  "})

    assert output_dir == "generated_images\\2026-06-14_18-30-00_Моя_игра_cards_refs"


def test_session_output_folder_uses_project_fallback(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(api_client, "datetime", type("FakeDateTime", (), {"now": staticmethod(lambda: _FakeNow())}))

    api_client.reset_session_folder()
    output_dir = api_client.get_session_output_folder({"OUTPUT_PROJECT_NAME": " : / ? "})

    assert output_dir == "generated_images\\2026-06-14_18-30-00_project"


class _FakeNow:
    def strftime(self, _format):
        return "2026-06-14_18-30-00"
