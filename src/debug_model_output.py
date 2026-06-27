import os
import random
from dataclasses import dataclass

from langsmith import traceable

from models import (
    NOT_CONSOLE_SPECIFIC,
    ConsoleCategory,
    NewsItem,
    ValidatedNewsItem,
)
from rejection import reject_news_item
from response import TokenUsage, get_news_items
from url_check import url_is_live

REQUIRED_TAGS = [
    "Next Generataional Hardware",
    "Industry",
    "Other Videogame",
]

TAGS = [
    "Next Generataional Hardware",
    "Industry",
    "Other Videogame",
    "Pokemon",
    "The Legend of Zelda",
    "Mario",
    "Metroid",
    "Animal Crossing",
    "Splatoon",
    "Kirby",
    "Super Smash Bros",
    "Fire Emblem",
    "Xenoblade",
    "Pikmin",
    "Final Fantasy",
    "Dragon Quest",
    "Persona",
    "Shin Megami Tensei",
    "Tales of",
    "Atelier",
    "Ys",
    "Trails",
    "Nier",
    "Kingdom Hearts",
    "Octopath Traveler",
    "Bravely Default",
    "Star Ocean",
    "SaGa",
    "Mana",
    "Granblue Fantasy",
    "Monster Hunter",
    "Resident Evil",
    "Street Fighter",
    "Devil May Cry",
    "Mega Man",
    "Dragon's Dogma",
    "Onimusha",
    "Ace Attorney",
    "Silent Hill",
    "Metal Gear Solid",
    "Castlevania",
    "Tekken",
    "Soulcalibur",
    "Elden Ring",
    "Dark Souls",
    "Armored Core",
    "Cyberpunk 2077",
    "The Witcher",
    "Baldur's Gate",
    "Diablo",
    "World of Warcraft",
    "Overwatch",
    "Call of Duty",
    "Battlefield",
    "Halo",
    "Gears of War",
    "Forza",
    "Gran Turismo",
    "Fable",
    "Perfect Dark",
    "Doom",
    "Wolfenstein",
    "Fallout",
    "The Elder Scrolls",
    "Starfield",
    "Indiana Jones",
    "Minecraft",
    "Roblox",
    "Fortnite",
    "Apex Legends",
    "Valorant",
    "League of Legends",
    "Dota 2",
    "Counter-Strike",
    "PUBG",
    "Destiny",
    "Warframe",
    "Helldivers",
    "Grand Theft Auto",
    "Red Dead Redemption",
    "Max Payne",
    "Borderlands",
    "BioShock",
    "Civilization",
    "XCOM",
    "Age of Empires",
    "Total War",
    "Crusader Kings",
    "Football Manager",
    "EA Sports FC",
    "Madden",
    "NBA 2K",
    "MLB The Show",
    "WWE 2K",
    "Tony Hawk",
    "Rocket League",
    "Genshin Impact",
    "Honkai Star Rail",
    "Zenless Zone Zero",
    "Wuthering Waves",
    "Fate/Grand Order",
    "Uma Musume",
    "Hollow Knight",
    "Hades",
    "Dead Cells",
    "Slay the Spire",
    "Stardew Valley",
    "Terraria",
    "Palworld",
    "Dwarf Fortress",
    "Balatro",
    "Vampire Survivors",
    "No Man's Sky",
    "Among Us",
    "Lethal Company",
    "Phasmophobia",
    "God of War",
    "The Last of Us",
    "Spider-Man",
    "Ghost of Tsushima",
    "Horizon",
    "Handheld Gaming Hardware",
    "VR and AR Hardware",
    "Cloud Gaming",
    "Game Subscription Services",
    "Esports",
    "Game Preservation",
    "Accessibility",
    "Modding",
    "AI in Games",
    "Studio Layoffs",
    "Acquisitions and Mergers",
    "Financial Results",
    "Events and Showcases",
    "DLC and Expansions",
    "Remakes and Remasters",
    "Early Access",
    "Game Delays",
    "Patch Notes and Balance",
    "Backward Compatibility",
    "Physical Media",
]

CONSOLES: list[ConsoleCategory] = [
    "SteamDeck and SteamMachine",
    "PC",
    "Switch and Switch 2",
    "Playstations",
    "XBOX",
]

