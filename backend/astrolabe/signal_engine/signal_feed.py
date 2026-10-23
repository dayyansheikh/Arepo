# ruff: noqa: E501
"""Per-market signal feed (schema ``se-feed-v1``; DESIGN_V1 section 27): the CHAMPION's newest write-once prediction,
read back as signal strength per market, for the owner's /lab and, after an owner-approved web deploy, the website.

- Only the champion (the model chosen by the pre-declared promotion rule) feeds it, and never while an embargo covers
  it (``specs.embargo_of``). Nothing is recomputed: the values are the stored quantised probabilities of
  ``predictions/<capture>/<champion>.parquet``, with its receipt time from the predictions log.
- Signal strength = P(up) - P(down) of a direction target, in [-1, 1]. It is forecast quality, not a probability of
  profit and not an edge claim; the champion's own prospective record (14-day leaderboard rows) ships with it.
- ``res_7d`` is left out on purpose: a model-versus-price gap at resolution reads as a trade suggestion.
- Market titles come from the public Gamma listing (bounded, cached in ``feed/titles.json``); a failed lookup only
  leaves the title empty. ``feed/latest.json`` is a rewritable view, never evidence."""

from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path

import numpy as np

from . import config as C
from . import labels as L
from . import predict as P
from . import specs as SP
from . import store as S

SCHEMA = "se-feed-v1"
TOP_N = 20
# Display pool (declared 2026-10-23 before any outcome was read; a display choice, not a model change): on a wide or
# extreme-priced book the 0.5c "flat" band is far inside the spread, so a strong strength is mostly the mid's quote
# mechanics, not a move a user could act on. Only markets inside this pool are ranked; the summary counts every
# eligible market.
POOL_SPREAD_MAX = 0.02
POOL_MID = (0.05, 0.95)
TITLE_CACHE_MAX = 3000
GAMMA_MARKETS = "https://gamma-api.polymarket.com/markets"
LABEL = ("Signal strength = the champion's forecast P(up) minus P(down) of the Polymarket mid over the horizon "
         "(flat = within 0.5c). Forecast quality only: not a probability of profit, not an edge claim, not advice.")
FEAT_COLS = ["market_id", "category", "ms_mid", "ms_spread", "ms_log_liq", "ms_hours_to_end"]


def _num(v, nd: int = 4):
    v = float(v)
    return round(v, nd) if math.isfinite(v) else None


def newest_champion_prediction(paths: S.Paths, champion: str, now: float) -> dict | None:
    """The champion's newest prediction log line (receipt) whose file is in place, from the last two days."""
    for r in reversed(S.read_logs(paths, "predictions", now - 2 * 86400)):
        if r.get("model_id") == champion and paths.predictions(r["capture_id"], champion).exists():
            return r
    return None


