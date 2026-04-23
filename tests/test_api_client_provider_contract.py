"""Focused checks for provider-specific API helpers."""

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