TARGET_VALID_NEWS_COUNT = 3
MAX_NEWS_SEARCH_ATTEMPTS = 10
SEARCH_TEMPERATURE = 1
EXPECTED_DEBUG_RUN_COUNT = 10
MIN_EXTRA_TAGS_PER_RUN = 5
MAX_EXTRA_TAGS_PER_RUN = 10
DEBUG_RANDOM_SEED = os.getenv("DEBUG_RANDOM_SEED")


@dataclass(frozen=True)
class DebugRun:
    name: str
    consoles: tuple[ConsoleCategory, ...]
    tags: tuple[str, ...]


@dataclass
class DebugValidationStats:
    search_attempts: int = 0
    candidate_loop_iterations: int = 0
    accepted_items: int = 0
    rejected_seen: int = 0
    rejected_tag: int = 0
    rejected_judge: int = 0
    rejected_url: int = 0


@dataclass
class DebugValidationResult:
    items: list[ValidatedNewsItem]
    token_usage: TokenUsage
    stats: DebugValidationStats
    error: str | None = None


@dataclass
class DebugRunSummary:
    successful_runs: int
    failed_runs: int
    token_usage: TokenUsage
    stats: DebugValidationStats


@traceable(name="PVN duplicate URL rejection", tags=["debug_model_output"])
def reject_duplicate_url(source_url: str) -> bool:
    return True


def tags_with_required(*extra_tags: str) -> tuple[str, ...]:
    requested_tags = [*REQUIRED_TAGS, *extra_tags]
    unknown_tags = [tag for tag in requested_tags if tag not in TAGS]

    if unknown_tags:
        raise ValueError(f"Unknown debug tags: {unknown_tags}")

    return tuple(dict.fromkeys(requested_tags))


def build_random_generator() -> random.Random:
    if DEBUG_RANDOM_SEED is None:
        return random.Random()

    return random.Random(DEBUG_RANDOM_SEED)


def debug_run_combination_key(
    consoles: tuple[ConsoleCategory, ...],
    tags: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return tuple(sorted(consoles)), tuple(sorted(tags))


def build_random_debug_runs(
    random_generator: random.Random,
    run_count: int,
) -> list[DebugRun]:
    extra_tag_pool = [tag for tag in TAGS if tag not in REQUIRED_TAGS]
    max_extra_tags = min(MAX_EXTRA_TAGS_PER_RUN, len(extra_tag_pool))

    if MIN_EXTRA_TAGS_PER_RUN > max_extra_tags:
        raise RuntimeError(
            "MIN_EXTRA_TAGS_PER_RUN cannot be larger than the available tag pool."
        )

    debug_runs: list[DebugRun] = []
    seen_combinations: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()
    max_generation_attempts = run_count * 100

    for _ in range(max_generation_attempts):
        if len(debug_runs) >= run_count:
            return debug_runs

        console_count = random_generator.randint(1, len(CONSOLES))
        extra_tag_count = random_generator.randint(
            MIN_EXTRA_TAGS_PER_RUN,
            max_extra_tags,
        )
        consoles = tuple(random_generator.sample(CONSOLES, console_count))
        extra_tags = tuple(random_generator.sample(extra_tag_pool, extra_tag_count))
        tags = tags_with_required(*extra_tags)
        combination = debug_run_combination_key(consoles=consoles, tags=tags)

        if combination in seen_combinations:
            continue

        seen_combinations.add(combination)
        debug_runs.append(
            DebugRun(
                name=f"Random combination {len(debug_runs) + 1}",
                consoles=consoles,
                tags=tags,
            )
        )

    raise RuntimeError(
        f"Only generated {len(debug_runs)} unique debug runs after "
        f"{max_generation_attempts} attempts."
    )


def validate_debug_runs(debug_runs: list[DebugRun]) -> None:
    if len(debug_runs) != EXPECTED_DEBUG_RUN_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_DEBUG_RUN_COUNT} debug runs, found {len(debug_runs)}."
        )

    seen_combinations: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()

    for debug_run in debug_runs:
        missing_required_tags = [
            tag
            for tag in REQUIRED_TAGS
            if tag not in debug_run.tags
        ]

        if missing_required_tags:
            raise RuntimeError(
                f"{debug_run.name} is missing required tags: {missing_required_tags}"
            )

        combination = debug_run_combination_key(
            consoles=debug_run.consoles,
            tags=debug_run.tags,
        )

        if combination in seen_combinations:
            raise RuntimeError(f"Duplicate debug run combination: {debug_run.name}")

        seen_combinations.add(combination)


