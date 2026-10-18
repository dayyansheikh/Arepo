# ruff: noqa: E501
"""CB13-T class labeller (docs/research_lab/CREATIVE_BATCH_13.md CB13-T "Labeller", CB13-S "Labeller audit", section 10 ruling 3). Rules part ``LABELLER``.

The labeller is its OWN frozen rules part so that the one allowed revision (on a failed blind audit, before the T freeze) changes only this part's hash plus nothing else. No
outcome, mark or price is an input: the inputs are the market ``title`` and ``slug`` of a monitor print, the static ``ctx_category`` / ``ctx_fee_type`` (declared static
attributes, section 1.4) and the touch capture's sidecar ``fee_type`` / ``fee_category`` / ``series_slugs``. Classes are applied in the declared precedence
SPORTS-FEED > PATH-SETTLED > PUBLIC-STATISTIC > SCHEDULED-EVENT > UNSCHEDULED-NEWS, and UNKNOWN when there is no title and no sidecar row.

This module imports nothing from the other CB13 modules (it needs no common code), so its part hash depends on this file alone plus the common rule functions.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Iterable

SPORTS = "SPORTS-FEED"
PATH = "PATH-SETTLED"
PUBLIC = "PUBLIC-STATISTIC"
SCHEDULED = "SCHEDULED-EVENT"
NEWS = "UNSCHEDULED-NEWS"
UNKNOWN = "UNKNOWN"
CLASSES = (SPORTS, PATH, PUBLIC, SCHEDULED, NEWS, UNKNOWN)
LOW_CLASSES = (PATH, PUBLIC)
NEWS_CLASSES = (NEWS,)
AUDIT_OTHER = "other"
AUDIT_LABELS = ("LOW", "NEWS", AUDIT_OTHER)
AUDIT_N = 200
AUDIT_SPORTS_ADJACENT_MIN = 30
AUDIT_SEEDS = (13121, 13122)  # first audit, and the fresh sample of the one allowed revision
AUDIT_AGREE_ALL = 0.85
AUDIT_AGREE_EACH = 0.80
UNKNOWN_MAX_SHARE = 0.05  # > 5% of SCREEN fills UNKNOWN -> GL fails

SPORTS_FEE_PREFIX = "sports_fees"
SPORTS_CATEGORIES = ("sports",)
SPORTS_SERIES_RE = re.compile(
    r"(?i)^(?:nfl|cfb|nba|wnba|mlb|nhl|ufc|mls|atp|wta|cbb|cwbb|ncaa\w*|epl|ucl|uel|uecl|f1|nascar|pga|lpga|liv|ipl|bbl|lol|cs2?|dota\w*|valorant|rugby\w*|cricket\w*|boxing\w*|mma|tennis|golf|hockey|"
    r"basketball|baseball|football|soccer|fa-cup|copa|europa|primera|japan|saudi|brazil|mex|tur|ere|serc|efl|scottish|egypt|czechia|norway|uefa|euro|world-cup|olympics|premier-league|la-liga|"
    r"serie|bundesliga|ligue|liga|league|championship|cup)(?:[-_].*|\d.*)?$")
SPORTS_TITLE_RE = re.compile(
    r"(?i)(\bvs\.?\s|\bversus\b|\bO/U\s*\d|\bover/under\b|\bspread\s*:|\bmoneyline\b|\b(?:will|win)\b.*\b(?:Super Bowl|World Series|Stanley Cup|NBA Finals|Final Four|World Cup|"
    r"Champions League|Europa League|Premier League|La Liga|Serie A|Bundesliga|Ligue 1|Grand Slam|Wimbledon|US Open|French Open|Australian Open|Masters Tournament|"
    r"Ryder Cup|Heisman|Ballon d.Or|NFL|NBA|MLB|NHL|MLS|UFC|WNBA|NCAA|March Madness|Formula 1|Grand Prix|FIFA)\b|\bgame\s+\d\b|\bplayoffs?\b|\bwin on 20\d\d-\d\d-\d\d\b|"
    r"\bend in a draw\b|\bboth teams to score\b|\bfirst (?:goal|touchdown) scorer\b|\bpoints?\s+o/u\b|\brebounds?\s+o/u\b|\bassists?\s+o/u\b)")

# ---- PATH-SETTLED: an asset term together with a price form (or a crypto / price-feed fee type) ----------------------------------------------------------
PATH_FEE_PREFIXES = ("crypto_fees", "crypto_15_min", "finance_prices_fees")
PATH_ASSETS = (  # (regex, underlying key); the first match names the underlying for the path key
    (re.compile(r"(?i)\b(bitcoin|btc)\b"), "BTC"), (re.compile(r"(?i)\b(ethereum|ether|eth)\b"), "ETH"), (re.compile(r"(?i)\b(solana|sol)\b"), "SOL"),
    (re.compile(r"(?i)\bxrp\b"), "XRP"), (re.compile(r"(?i)\b(dogecoin|doge)\b"), "DOGE"), (re.compile(r"(?i)\b(bnb)\b"), "BNB"),
    (re.compile(r"(?i)\b(s&p ?500|spx|spy)\b"), "SPX"), (re.compile(r"(?i)\b(nasdaq(?:-100)?|ndx|qqq)\b"), "NDX"), (re.compile(r"(?i)\b(dow jones|dow|djia|dji)\b"), "DJI"),
    (re.compile(r"(?i)\bgold\b"), "GOLD"), (re.compile(r"(?i)\bsilver\b"), "SILVER"), (re.compile(r"(?i)\b(crude oil|wti|brent|oil)\b"), "OIL"),
    (re.compile(r"(?i)\bnatural gas\b"), "NATGAS"), (re.compile(r"(?i)\bcopper\b"), "COPPER"), (re.compile(r"(?i)\b(eur/usd|usd/jpy|gbp/usd|dxy|dollar index)\b"), "FX"),
    (re.compile(r"(?i)\b(tesla|tsla)\b"), "TSLA"), (re.compile(r"(?i)\b(nvidia|nvda)\b"), "NVDA"), (re.compile(r"(?i)\b(apple|aapl)\b"), "AAPL"),
    (re.compile(r"(?i)\b(microsoft|msft)\b"), "MSFT"), (re.compile(r"(?i)\b(amazon|amzn)\b"), "AMZN"), (re.compile(r"(?i)\b(google|alphabet|googl)\b"), "GOOGL"),
    (re.compile(r"(?i)\b(meta platforms|meta|fb)\b(?=.*(?:close|price|above|below|up or down))"), "META"), (re.compile(r"(?i)\b(crypto(?:currency)?)\b"), "CRYPTO"),
    (re.compile(r"(?i)\b(10-year|treasury yield)\b"), "RATES"),
)
PATH_FORM_RE = re.compile(r"(?i)(\bup or down\b|\babove\b|\bbelow\b|\breach(?:es)?\b|\bhit(?:s)?\b|\bdip(?:s)? to\b|\bprice of\b|\bclose(?:s)? (?:at|above|below)\b|\bbetween \$|\$\s?\d|\bfinish (?:above|below)\b|\bgreen\b|\bred\b)")

# ---- PUBLIC-STATISTIC: a published number from a named statistical source ----------------------------------------------------------------------------------
PUBLIC_FEE_PREFIXES = ("weather_fees",)
PUBLIC_RE = re.compile(
    r"(?i)(\bCPI\b|\binflation\b|\bunemployment\b|\bjobs report\b|\bnonfarm\b|\bpayrolls?\b|\bGDP\b|\bjobless claims\b|\bPCE\b|\bretail sales\b|\bhousing starts\b|\bPMI\b|\bISM\b|"
    r"\bconsumer sentiment\b|\bhighest temperature\b|\blowest temperature\b|\btemperature\b|\bdegrees\b|\b°\s?[FC]\b|\bprecipitation\b|\brainfall\b|\bsnowfall\b|\bearthquakes?\b|"
    r"\bmagnitude\s*\d|\bbox office\b|\bopening weekend\b|\bgross(?:es)?\b|\bRotten Tomatoes\b|\bMetacritic\b|\bIMDb\b|\bBillboard\b|\bSpotify\b|\btop \d+ (?:on|in)\b|\b#1 (?:on|in)\b|"
    r"\bhow many (?:times|tweets|posts)\b|\btweets?\b|\bposts? (?:on|per)\b|\bpolls?\b|\bapproval rating\b|\bfavorability\b|\bsubscribers?\b|\bviews?\b|\bfollowers\b)")

# ---- SCHEDULED-EVENT: an event with a public date ---------------------------------------------------------------------------------------------------------
SCHEDULED_FEE_PREFIXES = ("mentions_fees",)
SCHEDULED_RE = re.compile(
    r"(?i)(\belections?\b|\bprimar(?:y|ies)\b|\bnominee\b|\bnomination\b|\bdebates?\b|\bOscars?\b|\bAcademy Awards?\b|\bGrammys?\b|\bEmmys?\b|\bGolden Globes?\b|\bTonys?\b|\bFed\b|\bFOMC\b|"
    r"\brate (?:cut|hike|decision)\b|\binterest rates?\b|\bearnings\b|\bruling\b|\bSupreme Court\b|\bspeech\b|\bwhat will .{1,60}? say\b|\bsay during\b|\bmention(?:s|ed)?\b|\blaunch(?:es)?\b|"
    r"\bvotes?\b|\breferendum\b|\b(?:win|wins|wins the)\b.{0,60}\b(?:race|seat|governorship|mayor(?:al)?|senate|house|gubernatorial|presidential)\b|\bballot\b|\bcongress\b|\bconfirmed?\b)")

# ---- audit stratum: non-game sports titles (frozen keyword list) -----------------------------------------------------------------------------------------
SPORTS_ADJACENT_RE = re.compile(
    r"(?i)(\btransfers?\b|\bsign(?:s|ed|ing)?\b|\btrade[sd]?\b|\bhead coach\b|\bcoach\b|\bmanager\b|\bfired\b|\bdraft pick\b|\b#?1 pick\b|\bMVP\b|\bHeisman\b|\bBallon d.Or\b|\bCy Young\b|"
    r"\bRookie of the Year\b|\bAll-Star\b|\bretire[sd]?\b|\bcontract\b|\bextension\b|\bHall of Fame\b|\bdraft\b|\bawards?\b)")


def _norm(x) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return ""
    return str(x).strip()


def first_series_slug(series_slugs) -> str:
    """The first entry of a sidecar ``series_slugs`` value (a JSON list string like ``["nfl-2026"]``), '' if none."""
    s = _norm(series_slugs)
    if not s:
        return ""
    m = re.search(r'"([^"]+)"', s)
    return m.group(1) if m else (s if not s.startswith("[") else "")


def underlying_of(title: str) -> str | None:
    t = _norm(title)
    for rx, key in PATH_ASSETS:
        if rx.search(t):
            return key
    return None


def classify(title, slug="", fee_type="", fee_category="", series_slugs="", ctx_category="", has_sidecar: bool = False) -> tuple[str, str | None]:
    """(class, underlying). ``underlying`` is non-None only for PATH-SETTLED. The precedence is the order of the checks below; every check reads only the arguments."""
    ttl, slg = _norm(title), _norm(slug)
    ft, fc, cc = _norm(fee_type), _norm(fee_category), _norm(ctx_category).lower()
    if not ttl and not slg and not has_sidecar and not ft and not fc:
        return UNKNOWN, None
    fs = first_series_slug(series_slugs)
    if ft.startswith(SPORTS_FEE_PREFIX) or fc.lower() in SPORTS_CATEGORIES or cc in SPORTS_CATEGORIES or (fs and SPORTS_SERIES_RE.match(fs)) or SPORTS_TITLE_RE.search(ttl):
        return SPORTS, None
    asset = underlying_of(ttl)
    if ft.startswith(PATH_FEE_PREFIXES) or fc.lower() == "crypto" or cc == "crypto" or (asset is not None and PATH_FORM_RE.search(ttl)):
        return PATH, asset or ("CRYPTO" if (ft.startswith("crypto") or fc.lower() == "crypto" or cc == "crypto") else None)
    if ft.startswith(PUBLIC_FEE_PREFIXES) or PUBLIC_RE.search(ttl):
        return PUBLIC, None
    if ft.startswith(SCHEDULED_FEE_PREFIXES) or SCHEDULED_RE.search(ttl):
        return SCHEDULED, None
    return NEWS, None


def audit_group(label: str) -> str:
    """The audit's three-way grouping of a class: LOW (PATH, PUBLIC), NEWS, other."""
    return "LOW" if label in LOW_CLASSES else ("NEWS" if label in NEWS_CLASSES else AUDIT_OTHER)


