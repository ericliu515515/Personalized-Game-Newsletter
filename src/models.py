
from typing import Annotated, Literal

from pydantic import BaseModel, Field

ConsoleCategory = Literal[
    "SteamDeck and SteamMachine",
    "PC",
    "Switch and Switch 2",
    "Playstations",
    "XBOX",
]

NOT_CONSOLE_SPECIFIC = "not console-specific"
SpecificConsoleList = Annotated[list[ConsoleCategory], Field(min_length=1)]
NotConsoleSpecificList = Annotated[
    list[Literal["not console-specific"]],
    Field(min_length=1, max_length=1),
]

NewsConsoles = SpecificConsoleList | NotConsoleSpecificList

class NewsItem(BaseModel):
    title: str
    summary: str
    source_name: str
    source_url: str
    consoles: NewsConsoles
    tag: str

class ValidatedNewsItem(NewsItem):
    url_validity: bool
