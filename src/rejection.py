import os
from typing import get_args

from dotenv import load_dotenv
from langsmith import traceable
from openai import OpenAI
from pydantic import BaseModel

from models import ConsoleCategory, NewsItem
from response import TokenUsage

load_dotenv()

REJECTION_MODEL = os.getenv("REJECTION_MODEL", os.getenv("SEARCH_MODEL"))

if not REJECTION_MODEL:
    raise RuntimeError(
        "REJECTION_MODEL or SEARCH_MODEL was not found. Add one to .env first."
    )

client = OpenAI()


class RejectionDecision(BaseModel):
    accepted: bool
    reason: str


@traceable(name="PVN rejection judge")
def reject_news_item(
    item: NewsItem,
    requested_tags: list[str],
) -> tuple[RejectionDecision, TokenUsage]:
    """
    Use an LLM judge to reject semantically wrong news matches.

    The search response schema already checks field shape. This judge checks
    whether the article is truly about the chosen broad tag and whether the
    assigned console labels conflict with explicit platform evidence.
    """
    known_console_text = ", ".join(get_args(ConsoleCategory))
    requested_tag_text = ", ".join(
        dict.fromkeys(tag.strip() for tag in requested_tags if tag.strip())
    )

    response = client.responses.parse(
        model=REJECTION_MODEL,
        temperature=0,
        input=f"""
You are judging one candidate videogame news item for a personal news digest.

Known console categories:
{known_console_text}

Requested tags:
{requested_tag_text}

Candidate item:
Title: {item.title}
Source: {item.source_name}
URL: {item.source_url}
Assigned consoles: {", ".join(item.consoles)}
Assigned tag: {item.tag}
Summary: {item.summary}

Tag interpretation:
- Requested tags are broad topic or franchise labels, not exact-title labels.
- A sequel, DLC, expansion, remake, subtitle, update, or spin-off can count as
  being about the assigned tag if it clearly belongs to that tag's franchise or topic.
- Example: "Dragon's Dogma II: Dark Arisen" is about the assigned tag "Dragon's Dogma".

Console interpretation:
- "not console-specific" is valid when the visible item is about general game news,
  franchise news, updates, DLC, business, events, or features, and the provided
  fields do not clearly say the news is specific to one known console category.


Reject the item if any of these are true:
- The article is not truly about the assigned tag.
- The assigned consoles conflict with explicit console/platform evidence in the title, URL, source name, or summary.
- The item says "not console-specific", but the visible fields clearly show that the article is specific to one of the known console categories.
- The article is explicitly specific to a console/platform that is not represented correctly by the assigned consoles.

Accept the item only if:
- The article is clearly about the assigned tag.
- The assigned consoles match explicit console/platform evidence, or the provided fields do not show a clear console/platform signal and the item is labeled "not console-specific".

Example rejection:
Title: The Duskbloods, A Nintendo Switch 2 Exclusive RPG From Elden Ring Developer From Software...
Assigned consoles: not console-specific
Assigned tag: Elden Ring
Reason: The article is about a Nintendo Switch 2 exclusive, so it is console-specific and cannot be labeled "not console-specific".

Return accepted=false for rejected items and accepted=true for valid items.
Keep reason short and specific.
""",
        text_format=RejectionDecision,
    )

    usage = response.usage
    token_usage = TokenUsage(
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
    )

    return response.output_parsed, token_usage
