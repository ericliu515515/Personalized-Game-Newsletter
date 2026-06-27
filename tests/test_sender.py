import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))


def make_news_item(index: int, title: str | None = None):
    from models import ValidatedNewsItem

    consoles = ["PC"]

    if index == 2:
        consoles = ["Switch and Switch 2"]
    elif index == 3:
        consoles = ["not console-specific"]

    return ValidatedNewsItem(
        title=title or f"News item {index}",
        summary=f"Summary for news item {index}.",
        source_name=f"Source {index}",
        source_url=f"https://example.com/news/{index}?a=1&b=2",
        consoles=consoles,
        tag="Pokemon",
        url_validity=True,
    )


def test_build_news_email_formats_empty_digest():
    from sender import build_news_email

    text_body, html_body = build_news_email([])

    assert "Sorry, PVN could not find any validated news items today." in text_body
    assert "Sorry, PVN could not find any validated news items today." in html_body
    assert "URL:" not in text_body
    assert "Read article" not in html_body


def test_build_news_email_formats_real_items_with_actual_count(monkeypatch):
    import sender

    monkeypatch.setattr(sender, "USERNAME", "Ada & Eric")

    news_items = [
        make_news_item(1, title="Pokemon & PC <Update>"),
        make_news_item(2),
    ]

    text_body, html_body = sender.build_news_email(news_items)

    assert "Hi Ada & Eric," in text_body
    assert "Hi Ada &amp; Eric," in html_body
    assert "Gaming News Digest" in text_body
    assert "Gaming News Digest" in html_body
    assert "PVN</div>" not in html_body
    assert "Daily gaming news digest" not in html_body
    assert "Sent by PVN." not in html_body
    assert "Here are today's 2 news." in text_body
    assert "Here are today's 2 news." in html_body
    assert text_body.count("URL:") == 2
    assert html_body.count("Read article") == 2
    assert "Pokemon & PC <Update>" in text_body
    assert "Pokemon &amp; PC &lt;Update&gt;" in html_body
    assert "https://example.com/news/1?a=1&amp;b=2" in html_body
    assert "Item 1" not in html_body
    assert "background:#111827" in html_body
    assert "background:#e60012" in html_body


def test_build_news_email_uses_singular_message_for_one_item():
    from sender import build_news_email

    text_body, html_body = build_news_email([make_news_item(3)])

    assert "Here is today's 1 news." in text_body
    assert "Here is today's 1 news." in html_body
    assert "background:#eab308; color:#111827" in html_body
    assert "not console-specific" in text_body
    assert "not console-specific" in html_body


def test_console_badge_colors_match_console_brands():
    from models import ValidatedNewsItem
    from sender import news_item_to_html

    item = ValidatedNewsItem(
        title="Multi-console item",
        summary="Summary for a multi-console item.",
        source_name="Source",
        source_url="https://example.com/news/multi-console",
        consoles=[
            "XBOX",
            "Playstations",
            "Switch and Switch 2",
            "PC",
            "SteamDeck and SteamMachine",
        ],
        tag="Industry",
        url_validity=True,
    )

    html_body = news_item_to_html(item, index=1)

    assert "background:#107c10" in html_body
    assert "background:#006fcd" in html_body
    assert "background:#e60012" in html_body
    assert "background:#111827" in html_body
    assert "background:#6b7280" in html_body


def test_send_news_email_uses_generated_formatted_email(monkeypatch):
    import sender

    captured = {}

    def fake_send_email(subject: str, body: str, html_body: str | None = None) -> None:
        captured["subject"] = subject
        captured["body"] = body
        captured["html_body"] = html_body

    monkeypatch.setattr(sender, "send_email", fake_send_email)

    sender.send_news_email(
        [make_news_item(1), make_news_item(2)],
        subject="PVN custom subject",
    )

    assert captured["subject"] == "PVN custom subject"
    assert "Here are today's 2 news." in captured["body"]
    assert "Gaming News Digest" in captured["html_body"]


def test_send_news_email_sends_empty_digest(monkeypatch):
    import sender

    captured = {}

    def fake_send_email(subject: str, body: str, html_body: str | None = None) -> None:
        captured["subject"] = subject
        captured["body"] = body
        captured["html_body"] = html_body

    monkeypatch.setattr(sender, "send_email", fake_send_email)

    sender.send_news_email([], subject="PVN empty digest")

    assert captured["subject"] == "PVN empty digest"
    assert "Sorry, PVN could not find any validated news items today." in captured["body"]
    assert "Sorry, PVN could not find any validated news items today." in captured[
        "html_body"
    ]
