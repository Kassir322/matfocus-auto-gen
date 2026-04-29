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
