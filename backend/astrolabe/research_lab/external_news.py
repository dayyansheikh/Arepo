# ruff: noqa: E501
"""External news/attention features per market from GDELT DOC 2.0 (research lab, family ``ml_external``).

Prototype, exploratory only. Deterministic query from the market question (no ML, no per-market tuning),
point-in-time features at an origin ``t`` using only articles whose GDELT ``seendate`` is strictly
before ``t``, and a size-capped local response cache. See ``docs/research_lab/EXTERNAL_NEWS.md`` for the
timestamp semantics and the leakage caveats.

Timestamp semantics (GDELT DOC 2.0): artlist ``seendate`` (``YYYYMMDDTHHMMSSZ``, UTC) is when GDELT first
saw the article, NOT its publication time (GDELT does not expose the publisher timestamp here). Seen time
is therefore the conservative PIT clock for "known to the index". Timeline bins are labelled by bin start;
only bins whose end is <= t are used.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"
FEATURE_VERSION = "ext-news-gdelt-v1"
CACHE_ROOT = Path("data-dumps/research_lab/external_news")
CACHE_CAP_BYTES = 500 * 1024 * 1024
MIN_INTERVAL_S = 10.0  # GDELT asks for 1 per 5 s; observed 429s at 6 s spacing, so we use 10 s
MAXRECORDS = 250  # DOC 2.0 artlist hard cap
BASELINE_DAYS = 7
WINDOWS_H = (1, 6, 24)
EVIDENCE_ROLES_OK = ("exploratory_historical", "exploratory_dev")

FEATURE_COLUMNS = [
    "ext_news_n_1h", "ext_news_n_6h", "ext_news_n_24h",
    "ext_news_ratio_1h", "ext_news_ratio_6h", "ext_news_ratio_24h",
    "ext_news_tone_mean", "ext_news_tone_change", "ext_news_n_sources_24h",
    "ext_news_hours_since_last", "ext_news_truncated",
]

# --------------------------------------------------------------------------------------- query terms
_STOP = set("""
will would could should shall does did has have had are was were been being the and for with from that this
than then over under into onto about after before during between against above below more less most least
other any all each both either neither not yes who whom whose what when where which why how end ends ended
win wins won lose loses lost price prices reach reaches hit hits close closes closed trade trades trading
market markets happen happens announce announced announces release released get gets become becomes
make makes made take takes next last first second third new top high low higher lower least much many
per vs versus out set sets say says said than ever again still yet already anyone someone another
january february march april may june july august september october november december
jan feb mar apr jun jul aug sep sept oct nov dec monday tuesday wednesday thursday friday saturday sunday by on in of to at as is be it or an a
""".split())
_GENERIC_CAP = {"Will", "Who", "What", "When", "Which", "How", "Does", "Is", "Are", "Can", "Do", "Did",
                "Yes", "No", "The", "A", "An", "By", "In", "On", "Before", "After", "Over", "Under",
                "Bitcoin Up", "Up", "Down", "Above", "Below"}
_CAP_RE = re.compile(r"\b(?:[A-Z][\w'.&-]*)(?:\s+(?:of|the|de|van|von|and|&)\s+[A-Z][\w'.&-]*|\s+[A-Z][\w'.&-]*)*")
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]{3,}")


def derive_query(question: str, event_title: str | None = None) -> dict[str, Any]:
    """Deterministic GDELT query from ``question`` (falling back to ``event_title``).

    Rule: quoted capitalised phrases (entities, first word of the sentence dropped when generic), at most the
    first two, joined by implicit AND; with no entity, the two longest non-stopword tokens. ``sourcelang:english``
    is appended. Returns ``{query, entities, nouns, source}``; ``query`` is ``None`` when nothing is extractable.
    """
    text = (question or "").strip()
    src = "question"
    ents = _entities(text)
    if not ents and event_title:
        t2 = event_title.strip()
        e2 = _entities(t2)
        if e2:
            ents, text, src = e2, t2, "event_title"
    nouns = _nouns(text)
    terms: list[str] = []
    if ents:
        terms = [f'"{e}"' for e in ents[:2]]
    elif nouns:
        terms = nouns[:2]
    if not terms:
        return {"query": None, "entities": ents, "nouns": nouns, "source": src}
    return {"query": " ".join(terms) + " sourcelang:english", "entities": ents, "nouns": nouns, "source": src}


def _entities(text: str) -> list[str]:
    out: list[str] = []
    for m in _CAP_RE.finditer(text):
        phrase = m.group(0).strip(" .'&-")
        words = phrase.split()
        while words and (words[0] in _GENERIC_CAP or words[0].lower() in ("the", "of", "and", "&")):
            words = words[1:]
        while words and (words[-1] in _GENERIC_CAP or words[-1].lower() in ("the", "of", "and", "&")):
            words = words[:-1]
        phrase = " ".join(words)
        if len(phrase) < 3 or any(ch.isdigit() for ch in phrase) or phrase.lower() in _STOP:
            continue
        if phrase.lower() not in {p.lower() for p in out}:
            out.append(phrase)
    return out


def _nouns(text: str) -> list[str]:
    toks = [w for w in _WORD_RE.findall(text) if w.lower() not in _STOP]
    seen: list[str] = []
    for w in sorted(toks, key=lambda x: (-len(x), x.lower())):
        if w.lower() not in seen:
            seen.append(w.lower())
    return seen


# --------------------------------------------------------------------------------------- time helpers
def _fmt(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y%m%d%H%M%S")


def parse_seen(s: str) -> datetime:
    return datetime.strptime(s, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)


def _as_utc(t: datetime | str) -> datetime:
    if isinstance(t, str):
        t = datetime.fromisoformat(t.replace("Z", "+00:00"))
    return t.astimezone(UTC) if t.tzinfo else t.replace(tzinfo=UTC)


# --------------------------------------------------------------------------------------- cache + client
def cache_size_bytes(root: Path) -> int:
    return sum(p.stat().st_size for p in root.rglob("*.json") if p.is_file()) if root.exists() else 0


@dataclass
class GdeltClient:
    """Rate-limited GDELT DOC client with a content-addressed local cache (<= ``cap_bytes``)."""

    cache_dir: Path = CACHE_ROOT
    cap_bytes: int = CACHE_CAP_BYTES
    min_interval_s: float = MIN_INTERVAL_S
    max_retries: int = 5
    fetch: Callable[[dict], tuple[int, str]] | None = None  # injectable for tests
    sleep: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = time.monotonic
    _last: float = field(default=-1e18, init=False)
    latencies: list[float] = field(default_factory=list, init=False)
    requests_made: int = field(default=0, init=False)
    cache_hits: int = field(default=0, init=False)
    failures: int = field(default=0, init=False)

    def _key(self, params: dict) -> Path:
        h = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:40]
        return Path(self.cache_dir) / h[:2] / f"{h}.json"

    def _http(self, params: dict) -> tuple[int, str]:
        import httpx

        r = httpx.get(ENDPOINT, params=params, timeout=60.0, headers={"User-Agent": "arepo-research/0.1"})
        return r.status_code, r.text

    def get(self, params: dict) -> dict | None:
        """Cached GET of a DOC request (``format=json`` is forced). Returns parsed JSON or ``None``.

        Only responses that parse as JSON are cached; 429/HTML/empty bodies are retried with
        backoff and then reported as ``None`` (missing, never zero).
        """
        params = {**params, "format": "json"}
        path = self._key(params)
        if path.exists():
            self.cache_hits += 1
            return json.loads(path.read_text())
        fetch = self.fetch or self._http
        delay = self.min_interval_s
        for _ in range(self.max_retries):
            wait = self.min_interval_s - (self.clock() - self._last)
            if wait > 0:
                self.sleep(wait)
            t0 = self.clock()
            try:
                status, body = fetch(params)
            except Exception as exc:  # network error: back off and retry
                log.warning("gdelt fetch error: %s", exc)
                status, body = 0, ""
            self._last = self.clock()
            self.requests_made += 1
            if status == 200:
                self.latencies.append(self._last - t0)
                try:
                    data = json.loads(body) if body.strip() else {}
                except ValueError:
                    data = None
                if data is not None:  # {} is a legitimate "no articles" reply
                    self._store(path, data)
                    return data
            delay = min(delay * 2, 300.0)
            self.sleep(delay)
        self.failures += 1
        return None

    def _store(self, path: Path, data: dict) -> None:
        if cache_size_bytes(Path(self.cache_dir)) >= self.cap_bytes:
            log.warning("external_news cache cap reached; not caching")
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, separators=(",", ":")))


# --------------------------------------------------------------------------------------- fetch + features
def fetch_artlist(client: GdeltClient, query: str, t: datetime) -> dict | None:
    t = _as_utc(t)
    return client.get({
        "query": query, "mode": "artlist", "maxrecords": MAXRECORDS, "sort": "datedesc",
        "startdatetime": _fmt(t - timedelta(days=BASELINE_DAYS)), "enddatetime": _fmt(t),
    })


def fetch_tone(client: GdeltClient, query: str, t: datetime) -> dict | None:
    t = _as_utc(t)
    return client.get({
        "query": query, "mode": "timelinetone",
        "startdatetime": _fmt(t - timedelta(days=BASELINE_DAYS)), "enddatetime": _fmt(t),
    })


def _tone_bins(tone: dict | None, t: datetime) -> list[tuple[datetime, float]]:
    """(bin_start, tone) for bins that are complete at ``t``. Bin width inferred from spacing (>=1 day
    for 7-day spans; sparse bins are possible, so we assume the day width when only one bin exists)."""
    if not tone:
        return []
    series = (tone.get("timeline") or [{}])[0].get("data") or []
    pts = sorted((parse_seen(d["date"]), float(d["value"])) for d in series if d.get("value") is not None)
    if not pts:
        return []
    res = (tone.get("query_details") or {}).get("date_resolution", "day")
    width = {"day": timedelta(days=1), "hour": timedelta(hours=1)}.get(res, timedelta(minutes=15))
    return [(s, v) for s, v in pts if s + width <= t]


def compute_features(art: dict | None, tone: dict | None, t: datetime | str) -> dict[str, Any]:
    """Features at origin ``t`` from raw responses; only articles with seendate < t. Missing -> NaN."""
    t = _as_utc(t)
    nan = float("nan")
    out: dict[str, Any] = {c: nan for c in FEATURE_COLUMNS}
    if art is None:  # fetch failed: everything missing
        return out
    arts = [a for a in (art.get("articles") or []) if a.get("seendate")]
    seen = [(parse_seen(a["seendate"]), a) for a in arts]
    seen = [(s, a) for s, a in seen if s < t and s >= t - timedelta(days=BASELINE_DAYS)]
    truncated = len(arts) >= MAXRECORDS
    oldest = min((s for s, _ in seen), default=None)
    out["ext_news_truncated"] = float(truncated)
    base_h = BASELINE_DAYS * 24 - 24
    base_start, base_end = t - timedelta(days=BASELINE_DAYS), t - timedelta(hours=24)
    n_base = sum(1 for s, _ in seen if base_start <= s < base_end)
    base_ok = not truncated or (oldest is not None and oldest <= base_start + timedelta(hours=1))
    for w in WINDOWS_H:
        n = sum(1 for s, _ in seen if s >= t - timedelta(hours=w))
        # With a truncated (newest-250) list a window is exact only when the list reaches back past it.
        exact = not truncated or (oldest is not None and oldest < t - timedelta(hours=w))
        out[f"ext_news_n_{w}h"] = float(n) if exact else nan
        if exact and base_ok and n_base > 0:
            out[f"ext_news_ratio_{w}h"] = (n / w) / (n_base / base_h)
    last24 = [(s, a) for s, a in seen if s >= t - timedelta(hours=24)]
    out["ext_news_n_sources_24h"] = float(len({a.get("domain") for _, a in last24})) if (
        not truncated or (oldest is not None and oldest < t - timedelta(hours=24))) else nan
    if seen:
        out["ext_news_hours_since_last"] = (t - max(s for s, _ in seen)).total_seconds() / 3600
    elif not truncated:
        out["ext_news_hours_since_last"] = BASELINE_DAYS * 24.0  # none in 7d: censored at 168h
    bins = _tone_bins(tone, t)
    if bins:
        last_v = bins[-1][1]
        prior = [v for _, v in bins[:-1]]
        out["ext_news_tone_mean"] = sum(v for _, v in bins) / len(bins)
        if prior:
            out["ext_news_tone_change"] = last_v - sum(prior) / len(prior)
    return out


def market_features(
    client: GdeltClient, question: str, event_title: str | None, t: datetime | str,
    evidence_role: str = "exploratory_dev",
) -> dict[str, Any]:
    """Query derivation + two fetches + features. ``evidence_role`` must be exploratory (never confirmatory)."""
    if evidence_role not in EVIDENCE_ROLES_OK:
        raise ValueError(f"external_news is exploratory only; got {evidence_role!r}")
    t = _as_utc(t)
    q = derive_query(question, event_title)
    rec: dict[str, Any] = {
        "query": q["query"], "query_source": q["source"], "origin_utc": t.isoformat(),
        "evidence_role": evidence_role, "feature_version": FEATURE_VERSION, "gdelt_clock": "seendate",
    }
    t0 = time.monotonic()
    if q["query"] is None:
        rec.update({c: float("nan") for c in FEATURE_COLUMNS})
        rec["status"] = "no_query"
        return rec
    art = fetch_artlist(client, q["query"], t)
    tone = fetch_tone(client, q["query"], t) if art is not None else None
    rec.update(compute_features(art, tone, t))
    rec["status"] = "fetch_failed" if art is None else ("no_articles" if not (art or {}).get("articles") else "ok")
    rec["top_titles"] = [a.get("title") for a in ((art or {}).get("articles") or [])[:3]]
    rec["fetch_seconds"] = round(time.monotonic() - t0, 2)
    return rec


def nan_to_none(x: Any) -> Any:
    return None if isinstance(x, float) and math.isnan(x) else x


# --------------------------------------------------------------------------------------- Wikipedia pageviews
WIKI_ENDPOINT = (
    "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user"
)
WIKI_PUBLISH_LAG = timedelta(hours=12)  # conservative: day D is used only from D+1 00:00 + 12 h
PAGEVIEW_COLUMNS = ["ext_wiki_views_last_day", "ext_wiki_views_mean_7d", "ext_wiki_ratio_1d_7d",
                    "ext_wiki_days_available"]


def wiki_article_title(entity: str) -> str:
    """Deterministic en.wikipedia title for an extracted entity (spaces to underscores, first letter
    upper-case). No search, so a wrong or missing page is simply a 404 (missing, not 0)."""
    s = entity.strip().strip('"')
    return (s[:1].upper() + s[1:]).replace(" ", "_")


def fetch_pageviews(
    entity: str, t: datetime | str, days: int = 10,
    fetch: Callable[[str], tuple[int, str]] | None = None,
) -> list[dict] | None:
    """Daily user pageviews for ``entity`` over ``days`` days ending at ``t``. None on 404/error."""
    from urllib.parse import quote

    t = _as_utc(t)
    url = (f"{WIKI_ENDPOINT}/{quote(wiki_article_title(entity), safe='_')}/daily/"
           f"{(t - timedelta(days=days)).strftime('%Y%m%d')}00/{t.strftime('%Y%m%d')}00")
    if fetch is None:
        def fetch(u: str) -> tuple[int, str]:
            import httpx

            r = httpx.get(u, timeout=30.0, headers={"User-Agent": "arepo-research/0.1"})
            return r.status_code, r.text
    try:
        status, body = fetch(url)
    except Exception:
        return None
    if status != 200:
        return None
    try:
        return json.loads(body).get("items") or []
    except ValueError:
        return None


def pageview_features(items: list[dict] | None, t: datetime | str) -> dict[str, float]:
    """Attention features at ``t`` from daily items. Day ``YYYYMMDD00`` is usable only if
    day_start + 24 h + ``WIKI_PUBLISH_LAG`` <= t (the day is over and published); the partial current
    day is never used. Ratio = last usable day / mean of the up to 7 usable days before it."""
    t = _as_utc(t)
    nan = float("nan")
    out = {c: nan for c in PAGEVIEW_COLUMNS}
    if items is None:
        return out
    days = []
    for it in items:
        try:
            d0 = datetime.strptime(str(it["timestamp"])[:8], "%Y%m%d").replace(tzinfo=UTC)
            days.append((d0, float(it["views"])))
        except (KeyError, ValueError, TypeError):
            continue
    days = sorted(x for x in days if x[0] + timedelta(days=1) + WIKI_PUBLISH_LAG <= t)
    out["ext_wiki_days_available"] = float(len(days))
    if not days:
        return out
    out["ext_wiki_views_last_day"] = days[-1][1]
    prior = [v for _, v in days[-8:-1]]
    if prior:
        mean = sum(prior) / len(prior)
        out["ext_wiki_views_mean_7d"] = mean
        if mean > 0:
            out["ext_wiki_ratio_1d_7d"] = days[-1][1] / mean
    return out