def add_token_usage(left: TokenUsage, right: TokenUsage) -> TokenUsage:
    return TokenUsage(
        input_tokens=left.input_tokens + right.input_tokens,
        output_tokens=left.output_tokens + right.output_tokens,
        total_tokens=left.total_tokens + right.total_tokens,
    )


def add_debug_stats(
    left: DebugValidationStats,
    right: DebugValidationStats,
) -> DebugValidationStats:
    return DebugValidationStats(
        search_attempts=left.search_attempts + right.search_attempts,
        candidate_loop_iterations=left.candidate_loop_iterations
        + right.candidate_loop_iterations,
        accepted_items=left.accepted_items + right.accepted_items,
        rejected_seen=left.rejected_seen + right.rejected_seen,
        rejected_tag=left.rejected_tag + right.rejected_tag,
        rejected_judge=left.rejected_judge + right.rejected_judge,
        rejected_url=left.rejected_url + right.rejected_url,
    )


def empty_token_usage() -> TokenUsage:
    return TokenUsage(
        input_tokens=0,
        output_tokens=0,
        total_tokens=0,
    )


@traceable(name="PVN debug validation loop", tags=["debug_model_output"])
def get_debug_valid_news_items(
    consoles: list[ConsoleCategory],
    tags: list[str],
    target_count: int,
    max_attempts: int,
    temperature: float,
) -> DebugValidationResult:
    validated_news_items: list[ValidatedNewsItem] = []
    seen_items: list[NewsItem] = []
    seen_urls: set[str] = set()
    allowed_tags = {tag.strip() for tag in tags if tag.strip()}
    total_token_usage = empty_token_usage()
    stats = DebugValidationStats()

    while (
        len(validated_news_items) < target_count
        and stats.search_attempts < max_attempts
    ):
        stats.search_attempts += 1

        try:
            news_items, token_usage = get_news_items(
                consoles=consoles,
                tags=tags,
                news_count=target_count,
                seen_items=seen_items,
                temperature=temperature,
            )
        except Exception as exc:
            return DebugValidationResult(
                items=validated_news_items,
                token_usage=total_token_usage,
                stats=stats,
                error=f"{type(exc).__name__}: {exc}",
            )

        total_token_usage = add_token_usage(total_token_usage, token_usage)

        for item in news_items:
            if len(validated_news_items) >= target_count:
                break

            stats.candidate_loop_iterations += 1

            if item.source_url in seen_urls:
                stats.rejected_seen += 1
                reject_duplicate_url(item.source_url)
                continue

            if item.tag not in allowed_tags:
                stats.rejected_tag += 1
                continue

            if item.consoles == consoles:
                item.consoles = [NOT_CONSOLE_SPECIFIC]

            seen_items.append(item)
            seen_urls.add(item.source_url)

            try:
                rejection_decision, rejection_token_usage = reject_news_item(
                    item=item,
                    requested_tags=tags,
                )
            except Exception as exc:
                return DebugValidationResult(
                    items=validated_news_items,
                    token_usage=total_token_usage,
                    stats=stats,
                    error=f"{type(exc).__name__}: {exc}",
                )

            total_token_usage = add_token_usage(
                total_token_usage,
                rejection_token_usage,
            )

            if not rejection_decision.accepted:
                stats.rejected_judge += 1
                continue

            try:
                source_url_is_live = url_is_live(item.source_url)
            except Exception as exc:
                return DebugValidationResult(
                    items=validated_news_items,
                    token_usage=total_token_usage,
                    stats=stats,
                    error=f"{type(exc).__name__}: {exc}",
                )

            if source_url_is_live:
                stats.accepted_items += 1
                validated_news_items.append(
                    ValidatedNewsItem(
                        **item.model_dump(),
                        url_validity=True,
                    )
                )
                continue

            stats.rejected_url += 1

    error = None

    if len(validated_news_items) < target_count:
        error = (
            f"Only found {len(validated_news_items)} valid news items "
            f"after {stats.search_attempts} search attempts."
        )

    return DebugValidationResult(
        items=validated_news_items,
        token_usage=total_token_usage,
        stats=stats,
        error=error,
    )