def fetch_titles(ids: list[int], timeout: float = 10.0) -> dict[str, dict]:
    """Public Gamma listing for up to 60 market ids in one request: question and event / market slugs."""
    if not ids:
        return {}
    url = GAMMA_MARKETS + "?" + urllib.parse.urlencode([("id", str(i)) for i in ids[:60]] + [("limit", str(len(ids[:60])))])
    req = urllib.request.Request(url, headers={"User-Agent": "arepo-research/1.0 (read-only)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - fixed public https host
        rows = json.loads(resp.read().decode("utf-8"))
    out = {}
    for m in rows if isinstance(rows, list) else []:
        ev = (m.get("events") or [{}])[0] or {}
        out[str(m.get("id"))] = {"title": (m.get("question") or "")[:200], "event_slug": ev.get("slug"),
                                 "slug": m.get("slug")}
    return out


def _titles(paths: S.Paths, ids: list[int], fetch: Callable[[list[int]], dict] | None) -> tuple[dict, str | None]:
    p = paths.sub("feed", "titles.json")
    try:
        cache = json.loads(p.read_text()) if p.exists() else {}
    except (OSError, ValueError):
        cache = {}
    missing = [i for i in ids if str(i) not in cache]
    err = None
    if missing and fetch is not None:
        try:
            got = fetch(missing)
            cache.update({k: v for k, v in got.items() if isinstance(v, dict)})
        except Exception as exc:  # noqa: BLE001 - titles are cosmetic; the feed still builds
            err = f"{type(exc).__name__}: {exc}"[:200]
        if len(cache) > TITLE_CACHE_MAX:
            cache = dict(list(cache.items())[-TITLE_CACHE_MAX:])
        S.replace_json(p, cache)
    return cache, err


def _url(t: dict | None) -> str | None:
    if not t or not t.get("event_slug"):
        return None
    base = f"https://polymarket.com/event/{t['event_slug']}"
    return f"{base}/{t['slug']}" if t.get("slug") and t["slug"] != t["event_slug"] else base


def _track_record(paths: S.Paths, champion: str) -> dict | None:
    p = paths.sub("leaderboard", "latest.json")
    try:
        lb = json.loads(p.read_text())
    except (OSError, ValueError):
        return None
    rows = [{k: r.get(k) for k in ("target", "n", "days", "log_loss", "brier", "auc", "cal_slope", "cal_intercept")}
            for r in lb.get("rows", []) if r.get("model_id") == champion and r.get("window_days") == 14
            and r.get("target") in C.DIR_TARGETS and not r.get("embargoed_until")]
    return {"generated_at": str(lb.get("generated_utc", ""))[:19] + "Z", "days_scored": lb.get("days_scored"),
            "window_days": 14, "rows": rows, "label": "prospective, write-once predictions scored after the fact"}


def build_feed(paths: S.Paths, reg: dict, now: float, top_n: int = TOP_N,
               fetch: Callable[[list[int]], dict] | None = fetch_titles) -> dict | None:
    champion = SP.current_champion(paths, reg)
    spec = reg["models"][champion]
    if SP.embargo_of(spec, now):
        return None  # never display an embargoed model's output
    line = newest_champion_prediction(paths, champion, now)
    if line is None:
        return None
    cid, slot = line["capture_id"], int(line["slot"])
    pf = S.read_parquet(paths.predictions(cid, champion))
    md = S.parquet_meta(paths.predictions(cid, champion))
    feats = S.read_parquet(paths.features(cid), columns=FEAT_COLS)
    if len(feats) != len(pf) or md.get("features_sha256") != S.sha256_file(paths.features(cid)):
        return None  # misaligned: show nothing rather than the wrong market's signal
    elig = pf["elig"].to_numpy(np.uint8)
    strength, summary = {}, {}
    for t in C.DIR_TARGETS:
        m = (elig & C.ELIG_BITS[t]) > 0
        p = P.dequantise_dir(pf[f"{t}_dn"].to_numpy(), pf[f"{t}_up"].to_numpy())
        s = np.where(m, p[:, 2] - p[:, 0], np.nan)
        strength[t] = s
        a = np.abs(s[m])
        summary[t] = {"eligible": int(m.sum()), "abs_ge_0_1": int((a >= 0.1).sum()), "abs_ge_0_25": int((a >= 0.25).sum()),
                      "mean": _num(np.nanmean(s[m])) if m.any() else None,
                      "valid_until": S.iso_s(S.slot_time(slot + L.horizon_slots(int(t[4:-1]))))}
    prim = strength[C.PRIMARY_TARGET]
    mids, spr = feats["ms_mid"].to_numpy(float), feats["ms_spread"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        pool = (spr <= POOL_SPREAD_MAX) & (mids >= POOL_MID[0]) & (mids <= POOL_MID[1])
    ok = np.isfinite(prim) & pool
    liq = feats["ms_log_liq"].to_numpy(float)
    order = np.lexsort((-np.nan_to_num(liq, nan=-1.0), -np.abs(np.nan_to_num(prim))))
    up = [i for i in order if ok[i] and prim[i] > 0][:top_n]
    dn = [i for i in order if ok[i] and prim[i] < 0][:top_n]
    ids = [int(feats["market_id"].iat[i]) for i in up + dn]
    titles, title_err = _titles(paths, ids, fetch)

    def row(i: int) -> dict:
        mid_id = int(feats["market_id"].iat[i])
        t = titles.get(str(mid_id))
        return {"market_id": mid_id, "title": (t or {}).get("title") or None, "url": _url(t),
                "category": str(feats["category"].iat[i]), "mid": _num(feats["ms_mid"].iat[i]),
                "spread": _num(feats["ms_spread"].iat[i]), "hours_to_end": _num(feats["ms_hours_to_end"].iat[i], 1),
                **{f"s_{t_[4:]}": _num(strength[t_][i], 3) for t_ in C.DIR_TARGETS}}

    idx = S.load_index(paths)
    origin = (idx.get(slot) or {}).get("started_utc")
    return S.clean_json({
        "schema": SCHEMA, "generated_at": S.iso_s(now), "engine_version": C.ENGINE_VERSION,
        "champion": {"model_id": champion, "spec_sha256": spec["_sha256"], "fit_id": line.get("fit_id")},
        "capture_id": cid, "slot": slot, "origin_utc": origin, "prediction_written_utc": line.get("written_utc"),
        "prediction_sha256": line.get("sha256"), "primary_target": C.PRIMARY_TARGET, "summary": summary,
        "top_up": [row(i) for i in up], "top_down": [row(i) for i in dn], "ranked_by": f"|s_{C.PRIMARY_TARGET[4:]}|, then liquidity",
        "pool": {"spread_max": POOL_SPREAD_MAX, "mid_range": list(POOL_MID), "markets": int((np.isfinite(prim) & pool).sum()),
                 "note": "ranked only where the spread is tight and the price is not extreme (quote mechanics dominate elsewhere)"},
        "track_record": _track_record(paths, champion), "titles_error": title_err, "label": LABEL})


def write_feed(paths: S.Paths, reg: dict, now: float, fetch: Callable[[list[int]], dict] | None = fetch_titles) -> dict:
    """Rebuild ``feed/latest.json`` when the champion has a newer prediction than the current feed (cheap no-op otherwise)."""
    p = paths.sub("feed", "latest.json")
    champion = SP.current_champion(paths, reg)
    line = newest_champion_prediction(paths, champion, now)
    try:
        cur = json.loads(p.read_text()) if p.exists() else {}
    except (OSError, ValueError):
        cur = {}
    if line is None:
        return {"built": False, "reason": "no_champion_prediction"}
    if cur.get("capture_id") == line["capture_id"] and (cur.get("champion") or {}).get("model_id") == champion:
        return {"built": False, "reason": "current", "capture_id": line["capture_id"]}
    feed = build_feed(paths, reg, now, fetch=fetch)
    if feed is None:
        return {"built": False, "reason": "refused"}
    S.replace_json(Path(p), feed)
    return {"built": True, "capture_id": feed["capture_id"], "up": len(feed["top_up"]), "down": len(feed["top_down"]),
            "titles_error": feed.get("titles_error")}
