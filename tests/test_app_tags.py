import json
import os
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("SEARCH_MODEL", "test-search-model")


def test_load_settings_reads_json_object(tmp_path):
    from load_settings import load_settings

    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps({"consoles": ["PC"], "tags": ["Pokemon"]}))

    assert load_settings(settings_path) == {
        "consoles": ["PC"],
        "tags": ["Pokemon"],
    }


def test_load_settings_rejects_non_object(tmp_path):
    from load_settings import load_settings

    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps(["Pokemon"]))

    with pytest.raises(ValueError, match="JSON object"):
        load_settings(settings_path)


def test_settings_tags_strips_empty_parts():
    from load_settings import settings_tags

    assert settings_tags({"tags": ["Pokemon", "Dragon's Dogma", "", "Hades "]}) == [
        "Pokemon",
        "Dragon's Dogma",
        "Hades",
    ]


def test_settings_tags_rejects_non_list_values():
    from load_settings import settings_tags

    with pytest.raises(ValueError, match="tags"):
        settings_tags({"tags": "Pokemon"})


def test_combine_tags_preserves_order_and_removes_duplicates():
    from load_settings import combine_tags

    assert combine_tags(
        ["Pokemon", "Hades"],
        ["Hades", "Dragon's Dogma", "Pokemon"],
    ) == ["Pokemon", "Hades", "Dragon's Dogma"]


def test_settings_consoles_accepts_exact_console_categories():
    from load_settings import settings_consoles

    assert settings_consoles(
        {"consoles": ["PC", "Switch and Switch 2", "XBOX"]}
    ) == [
        "PC",
        "Switch and Switch 2",
        "XBOX",
    ]


def test_settings_consoles_rejects_unknown_console():
    from load_settings import settings_consoles

    with pytest.raises(ValueError, match="Unknown console"):
        settings_consoles({"consoles": ["mobile"]})


def test_settings_consoles_does_not_map_lowercase_aliases():
    from load_settings import settings_consoles

    with pytest.raises(ValueError, match="Unknown console"):
        settings_consoles({"consoles": ["pc"]})


def test_settings_consoles_requires_at_least_one_console():
    from load_settings import settings_consoles

    with pytest.raises(ValueError, match="at least one"):
        settings_consoles({"consoles": []})


def test_settings_username_strips_whitespace():
    from load_settings import settings_username

    assert settings_username({"username": " Eric "}) == "Eric"


def test_settings_username_rejects_empty_value():
    from load_settings import settings_username

    with pytest.raises(ValueError, match="username"):
        settings_username({"username": ""})


def test_settings_username_rejects_non_string_value():
    from load_settings import settings_username

    with pytest.raises(ValueError, match="username"):
        settings_username({"username": ["Eric"]})


def test_followed_tags_concatenates_settings_with_built_ins(monkeypatch):
    import load_settings as settings

    monkeypatch.setattr(
        settings,
        "SETTINGS",
        {"tags": ["Pokemon", "Dragon's Dogma"]},
    )

    followed_tags = settings.followed_tags()

    assert followed_tags[:2] == ["Pokemon", "Dragon's Dogma"]
    assert followed_tags[-len(settings.BUILT_IN_TAGS):] == settings.BUILT_IN_TAGS
    assert followed_tags.count("Pokemon") == 1