def print_debug_stats(stats: DebugValidationStats) -> None:
    print("\nLoop statistics")
    print(f"Search attempts: {stats.search_attempts}")
    print(f"Candidate loop iterations: {stats.candidate_loop_iterations}")
    print(f"Accepted valid items: {stats.accepted_items}")
    print(f"Rejected because already seen: {stats.rejected_seen}")
    print(f"Rejected by judge: {stats.rejected_judge}")
    print(f"Rejected because URL was not live: {stats.rejected_url}")
    print(f"Rejected because tag was not allowed: {stats.rejected_tag}")


def print_news_items(news_items: list[ValidatedNewsItem]) -> None:
    for index, item in enumerate(news_items, start=1):
        print(f"\n{index}. {item.title}")
        print(f"Source: {item.source_name}")
        print(f"Consoles: {', '.join(item.consoles)}")
        print(f"Tag: {item.tag}")
        print(f"URL: {item.source_url}")
        print(f"Summary: {item.summary}")


@traceable(name="PVN debug run", tags=["debug_model_output"])
def run_debug_case(index: int, debug_run: DebugRun) -> DebugValidationResult:
    print("\n" + "=" * 80)
    print(f"Debug run {index}/{EXPECTED_DEBUG_RUN_COUNT}: {debug_run.name}")
    print(f"Consoles: {', '.join(debug_run.consoles)}")
    print(f"Tags: {', '.join(debug_run.tags)}")

    result = get_debug_valid_news_items(
        consoles=list(debug_run.consoles),
        tags=list(debug_run.tags),
        target_count=TARGET_VALID_NEWS_COUNT,
        max_attempts=MAX_NEWS_SEARCH_ATTEMPTS,
        temperature=SEARCH_TEMPERATURE,
    )

    print_news_items(result.items)
    print_debug_stats(result.stats)

    print(
        "\nToken usage: "
        f"input={result.token_usage.input_tokens}, "
        f"output={result.token_usage.output_tokens}, "
        f"total={result.token_usage.total_tokens}"
    )

    if result.error is not None:
        print(f"\nRun failed: {result.error}")

    return result


@traceable(name="PVN debug run loop", tags=["debug_model_output"])
def run_debug_runs(debug_runs: list[DebugRun]) -> DebugRunSummary:
    successful_runs = 0
    failed_runs = 0
    total_token_usage = empty_token_usage()
    total_stats = DebugValidationStats()

    for index, debug_run in enumerate(debug_runs, start=1):
        result = run_debug_case(index=index, debug_run=debug_run)
        total_token_usage = add_token_usage(total_token_usage, result.token_usage)
        total_stats = add_debug_stats(total_stats, result.stats)

        if result.error is not None:
            failed_runs += 1
            continue

        successful_runs += 1

    return DebugRunSummary(
        successful_runs=successful_runs,
        failed_runs=failed_runs,
        token_usage=total_token_usage,
        stats=total_stats,
    )


def main() -> None:
    random_generator = build_random_generator()
    debug_runs = build_random_debug_runs(
        random_generator=random_generator,
        run_count=EXPECTED_DEBUG_RUN_COUNT,
    )
    validate_debug_runs(debug_runs)

    if DEBUG_RANDOM_SEED is not None:
        print(f"DEBUG_RANDOM_SEED: {DEBUG_RANDOM_SEED}")

    summary = run_debug_runs(debug_runs)

    print("\n" + "=" * 80)
    print("Debug run summary")
    print(f"Successful runs: {summary.successful_runs}")
    print(f"Failed runs: {summary.failed_runs}")
    print_debug_stats(summary.stats)
    print(f"Total input tokens: {summary.token_usage.input_tokens}")
    print(f"Total output tokens: {summary.token_usage.output_tokens}")
    print(f"Total tokens: {summary.token_usage.total_tokens}")


if __name__ == "__main__":
    main()