def sports_adjacent(title) -> bool:
    return bool(SPORTS_ADJACENT_RE.search(_norm(title)))


def _rank(seed: int, key: str) -> str:
    return hashlib.sha256(f"{seed}|{key}".encode()).hexdigest()


def audit_sample(markets: Iterable[dict], seed: int, *, n: int = AUDIT_N, min_adjacent: int = AUDIT_SPORTS_ADJACENT_MIN) -> list[dict]:
    """Seeded stratified sample of ``n`` markets (each ``{"condition_id", "title", "slug", "label"}``): at least ``min_adjacent`` sports-adjacent titles (frozen keyword list;
    first), the rest split equally over the labeller's LOW / NEWS / other groups. Deterministic: markets are ranked by sha256(seed|condition_id). The returned rows carry the
    labeller's ``label``; the file given to the reviewer must be built with ``reviewer_view`` (title and slug only)."""
    ms = {str(m["condition_id"]): m for m in markets}
    ranked = sorted(ms, key=lambda k: _rank(seed, k))
    picked: list[str] = []
    for k in ranked:
        if len(picked) >= min_adjacent:
            break
        if sports_adjacent(ms[k].get("title")):
            picked.append(k)
    rest = n - len(picked)
    per = {g: rest // 3 + (1 if i < rest % 3 else 0) for i, g in enumerate(AUDIT_LABELS)}
    have = {g: 0 for g in AUDIT_LABELS}
    chosen = set(picked)
    for k in ranked:
        if k in chosen:
            continue
        g = audit_group(ms[k]["label"])
        if have[g] < per[g]:
            have[g] += 1
            chosen.add(k)
            picked.append(k)
        if len(picked) >= n:
            break
    for k in ranked:  # a stratum that ran short (small universe) is topped up in rank order
        if len(picked) >= n:
            break
        if k not in chosen:
            chosen.add(k)
            picked.append(k)
    return [{"condition_id": k, "title": ms[k].get("title"), "slug": ms[k].get("slug"), "label": ms[k]["label"], "sports_adjacent": sports_adjacent(ms[k].get("title"))} for k in picked]


def reviewer_view(sample: list[dict]) -> list[dict]:
    """What the independent reviewer sees: title and slug only. No labeller output, no price, no fee type."""
    return [{"condition_id": r["condition_id"], "title": r["title"], "slug": r["slug"]} for r in sample]


def audit_score(sample: list[dict], reviewer: dict[str, str]) -> dict:
    """GL: agreement on {LOW, NEWS, other} between the labeller (``sample[i]['label']``) and the reviewer (``{condition_id: LOW|NEWS|other}``). PASS iff overall >= 85% and, within
    each of LOW and NEWS, >= 80% (both ways: of the items the labeller put in the group, and of the items the reviewer put in it). A missing reviewer label is a refusal-grade error."""
    miss = [r["condition_id"] for r in sample if r["condition_id"] not in reviewer]
    bad = [v for v in reviewer.values() if v not in AUDIT_LABELS]
    if miss or bad:
        raise ValueError(f"reviewer labels incomplete or invalid: missing {len(miss)}, invalid {len(bad)}")
    pairs = [(audit_group(r["label"]), reviewer[r["condition_id"]]) for r in sample]
    n = len(pairs)
    agree = sum(1 for a, b in pairs if a == b)
    out: dict = {"n": n, "overall": agree / n if n else 0.0, "by_group": {}}
    ok_each = True
    for g in ("LOW", "NEWS"):
        lab = [(a, b) for a, b in pairs if a == g]
        rev = [(a, b) for a, b in pairs if b == g]
        s_lab = sum(1 for a, b in lab if a == b) / len(lab) if lab else 0.0
        s_rev = sum(1 for a, b in rev if a == b) / len(rev) if rev else 0.0
        out["by_group"][g] = {"labeller_n": len(lab), "reviewer_n": len(rev), "agree_of_labeller": s_lab, "agree_of_reviewer": s_rev}
        ok_each = ok_each and bool(lab) and bool(rev) and s_lab >= AUDIT_AGREE_EACH and s_rev >= AUDIT_AGREE_EACH
    out["pass"] = bool(n and out["overall"] >= AUDIT_AGREE_ALL and ok_each)
    return out


def declared() -> dict:
    return {"classes": list(CLASSES), "precedence": [SPORTS, PATH, PUBLIC, SCHEDULED, NEWS, UNKNOWN], "low": list(LOW_CLASSES), "news": list(NEWS_CLASSES),
            "inputs": "title, slug, ctx_category, ctx_fee_type (static attributes) and the touch capture sidecar fee_type, fee_category, series_slugs; no price, mark or outcome",
            "audit": {"n": AUDIT_N, "sports_adjacent_min": AUDIT_SPORTS_ADJACENT_MIN, "seeds": list(AUDIT_SEEDS), "agree_all": AUDIT_AGREE_ALL, "agree_each": AUDIT_AGREE_EACH,
                      "one_revision_allowed": True, "second_fail": "T1 and T2 not testable (labeller), counted"},
            "unknown_max_share": UNKNOWN_MAX_SHARE, "sports_counted": False}
