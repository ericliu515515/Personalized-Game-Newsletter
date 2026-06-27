import os
from dataclasses import dataclass
from typing import Annotated, Literal, get_args

from dotenv import load_dotenv
from langsmith import traceable
from openai import OpenAI
from pydantic import BaseModel, Field, create_model

from models import NOT_CONSOLE_SPECIFIC, ConsoleCategory, NewsItem

load_dotenv()

SEARCH_MODEL = os.getenv("SEARCH_MODEL")

if not SEARCH_MODEL:
    raise RuntimeError("SEARCH_MODEL was not found. Add it to .env first.")

client = OpenAI()


@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int


def build_news_result_model(
    consoles: list[ConsoleCategory],
    tags: list[str],
    news_count: int,
) -> type[BaseModel]:
    allowed_consoles = tuple(dict.fromkeys(consoles))
    allowed_tags = tuple(dict.fromkeys(tag.strip() for tag in tags if tag.strip()))

    if not allowed_consoles:
        raise ValueError("consoles must contain at least one console category.")

    if not allowed_tags:
        raise ValueError("tags must contain at least one non-empty tag.")

    valid_consoles = set(get_args(ConsoleCategory))
    invalid_consoles = [
        console
        for console in allowed_consoles
        if console not in valid_consoles
    ]

    if invalid_consoles:
        raise ValueError(f"Invalid console categories: {invalid_consoles}")

    DynamicConsoleCategory = Literal.__getitem__(allowed_consoles)
    DynamicConsoleList = Annotated[
        list[DynamicConsoleCategory],
        Field(min_length=1),
    ]
    DynamicNotConsoleSpecificList = Annotated[
        list[Literal[NOT_CONSOLE_SPECIFIC]],
        Field(min_length=1, max_length=1),
    ]
    DynamicConsoles = DynamicConsoleList | DynamicNotConsoleSpecificList
    DynamicTag = Literal.__getitem__(allowed_tags)

    DynamicNewsItem = create_model(
        "DynamicNewsItem",
        title=(str, ...),
        summary=(str, ...),
        source_name=(str, ...),
        source_url=(str, ...),
        consoles=(DynamicConsoles, ...),
        tag=(DynamicTag, ...),
    )

    DynamicNewsResult = create_model(
        "DynamicNewsResult",
        items=(
            list[DynamicNewsItem],
            Field(min_length=news_count, max_length=news_count),
        ),
    )

    return DynamicNewsResult


@traceable(name="PVN search")
def get_news_items(
    consoles: list[ConsoleCategory],
    tags: list[str],
    news_count: int = 5,
    seen_items: list[NewsItem] | None = None,
    temperature: float = 1.0,
) -> tuple[list[NewsItem], TokenUsage]:
    """
    Search the web with OpenAI and return current news items.

    Args:
        consoles: Console categories that returned articles can be related to.
        tags: Videogame series tags that returned articles must be related to.
        news_count: Number of news items to return.
        seen_items: News items already returned by earlier attempts. These are
        added to the prompt so the model avoids repeating them.
        temperature: Controls randomness. Higher values make results more varied.

    Returns:
        A tuple containing the parsed NewsItem list and token usage metadata.
    """
    if news_count < 1:
        raise ValueError("news_count must be at least 1.")

    if not 0 <= temperature <= 2:
        raise ValueError("temperature must be between 0 and 2.")

    DynamicNewsResult = build_news_result_model(
        consoles=consoles,
        tags=tags,
        news_count=news_count,
    )

    seen_items = seen_items or []
    console_prompt = ", ".join(consoles)
    tag_prompt = ", ".join(dict.fromkeys(tag.strip() for tag in tags if tag.strip()))
    seen_items_prompt = "No previously seen items."

    if seen_items:
        seen_items_prompt = "\n".join(
            f"- {', '.join(item.consoles)} | {item.tag}: {item.title} | {item.source_url}"
            for item in seen_items
        )

    # The output "response" is an OpenAI SDK object.
    # type(response.output_parsed) = DynamicNewsResult
    # type(response.output_parsed.items) = list[NewsItem]
    response = client.responses.parse(
        model=SEARCH_MODEL,
        tools=[{"type": "web_search"}],
        tool_choice="required",
        temperature=temperature,
        input=f"""
The user only owns these consoles:
{console_prompt}

The user only cares about these topic tags:
{tag_prompt}

Use web search to find exactly {news_count} current news articles.

A valid article must be clearly about one of the requested tags.

For each item:
- Assign tag to the requested tag that the article is about.
- If the article is general videogame, publisher, business, event, DLC policy, or industry news that is not specific to any user console, set consoles to ["not console-specific"].
- Do not mix "not console-specific" with real console categories. Use either ["not console-specific"] or one or more real consoles.
- If platform support is unclear from the article or reliable search context, use ["not console-specific"] unless the news itself is console-specific.

Requirements:
- Return only specific news article pages.
- The article must be clearly related to the videogame series assigned in the tag field.
- The URL must point directly to the individual article, not a homepage, category page, tag page, search page, or news index.
- Prefer recent, reputable sources.
- Do not include duplicate stories from different URLs unless they add meaningfully different reporting.
- If a source URL looks like a section page, such as `/ai/news`, `/technology`, `/category/artificial-intelligence`, or a site homepage, reject it and find another result.
- Do not return any item whose title or URL matches an already seen item.

Console assignment emphasis:
For each news item about a specific game, set consoles to every user-owned console that can run that game. If the specific game can run on more than one user-owned console, include all matching user-owned consoles.

Good URL example:
https://www.tomsguide.com/ai/anthropic-abruptly-disables-fable-5-and-mythos-5-following-us-government-order

Bad URL example:
https://www.tomsguide.com/ai/news

Return exactly {news_count} items.

Only return URLs that are likely to be live and reachable.
Do not return URLs that appear to be broken, archived, placeholder, paywall redirect-only, or 404 pages.

Already seen items to avoid, including earlier attempts and prior query history:
{seen_items_prompt}
""",
        text_format=DynamicNewsResult,
    )

    usage = response.usage
    token_usage = TokenUsage(
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
    )

    news_items = [
        NewsItem(**item.model_dump())
        for item in response.output_parsed.items
    ]

    return news_items, token_usage
