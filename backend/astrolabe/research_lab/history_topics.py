"""Creation-known topic labels for the power backfill (research lab, exploratory_historical).

Gamma ``markets`` rows carry no tags, so the topic is a transparent keyword rule over text that is
fixed when the market is listed (question, event title, slug) plus the creation-time ``feeType``
category. It is a sampling stratum only: it never enters a model feature, and it is imperfect on
purpose (no tuning). Sampling weights are exact for the *label*, whatever its accuracy.
"""

from __future__ import annotations

import re

ASYMMETRIC_TOPICS = ("politics", "geopolitics", "awards", "corporate", "macro")
FEE_FIRST = {"sports": "sports", "crypto": "crypto", "weather": "weather", "mentions": "mentions",
             "politics": "politics", "economics": "macro"}

_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("awards", ("oscar", "oscars", "academy award", "grammy", "grammys", "emmy", "emmys",
                "golden globe", "bafta", "tony award", "nobel", "best picture", "best actor",
                "best actress", "best director", "ballon d'or", "person of the year",
                "album of the year", "song of the year")),
    ("macro", ("fed", "fomc", "interest rate", "rate cut", "rate hike", "inflation", "cpi", "gdp",
               "unemployment", "jobs report", "nonfarm", "recession", "powell", "ecb", "boj",
               "bank of england", "bps", "pce", "payrolls", "debt ceiling", "treasury yield")),
    ("geopolitics", ("russia", "ukraine", "israel", "gaza", "hamas", "iran", "taiwan", "nato",
                     "ceasefire", "invade", "invasion", "missile", "sanctions", "putin",
                     "zelensky", "netanyahu", "north korea", "venezuela", "hezbollah", "syria",
                     "security council", "peace deal", "treaty", "war", "military", "china")),
    ("politics", ("trump", "biden", "harris", "election", "elected", "president", "senate",
                  "congress", "republican", "democrat", "democratic", "governor", "mayor",
                  "primary", "nominee", "nomination", "parliament", "prime minister", "impeach",
                  "supreme court", "cabinet", "speaker of the house", "shutdown", "executive order",
                  "approval rating", "vote", "voters", "poll", "tariff", "tariffs", "white house")),
    ("corporate", ("ceo", "ipo", "acquire", "acquisition", "merger", "earnings", "openai",
                   "apple", "tesla", "nvidia", "microsoft", "google", "meta", "amazon", "spacex",
                   "layoffs", "bankrupt", "bankruptcy", "stock split", "market cap", "step down",
                   "resign", "gpt", "iphone", "anthropic", "announce")),
)
_COMPILED = tuple((name, re.compile(r"\b(?:" + "|".join(re.escape(k) for k in kws) + r")\b"))
                  for name, kws in _RULES)


def topic_of(question: str, event_title: str, slug: str, fee_category: str) -> str:
    """One label per market: fee-type category first (sports/crypto/weather/mentions/politics/
    economics), then the first keyword rule that matches, else ``other``."""
    if fee_category in FEE_FIRST:
        return FEE_FIRST[fee_category]
    text = f"{question} {event_title} {str(slug).replace('-', ' ')}".lower()
    for name, rx in _COMPILED:
        if rx.search(text):
            return name
    return "other"


def is_asymmetric(topic: str) -> bool:
    return topic in ASYMMETRIC_TOPICS
