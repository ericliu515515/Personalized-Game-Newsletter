import os
import random
import sys
from pathlib import Path
from typing import get_args

import pytest
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))
load_dotenv(PROJECT_ROOT / ".env")


pytestmark = pytest.mark.integration

TEST_RUN_COUNT = 10
RANDOM_SEED = 20260618
MODEL_INPUT_USD_PER_1M_TOKENS = 0.20
MODEL_OUTPUT_USD_PER_1M_TOKENS = 1.25
WEB_SEARCH_USD_PER_CALL = 0.01
USD_TO_NTD = 31.6
TAGS = [
    "Pokemon",
    "The Legend of Zelda",
    "Mario",
    "Final Fantasy",
    "Monster Hunter",
]


def require_openai_env() -> None:
    missing = [
        name
        for name in ("OPENAI_API_KEY", "SEARCH_MODEL")
        if not os.getenv(name)
    ]

    if missing:
        pytest.skip(f"Missing OpenAI test environment variables: {', '.join(missing)}")


def estimate_ntd_cost(input_tokens: int, output_tokens: int) -> float:
    input_cost_usd = input_tokens / 1_000_000 * MODEL_INPUT_USD_PER_1M_TOKENS
    output_cost_usd = output_tokens / 1_000_000 * MODEL_OUTPUT_USD_PER_1M_TOKENS
    total_cost_usd = input_cost_usd + output_cost_usd + WEB_SEARCH_USD_PER_CALL

    return total_cost_usd * USD_TO_NTD


def test_get_news_items_returns_only_requested_consoles_and_tags() -> None:
    require_openai_env()

    from models import NOT_CONSOLE_SPECIFIC, ConsoleCategory
    from response import get_news_items

    all_consoles = list(get_args(ConsoleCategory))
    random_generator = random.Random(RANDOM_SEED)
    requested_console_groups: list[list[ConsoleCategory]] = []
    seen_console_groups: set[tuple[ConsoleCategory, ...]] = set()

    while len(requested_console_groups) < TEST_RUN_COUNT:
        console_count = random_generator.randint(1, len(all_consoles))
        requested_consoles = sorted(
            random_generator.sample(all_consoles, console_count)
        )
        requested_console_group = tuple(requested_consoles)

        if requested_console_group in seen_console_groups:
            continue

        seen_console_groups.add(requested_console_group)
        requested_console_groups.append(requested_consoles)

    total_input_tokens = 0
    total_output_tokens = 0
    total_tokens = 0
    total_estimated_ntd_cost = 0.0

    for test_index, requested_consoles in enumerate(requested_console_groups, start=1):
        news_items, token_usage = get_news_items(
            consoles=requested_consoles,
            tags=TAGS,
            news_count=5,
            temperature=1,
        )

        total_input_tokens += token_usage.input_tokens
        total_output_tokens += token_usage.output_tokens
        total_tokens += token_usage.total_tokens
        estimated_ntd_cost = estimate_ntd_cost(
            input_tokens=token_usage.input_tokens,
            output_tokens=token_usage.output_tokens,
        )
        total_estimated_ntd_cost += estimated_ntd_cost

        assert len(news_items) == 5
        assert token_usage.input_tokens > 0
        assert token_usage.output_tokens > 0
        assert token_usage.total_tokens > 0

        for item in news_items:
            assert item.consoles
            assert len(set(item.consoles)) == len(item.consoles)

            if item.consoles == [NOT_CONSOLE_SPECIFIC]:
                pass
            else:
                assert NOT_CONSOLE_SPECIFIC not in item.consoles
                assert set(item.consoles).issubset(set(requested_consoles))

            assert item.tag in TAGS

        print(
            f"Test {test_index} estimated NTD cost: {estimated_ntd_cost:.4f} "
            f"(input={token_usage.input_tokens}, "
            f"output={token_usage.output_tokens}, "
            f"total={token_usage.total_tokens})"
        )

    print(f"Total input tokens across {TEST_RUN_COUNT} OpenAI calls: {total_input_tokens}")
    print(f"Total output tokens across {TEST_RUN_COUNT} OpenAI calls: {total_output_tokens}")
    print(f"Total tokens across {TEST_RUN_COUNT} OpenAI calls: {total_tokens}")
    print(
        f"Total estimated NTD cost across {TEST_RUN_COUNT} OpenAI calls: "
        f"{total_estimated_ntd_cost:.4f}"
    )
    assert total_input_tokens > 0
    assert total_output_tokens > 0
    assert total_tokens > 0
    assert total_estimated_ntd_cost > 0
