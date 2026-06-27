import os

from langsmith import traceable

# Currently they are in the same folder
from url_check import url_is_live
from models import (
    NOT_CONSOLE_SPECIFIC,
    ConsoleCategory,
    NewsItem,
    ValidatedNewsItem,
)
from query_history import load_query_history_items
from rejection import reject_news_item
from response import TokenUsage, get_news_items

if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("OPENAI_API_KEY was not found. Add it to .env first.")


@traceable(name="PVN duplicate URL rejection")
def reject_duplicate_url(source_url: str) -> bool:
    return True


@traceable(name="PVN validation loop")
def get_valid_news_items(
    consoles: list[ConsoleCategory],
    tags: list[str],
    target_count: int,
    max_attempts: int,
    temperature: float,
) -> tuple[list[ValidatedNewsItem], TokenUsage, str]:
    validated_news_items: list[ValidatedNewsItem] = []
    seen_items: list[NewsItem] = load_query_history_items()
    seen_urls: set[str] = {item.source_url for item in seen_items}
    allowed_tags = {tag.strip() for tag in tags if tag.strip()}
    total_token_usage = TokenUsage(
        input_tokens=0,
        output_tokens=0,
        total_tokens=0,
    )
    attempt_count = 0

    while len(validated_news_items) < target_count and attempt_count < max_attempts:
        attempt_count += 1
        news_items, token_usage = get_news_items(
            consoles=consoles,
            tags=tags,
            news_count=target_count,
            seen_items=seen_items,
            temperature=temperature,
        )
        total_token_usage = TokenUsage(
            input_tokens=total_token_usage.input_tokens + token_usage.input_tokens,
            output_tokens=total_token_usage.output_tokens + token_usage.output_tokens,
            total_tokens=total_token_usage.total_tokens + token_usage.total_tokens,
        )

        for item in news_items:
            if len(validated_news_items) >= target_count:
                break

            if item.source_url in seen_urls:
                reject_duplicate_url(item.source_url)
                continue

            if item.tag not in allowed_tags:
                continue

            if item.consoles == consoles:
                item.consoles = [NOT_CONSOLE_SPECIFIC]

            seen_items.append(item)
            seen_urls.add(item.source_url)

            rejection_decision, rejection_token_usage = reject_news_item(
                item=item,
                requested_tags=tags,
            )
            
            total_token_usage = TokenUsage(
                input_tokens=total_token_usage.input_tokens
                + rejection_token_usage.input_tokens,
                output_tokens=total_token_usage.output_tokens
                + rejection_token_usage.output_tokens,
                total_tokens=total_token_usage.total_tokens
                + rejection_token_usage.total_tokens,
            )

            if not rejection_decision.accepted:
                continue

            if url_is_live(item.source_url):
                validated_news_items.append(
                    ValidatedNewsItem(
                        **item.model_dump(),
                        url_validity=True,
                    )
                )

    message = f"{len(validated_news_items)}/{target_count}"

    return validated_news_items, total_token_usage, message
