from dotenv import load_dotenv

load_dotenv()

from models import ValidatedNewsItem
from query_history import append_query_history
from sender import send_news_email
from load_settings import CONSOLES, TAGS
from validation import get_valid_news_items

TARGET_VALID_NEWS_COUNT = 3
MAX_NEWS_SEARCH_ATTEMPTS = 10
SEARCH_TEMPERATURE = 1


def news_item_to_markdown(item: ValidatedNewsItem, index: int) -> str:
    console_text = ", ".join(item.consoles)

    return f"""## {index}. [{item.title}]({item.source_url})

**Source:** {item.source_name}

**Consoles:** {console_text}

**Tag:** {item.tag}

{item.summary}
"""


def main() -> None:
    try:
        validated_news_items, token_usage, validation_message = get_valid_news_items(
            consoles=CONSOLES,
            tags=TAGS,
            target_count=TARGET_VALID_NEWS_COUNT,
            max_attempts=MAX_NEWS_SEARCH_ATTEMPTS,
            temperature=SEARCH_TEMPERATURE,
        )
    except Exception as exc:
        append_query_history(
            tags=TAGS,
            consoles=CONSOLES,
            target_count=TARGET_VALID_NEWS_COUNT,
            max_attempts=MAX_NEWS_SEARCH_ATTEMPTS,
            temperature=SEARCH_TEMPERATURE,
            validated_news_items=[],
            token_usage=None,
            message=f"0/{TARGET_VALID_NEWS_COUNT}",
            error=f"{type(exc).__name__}: {exc}",
        )
        raise

    append_query_history(
        tags=TAGS,
        consoles=CONSOLES,
        target_count=TARGET_VALID_NEWS_COUNT,
        max_attempts=MAX_NEWS_SEARCH_ATTEMPTS,
        temperature=SEARCH_TEMPERATURE,
        validated_news_items=validated_news_items,
        token_usage=token_usage,
        message=validation_message,
    )

    print("# News Results")
    print(f"Tags: {', '.join(TAGS)}")
    print(f"Validated items: {validation_message}")

    for index, item in enumerate(validated_news_items, start=1):
        print("")
        print(news_item_to_markdown(item, index))

    print("")
    print("## Token Usage")
    print(f"Input tokens: {token_usage.input_tokens}")
    print(f"Output tokens: {token_usage.output_tokens}")
    print(f"Total tokens: {token_usage.total_tokens}")

    print("")
    print("Sending email...")
    send_news_email(validated_news_items)
    print("Email sent.")


if __name__ == "__main__":
    main()
