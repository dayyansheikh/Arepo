# ruff: noqa: E501
"""Sportsbook lines as published on ESPN's public scoreboards (CH29: closing-line value vs Polymarket's pre-game
price). Category-agnostic capture: sports scope is undecided, so this records data only and binds no design.

Keyless ``GET https://site.api.espn.com/apis/site/v2/sports/<sport>/<league>/scoreboard`` per league (the
current board: today's games, the current NFL / college-football week). Each game carries the provider's
(currently DraftKings) moneyline, spread and total with ``open`` and ``close`` (= current until the game starts)
prices. Line MOVEMENT through time is not retrievable later; that is what this stream keeps.

Keys ``g:<league>:<event id>`` = ``{date, name, state, completed, period, clock, detail, competitors, odds}``;
``competitors`` = ``[{id, home_away, abbr, score}]``; ``odds`` = per provider ``{provider, details,
over_under, spread, moneyline, point_spread, total, home_fav, away_fav, home_fav_open, away_fav_open}`` where
``moneyline`` / ``point_spread`` / ``total`` are ``{side: {open|close|current: {line, odds}}}`` (American odds
strings, raw). Links, logos and tracking blobs are dropped.
"""

from __future__ import annotations

from typing import Any

from .common import FetchError, Http, PollResult, StreamSpec

BASE = "https://site.api.espn.com/apis/site/v2/sports"
LEAGUES: dict[str, dict] = {
    "football/nfl": {},
    "football/college-football": {"groups": "80", "limit": "300"},
    "basketball/nba": {},
    "basketball/wnba": {},
    "basketball/mens-college-basketball": {"groups": "50", "limit": "400"},
    "baseball/mlb": {},
    "hockey/nhl": {},
    "soccer/eng.1": {},
    "soccer/uefa.champions": {},
    "soccer/esp.1": {},
    "soccer/usa.1": {},
    "mma/ufc": {},
}
PHASES = ("open", "close", "current")


def _price(x: Any) -> dict | None:
    if not isinstance(x, dict):
        return None
    out = {k: x.get(k) for k in ("line", "odds") if x.get(k) is not None}
    return out or None


def _market(block: Any) -> dict | None:
    if not isinstance(block, dict):
        return None
    out = {}
    for side, v in block.items():
        if not isinstance(v, dict):
            continue
        ph = {p: _price(v.get(p)) for p in PHASES if _price(v.get(p))}
        if ph:
            out[side] = ph
    return out or None


def compact_odds(odds: Any) -> list[dict]:
    out = []
    for o in odds if isinstance(odds, list) else []:
        if not isinstance(o, dict):
            continue
        prov = o.get("provider") or {}
        h, a = o.get("homeTeamOdds") or {}, o.get("awayTeamOdds") or {}
        rec = {"provider": prov.get("name"), "provider_id": prov.get("id"), "details": o.get("details"),
               "over_under": o.get("overUnder"), "spread": o.get("spread"),
               "moneyline": _market(o.get("moneyline")), "point_spread": _market(o.get("pointSpread")),
               "total": _market(o.get("total")),
               "home_fav": h.get("favorite"), "away_fav": a.get("favorite"),
               "home_fav_open": h.get("favoriteAtOpen"), "away_fav_open": a.get("favoriteAtOpen"),
               "home_ml": h.get("moneyLine"), "away_ml": a.get("moneyLine")}
        out.append({k: v for k, v in rec.items() if v is not None})
    return out


def parse_board(league: str, payload: Any) -> dict[str, Any]:
    items: dict[str, Any] = {}
    for e in (payload or {}).get("events") or []:
        if not isinstance(e, dict) or e.get("id") is None:
            continue
        comp = (e.get("competitions") or [{}])[0] or {}
        st = comp.get("status") or e.get("status") or {}
        typ = st.get("type") or {}
        competitors = []
        for c in comp.get("competitors") or []:
            team = c.get("team") or c.get("athlete") or {}
            competitors.append({"id": c.get("id"), "home_away": c.get("homeAway"),
                                "abbr": team.get("abbreviation") or team.get("shortName"),
                                "score": c.get("score")})
        items[f"g:{league}:{e['id']}"] = {
            "date": comp.get("date") or e.get("date"), "name": e.get("name"), "state": typ.get("state"),
            "completed": typ.get("completed"), "period": st.get("period"), "clock": st.get("displayClock"),
            "detail": typ.get("shortDetail"), "competitors": competitors, "odds": compact_odds(comp.get("odds")),
        }
    return items


def poll(http: Http, extra: dict, *, leagues: dict[str, dict] | None = None, **_: Any) -> PollResult:
    items: dict[str, Any] = {}
    failed = []
    per = {}
    for lg, params in (leagues or LEAGUES).items():
        try:
            got = parse_board(lg, http.get_json(f"{BASE}/{lg}/scoreboard", params or None, tag=lg))
        except (FetchError, AttributeError, TypeError, KeyError, IndexError) as e:  # one league failing
            # must not drop the others; recorded in meta
            failed.append({"league": lg, "error": str(e)[:200]})
            continue
        per[lg] = len(got)
        items.update(got)
    if failed and not items:
        raise FetchError(f"espn: all leagues failed ({failed[0]['error']})")
    # boards roll by date, so a game leaving the board is not an event: no gone scopes
    return PollResult(items=items, scopes=(), meta={"per_league": per, "failed": failed,
                                                   "n_with_odds": sum(bool(v["odds"]) for v in items.values())})


SPEC = StreamSpec(name="espn_odds", dirname="stream_espn_odds", slot_s=600, checkpoint_s=6 * 3600,
                  allowance_bytes=5_000_000, stream_cap_gb=2.0, rps=1.0, budget_s=240, poll=poll)
