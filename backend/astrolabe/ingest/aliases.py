"""Company/ticker alias layer for market search.

When a reader searches "MSFT" the market may be titled "Microsoft" (and vice versa), so the
search expands a query to its known aliases and searches each. The list is small, curated and
conservative: it only maps well-known company names to their tickers. Unknown terms are
searched as-is. This never fabricates a market; it only broadens what the real search matches.
"""
from __future__ import annotations

# Each group is a set of interchangeable aliases (company names + tickers + common variants).
_ALIAS_GROUPS: list[set[str]] = [
    {"microsoft", "msft"},
    {"apple", "aapl"},
    {"google", "alphabet", "goog", "googl"},
    {"amazon", "amzn"},
    {"tesla", "tsla"},
    {"nvidia", "nvda"},
    {"meta", "facebook", "fb", "meta platforms"},
    {"netflix", "nflx"},
    {"openai"},
    {"coinbase", "coin"},
    {"palantir", "pltr"},
    {"amd", "advanced micro devices"},
    {"intel", "intc"},
    {"boeing", "ba"},
    {"disney", "dis"},
    {"walmart", "wmt"},
    {"jpmorgan", "jpm", "jp morgan"},
    {"bitcoin", "btc"},
    {"ethereum", "eth"},
    {"solana", "sol"},
]

# Flattened lookup: alias -> the full set it belongs to.
_LOOKUP: dict[str, set[str]] = {}
for _group in _ALIAS_GROUPS:
    for _a in _group:
        _LOOKUP.setdefault(_a, set()).update(_group)


def expand_query(query: str) -> list[str]:
    """Return the query plus any known aliases (the original first, de-duplicated).

    Matching is case-insensitive and on the whole trimmed query (e.g. "MSFT" or "Microsoft").
    """
    q = (query or "").strip()
    if not q:
        return []
    out = [q]
    aliases = _LOOKUP.get(q.lower())
    if aliases:
        for a in sorted(aliases):
            if a.lower() != q.lower():
                out.append(a)
    return out
