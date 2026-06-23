"""Focused checks for provider-specific API helpers."""

import base64

from utils import api_client


def test_chatgpt_prompt_prepends_aspect_ratio():
    prompt = api_client.build_prompt("draw a lighthouse", api_client.PROVIDER_CHATGPT, "4:3")
    assert prompt == "ar - 4:3. draw a lighthouse"


def test_build_provider_prompt_adds_chatgpt_style_reference_instruction():
    prompt = api_client.build_provider_prompt(
        "draw a lighthouse",
        api_client.PROVIDER_CHATGPT,
        "4:3",
        api_client.REFERENCE_MODE_STYLE,
    )

    assert prompt.startswith("ar - 4:3. Reference image 1 is the STYLE REFERENCE only.")
    assert "Reference image 2 is the CONTENT REFERENCE only." not in prompt
    assert prompt.endswith("draw a lighthouse")


def test_build_provider_prompt_adds_chatgpt_style_and_content_instruction():
    prompt = api_client.build_provider_prompt(
        "draw a lighthouse",
        api_client.PROVIDER_CHATGPT,
        "4:3",
        api_client.REFERENCE_MODE_STYLE_AND_CONTENT,
    )

    style_index = prompt.index("Reference image 1 is the STYLE REFERENCE only.")
    content_index = prompt.index("Reference image 2 is the CONTENT REFERENCE only.")
    assert style_index < content_index
    assert prompt.count("ar - 4:3.") == 1
    assert prompt.endswith("draw a lighthouse")


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
        image_arg = kwargs["image"]
        if isinstance(image_arg, list):
            kwargs["_image_bytes"] = [image_file.read() for image_file in image_arg]
        else:
            kwargs["_image_bytes"] = [image_arg.read()]
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
    assert call["_image_bytes"] == [b"reference"]
    assert call["size"] == "auto"
    assert call["quality"] == "medium"


def test_chatgpt_style_and_content_references_use_ordered_image_edit(tmp_path):
    style_path = tmp_path / "style.png"
    content_path = tmp_path / "content.png"
    style_path.write_bytes(b"style")
    content_path.write_bytes(b"content")
    client = _FakeOpenAIClient()

    image_bytes, error = api_client.generate_image_with_references(
        client=client,
        prompt="draw a lighthouse",
        style_reference_image_path=str(style_path),
        content_reference_image_path=str(content_path),
        model="gpt-image-2",
        aspect_ratio="4:3",
        provider=api_client.PROVIDER_CHATGPT,
        quality="low",
    )

    assert error is None
    assert image_bytes == b"fake-png"
    call = client.images.calls[0]
    assert call["_image_bytes"] == [b"style", b"content"]
    assert "Reference image 1 is the STYLE REFERENCE only." in call["prompt"]
    assert "Reference image 2 is the CONTENT REFERENCE only." in call["prompt"]
    assert call["prompt"].endswith("draw a lighthouse")


def test_chatgpt_style_only_reference_uses_single_image_edit(tmp_path):
    style_path = tmp_path / "style.png"
    style_path.write_bytes(b"style")
    client = _FakeOpenAIClient()

    image_bytes, error = api_client.generate_image_with_references(
        client=client,
        prompt="draw a lighthouse",
        style_reference_image_path=str(style_path),
        model="gpt-image-2",
        aspect_ratio="4:3",
        provider=api_client.PROVIDER_CHATGPT,
        quality="low",
    )

    assert error is None
    assert image_bytes == b"fake-png"
    call = client.images.calls[0]
    assert call["_image_bytes"] == [b"style"]
    assert "Reference image 1 is the STYLE REFERENCE only." in call["prompt"]
    assert "Reference image 2 is the CONTENT REFERENCE only." not in call["prompt"]


def test_chatgpt_content_only_references_keep_old_prompt_shape(tmp_path):
    content_path = tmp_path / "content.png"
    content_path.write_bytes(b"content")
    client = _FakeOpenAIClient()

    image_bytes, error = api_client.generate_image_with_references(
        client=client,
        prompt="draw a lighthouse",
        content_reference_image_path=str(content_path),
        model="gpt-image-2",
        aspect_ratio="4:3",
        provider=api_client.PROVIDER_CHATGPT,
        quality="low",
    )

    assert error is None
    assert image_bytes == b"fake-png"
    call = client.images.calls[0]
    assert call["_image_bytes"] == [b"content"]
    assert call["prompt"] == "ar - 4:3. draw a lighthouse"


def test_missing_style_reference_returns_error_before_api_call(tmp_path):
    client = _FakeOpenAIClient()

    image_bytes, error = api_client.generate_image_with_references(
        client=client,
        prompt="draw a lighthouse",
        style_reference_image_path=str(tmp_path / "missing.png"),
        model="gpt-image-2",
        aspect_ratio="4:3",
        provider=api_client.PROVIDER_CHATGPT,
        quality="low",
    )

    assert image_bytes is None
    assert "не найдено" in error
    assert client.images.calls == []


def test_chatgpt_generation_uses_sent_prompt_exactly():
    client = _FakeOpenAIClient()

    image_bytes, error = api_client.generate_image(
        client=client,
        prompt="draw a lighthouse",
        model="gpt-image-2",
        aspect_ratio="4:3",
        provider=api_client.PROVIDER_CHATGPT,
        quality="low",
        sent_prompt="already final prompt",
    )

    assert error is None
    assert image_bytes == b"fake-png"
    assert client.images.calls[0]["prompt"] == "already final prompt"


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
