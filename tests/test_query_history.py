import json
import sys
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))


def make_news_item():
    from models import ValidatedNewsItem

    return ValidatedNewsItem(
        title="Pokemon update",
        summary="A concise news summary.",
        source_name="Example News",
        source_url="https://example.com/news/pokemon-update",
        consoles=["PC"],
        tag="Pokemon",
        url_validity=True,
    )


def test_append_query_history_writes_jsonl_record(tmp_path):
    from query_history import append_query_history

    history_path = tmp_path / "query_history.jsonl"
    token_usage = SimpleNamespace(
        input_tokens=10,
        output_tokens=20,
        total_tokens=30,
    )

    append_query_history(
        tags=["Pokemon"],
        consoles=["PC"],
        target_count=3,
        max_attempts=10,
        temperature=1,
        validated_news_items=[make_news_item()],
        token_usage=token_usage,
        message="1/3",
        history_path=history_path,
    )

    history_lines = history_path.read_text(encoding="utf-8").splitlines()
    assert len(history_lines) == 1

    record = json.loads(history_lines[0])
    assert record["timestamp"].endswith("Z")
    assert record["tags"] == ["Pokemon"]
    assert record["consoles"] == ["PC"]
    assert record["target_count"] == 3
    assert record["max_attempts"] == 10
    assert record["temperature"] == 1
    assert record["found_count"] == 1
    assert record["message"] == "1/3"
    assert record["token_usage"] == {
        "input_tokens": 10,
        "output_tokens": 20,
        "total_tokens": 30,
    }
    assert record["items"][0]["title"] == "Pokemon update"
    assert record["error"] is None


def test_append_query_history_writes_failed_run_record(tmp_path):
    from query_history import append_query_history

    history_path = tmp_path / "query_history.jsonl"

    append_query_history(
        tags=["Pokemon"],
        consoles=["PC"],
        target_count=3,
        max_attempts=10,
        temperature=1,
        validated_news_items=[],
        token_usage=None,
        message="0/3",
        error="RuntimeError: failed",
        history_path=history_path,
    )

    record = json.loads(history_path.read_text(encoding="utf-8"))
    assert record["found_count"] == 0
    assert record["items"] == []
    assert record["token_usage"] is None
    assert record["error"] == "RuntimeError: failed"


def test_load_query_history_items_returns_seen_news_items(tmp_path):
    from query_history import append_query_history, load_query_history_items

    history_path = tmp_path / "query_history.jsonl"

    append_query_history(
        tags=["Pokemon"],
        consoles=["PC"],
        target_count=3,
        max_attempts=10,
        temperature=1,
        validated_news_items=[make_news_item()],
        token_usage=None,
        message="1/3",
        history_path=history_path,
    )

    seen_items = load_query_history_items(history_path)

    assert len(seen_items) == 1
    assert seen_items[0].title == "Pokemon update"
    assert seen_items[0].source_url == "https://example.com/news/pokemon-update"


def test_load_query_history_items_deduplicates_by_url(tmp_path):
    from query_history import append_query_history, load_query_history_items

    history_path = tmp_path / "query_history.jsonl"
    news_item = make_news_item()

    append_query_history(
        tags=["Pokemon"],
        consoles=["PC"],
        target_count=3,
        max_attempts=10,
        temperature=1,
        validated_news_items=[news_item],
        token_usage=None,
        message="1/3",
        history_path=history_path,
    )
    append_query_history(
        tags=["Pokemon"],
        consoles=["PC"],
        target_count=3,
        max_attempts=10,
        temperature=1,
        validated_news_items=[news_item],
        token_usage=None,
        message="1/3",
        history_path=history_path,
    )

    seen_items = load_query_history_items(history_path)

    assert len(seen_items) == 1
