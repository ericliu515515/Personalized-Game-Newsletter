import os
import sys
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("SEARCH_MODEL", "test-search-model")


def test_full_requested_console_list_is_normalized_before_rejection(monkeypatch):
    import validation
    from models import NOT_CONSOLE_SPECIFIC, NewsItem
    from response import TokenUsage

    requested_consoles = ["PC", "Switch and Switch 2"]
    item = NewsItem(
        title="General game update",
        summary="A general update for a requested tag.",
        source_name="Example News",
        source_url="https://example.com/news/general-game-update",
        consoles=requested_consoles,
        tag="Pokemon",
    )
    consoles_seen_by_rejection = []

    def fake_get_news_items(**kwargs):
        return [item], TokenUsage(input_tokens=1, output_tokens=2, total_tokens=3)

    def fake_reject_news_item(item, requested_tags):
        consoles_seen_by_rejection.append(list(item.consoles))
        return SimpleNamespace(accepted=True), TokenUsage(
            input_tokens=4,
            output_tokens=5,
            total_tokens=9,
        )

    monkeypatch.setattr(validation, "get_news_items", fake_get_news_items)
    monkeypatch.setattr(validation, "load_query_history_items", lambda: [])
    monkeypatch.setattr(validation, "reject_news_item", fake_reject_news_item)
    monkeypatch.setattr(validation, "url_is_live", lambda source_url: True)

    validated_items, token_usage, message = validation.get_valid_news_items(
        consoles=requested_consoles,
        tags=["Pokemon"],
        target_count=1,
        max_attempts=1,
        temperature=1,
    )

    assert consoles_seen_by_rejection == [[NOT_CONSOLE_SPECIFIC]]
    assert validated_items[0].consoles == [NOT_CONSOLE_SPECIFIC]
    assert token_usage.total_tokens == 12
    assert message == "1/1"


def test_get_valid_news_items_returns_shortfall_message_without_raising(monkeypatch):
    import validation
    from models import NewsItem
    from response import TokenUsage

    news_items = [
        NewsItem(
            title="News item 1",
            summary="Summary 1.",
            source_name="Example News",
            source_url="https://example.com/news/1",
            consoles=["PC"],
            tag="Pokemon",
        ),
        NewsItem(
            title="News item 2",
            summary="Summary 2.",
            source_name="Example News",
            source_url="https://example.com/news/2",
            consoles=["PC"],
            tag="Pokemon",
        ),
    ]

    def fake_get_news_items(**kwargs):
        return news_items, TokenUsage(input_tokens=1, output_tokens=2, total_tokens=3)

    def fake_reject_news_item(item, requested_tags):
        return SimpleNamespace(accepted=True), TokenUsage(
            input_tokens=4,
            output_tokens=5,
            total_tokens=9,
        )

    monkeypatch.setattr(validation, "get_news_items", fake_get_news_items)
    monkeypatch.setattr(validation, "load_query_history_items", lambda: [])
    monkeypatch.setattr(validation, "reject_news_item", fake_reject_news_item)
    monkeypatch.setattr(validation, "url_is_live", lambda source_url: True)

    validated_items, token_usage, message = validation.get_valid_news_items(
        consoles=["PC"],
        tags=["Pokemon"],
        target_count=4,
        max_attempts=1,
        temperature=1,
    )

    assert len(validated_items) == 2
    assert token_usage.total_tokens == 21
    assert message == "2/4"


def test_get_valid_news_items_passes_query_history_to_seen_items(monkeypatch):
    import validation
    from models import NewsItem
    from response import TokenUsage

    historical_item = NewsItem(
        title="Old Pokemon news",
        summary="Old summary.",
        source_name="Example News",
        source_url="https://example.com/news/old-pokemon",
        consoles=["PC"],
        tag="Pokemon",
    )
    new_item = NewsItem(
        title="New Pokemon news",
        summary="New summary.",
        source_name="Example News",
        source_url="https://example.com/news/new-pokemon",
        consoles=["PC"],
        tag="Pokemon",
    )
    seen_items_from_search_call = []

    def fake_get_news_items(**kwargs):
        seen_items_from_search_call.extend(kwargs["seen_items"])
        return [new_item], TokenUsage(input_tokens=1, output_tokens=2, total_tokens=3)

    def fake_reject_news_item(item, requested_tags):
        return SimpleNamespace(accepted=True), TokenUsage(
            input_tokens=4,
            output_tokens=5,
            total_tokens=9,
        )

    monkeypatch.setattr(
        validation,
        "load_query_history_items",
        lambda: [historical_item],
    )
    monkeypatch.setattr(validation, "get_news_items", fake_get_news_items)
    monkeypatch.setattr(validation, "reject_news_item", fake_reject_news_item)
    monkeypatch.setattr(validation, "url_is_live", lambda source_url: True)

    validated_items, token_usage, message = validation.get_valid_news_items(
        consoles=["PC"],
        tags=["Pokemon"],
        target_count=1,
        max_attempts=1,
        temperature=1,
    )

    assert [item.source_url for item in seen_items_from_search_call] == [
        "https://example.com/news/old-pokemon"
    ]
    assert validated_items[0].source_url == "https://example.com/news/new-pokemon"
    assert token_usage.total_tokens == 12
    assert message == "1/1"
