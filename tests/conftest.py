"""Pytest safeguards for legacy tests.

The legacy `tests/test_suite.py` still exercises the old config/core layer. That
layer writes `data/settings.json` directly and only preserves legacy keys, so it
must never run against the user's real v2 settings file.
"""

import pytest


@pytest.fixture(autouse=True)
def isolate_legacy_settings_manager(request, monkeypatch, tmp_path):
    if request.module.__name__ != "tests.test_suite":
        return

    from config.settings import SettingsManager

    original_init = SettingsManager.__init__

    def isolated_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.settings_file = str(tmp_path / "legacy_settings.json")

    monkeypatch.setattr(SettingsManager, "__init__", isolated_init)
