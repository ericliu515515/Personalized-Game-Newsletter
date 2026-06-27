import json
from pathlib import Path
from typing import Any, get_args

from models import ConsoleCategory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PATH = PROJECT_ROOT / "config" / "settings.json"

BUILT_IN_TAGS = [
    "Handheld Gaming Hardware",
    "Next Generataional Hardware",
    "Industry",
    "Other Videogame",
]


def combine_tags(*tag_groups: list[str]) -> list[str]:
    tags: list[str] = []
    seen_tags: set[str] = set()

    for tag_group in tag_groups:
        for tag in tag_group:
            normalized_tag = tag.strip()

            if not normalized_tag or normalized_tag in seen_tags:
                continue

            tags.append(normalized_tag)
            seen_tags.add(normalized_tag)

    return tags


def load_settings(settings_path: Path = SETTINGS_PATH) -> dict[str, Any]:
    try:
        with settings_path.open() as settings_file:
            settings = json.load(settings_file)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Settings file not found: {settings_path}. "
            "Create config/settings.json first."
        ) from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Settings file is not valid JSON: {settings_path}") from exc

    if not isinstance(settings, dict):
        raise ValueError("Settings file must contain a JSON object.")

    return settings


def settings_tags(settings: dict[str, Any]) -> list[str]:
    tags = settings.get("tags", [])

    if not isinstance(tags, list):
        raise ValueError('settings.json field "tags" must be a list of strings.')

    if not all(isinstance(tag, str) for tag in tags):
        raise ValueError('settings.json field "tags" must contain only strings.')

    return [tag.strip() for tag in tags if tag.strip()]


def settings_consoles(settings: dict[str, Any]) -> list[ConsoleCategory]:
    console_choices = settings.get("consoles", [])

    if not isinstance(console_choices, list):
        raise ValueError('settings.json field "consoles" must be a list of strings.')

    if not all(isinstance(choice, str) for choice in console_choices):
        raise ValueError(
            'settings.json field "consoles" must contain only strings.'
        )

    consoles: list[ConsoleCategory] = []
    seen_consoles: set[ConsoleCategory] = set()
    valid_consoles = set(get_args(ConsoleCategory))

    for console_choice in console_choices:
        console = console_choice.strip()

        if console in seen_consoles:
            continue

        if console not in valid_consoles:
            valid_console_text = ", ".join(get_args(ConsoleCategory))
            raise ValueError(
                f"Unknown console: {console_choice}. "
                f"Keep one of the provided console values: {valid_console_text}."
            )

        consoles.append(console)
        seen_consoles.add(console)

    if not consoles:
        raise ValueError('settings.json field "consoles" must select at least one item.')

    return consoles


def settings_username(settings: dict[str, Any]) -> str:
    username = settings.get("username", "")

    if not isinstance(username, str):
        raise ValueError('settings.json field "username" must be a string.')

    normalized_username = username.strip()

    if not normalized_username:
        raise ValueError('settings.json field "username" must not be empty.')

    return normalized_username


def followed_tags() -> list[str]:
    return combine_tags(settings_tags(SETTINGS), BUILT_IN_TAGS)


SETTINGS = load_settings()
USERNAME = settings_username(SETTINGS)
CONSOLES = settings_consoles(SETTINGS)
TAGS = followed_tags()
