"""Focused checks for OpenAI Costs API helper."""

import io
import json

from utils import api_client


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_fetch_openai_costs_sums_amounts(monkeypatch):
    payload = {
        "object": "page",
        "data": [
            {
                "result": [
                    {"amount": {"currency": "usd", "value": 1.20}},
                    {"amount": {"currency": "usd", "value": 0.29}},
                ]
            }
        ],
    }

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout=30: _FakeResponse(payload))

    amount, error = api_client.fetch_openai_costs("sk-test", 100, 200)

    assert error is None
    assert amount == 1.49


def test_fetch_openai_costs_returns_error_when_empty(monkeypatch):
    payload = {"object": "page", "data": []}
    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout=30: _FakeResponse(payload))

    amount, error = api_client.fetch_openai_costs("sk-test", 100, 200)

    assert amount is None
    assert "нет данных" in error

