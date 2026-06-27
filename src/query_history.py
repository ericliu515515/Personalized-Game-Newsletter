import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from models import ConsoleCategory, NewsItem, ValidatedNewsItem

PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUERY_HISTORY_PATH = PROJECT_ROOT / "data" / "query_history.jsonl"


def current_utc_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def token_usage_to_dict(token_usage: Any | None) -> dict[str, int] | None:
    if token_usage is None:
        return None

    return {
        "input_tokens": token_usage.input_tokens,
        "output_tokens": token_usage.output_tokens,
        "total_tokens": token_usage.total_tokens,
    }


def append_query_history(
    *,
    tags: list[str],
    consoles: list[ConsoleCategory],
    target_count: int,
    max_attempts: int,
    temperature: float,
    validated_news_items: list[ValidatedNewsItem],
    token_usage: Any | None,
    message: str,
    error: str | None = None,
    history_path: Path = QUERY_HISTORY_PATH,
) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": current_utc_timestamp(),
        "tags": tags,
        "consoles": consoles,
        "target_count": target_count,
        "max_attempts": max_attempts,
        "temperature": temperature,
        "found_count": len(validated_news_items),
        "message": message,
        "token_usage": token_usage_to_dict(token_usage),
        "items": [item.model_dump() for item in validated_news_items],
        "error": error,
    }

    with history_path.open("a", encoding="utf-8") as history_file:
        history_file.write(json.dumps(record, ensure_ascii=False))
        history_file.write("\n")


def load_query_history_items(
    history_path: Path = QUERY_HISTORY_PATH,
) -> list[NewsItem]:
    if not history_path.exists():
        return []

    seen_items: list[NewsItem] = []
    seen_urls: set[str] = set()

    with history_path.open(encoding="utf-8") as history_file:
        for line_number, line in enumerate(history_file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Query history line {line_number} is not valid JSON: "
                    f"{history_path}"
                ) from exc

            items = record.get("items", [])

            if not isinstance(items, list):
                continue

            for item_data in items:
                if not isinstance(item_data, dict):
                    continue

                try:
                    item = NewsItem(**item_data)
                except ValidationError:
                    continue

                if item.source_url in seen_urls:
                    continue

                seen_items.append(item)
                seen_urls.add(item.source_url)

    return seen_items
