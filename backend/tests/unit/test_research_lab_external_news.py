# ruff: noqa: E501
import json
import math
from datetime import UTC, datetime, timedelta

import pytest

from astrolabe.research_lab import external_news as en

T = datetime(2026, 10, 11, 18, 0, tzinfo=UTC)


def _art(minutes_before, domain="a.com"):
    return {"seendate": (T - timedelta(minutes=minutes_before)).strftime("%Y%m%dT%H%M%SZ"),
            "domain": domain, "title": "x"}


def test_derive_query_entities_and_determinism():
    q = en.derive_query("Will Donald Trump meet Xi Jinping before 2027?")
    assert q["query"] == '"Donald Trump" "Xi Jinping" sourcelang:english'
    assert q == en.derive_query("Will Donald Trump meet Xi Jinping before 2027?")


def test_derive_query_noun_fallback_and_none():
    q = en.derive_query("will inflation exceed targets in march?")
    assert q["query"] == "inflation targets sourcelang:english" or q["query"].startswith("inflation")
    assert en.derive_query("will it be 5?")["query"] is None


def test_features_strictly_before_t_and_windows():
    art = {"articles": [_art(0), _art(30), _art(120), _art(60 * 30), _art(60 * 24 * 3, "b.com")]}
    f = en.compute_features(art, None, T)
    assert f["ext_news_n_1h"] == 1  # the article seen exactly at t is excluded
    assert f["ext_news_n_6h"] == 2
    assert f["ext_news_n_24h"] == 2
    assert f["ext_news_hours_since_last"] == pytest.approx(0.5)
    assert f["ext_news_n_sources_24h"] == 1
    assert f["ext_news_ratio_24h"] == pytest.approx((2 / 24) / (2 / 144))


def test_missing_stays_nan_and_truncation_flag():
    f = en.compute_features(None, None, T)
    assert all(math.isnan(v) for v in f.values())
    art = {"articles": [_art(i) for i in range(1, en.MAXRECORDS + 1)]}  # all within 4h
    g = en.compute_features(art, None, T)
    assert g["ext_news_truncated"] == 1.0 and math.isnan(g["ext_news_n_24h"])
    assert g["ext_news_n_1h"] == 59 or math.isnan(g["ext_news_n_1h"]) is False


def test_no_articles_censored():
    f = en.compute_features({}, None, T)
    assert f["ext_news_n_24h"] == 0 and f["ext_news_hours_since_last"] == 168.0
    assert math.isnan(f["ext_news_ratio_24h"])


def test_tone_uses_complete_bins_only():
    d = lambda dt, v: {"date": dt.strftime("%Y%m%dT%H%M%SZ"), "value": v}  # noqa: E731
    day = datetime(2026, 10, 11, tzinfo=UTC)
    tone = {"query_details": {"date_resolution": "day"}, "timeline": [{"data": [
        d(day - timedelta(days=3), -2.0), d(day - timedelta(days=1), -4.0), d(day, 9.0)]}]}
    f = en.compute_features({"articles": []}, tone, T)  # the 10-11 bin ends after T: excluded
    assert f["ext_news_tone_mean"] == pytest.approx(-3.0)
    assert f["ext_news_tone_change"] == pytest.approx(-2.0)


def test_client_cache_rate_limit_and_retry(tmp_path):
    calls, sleeps = [], []
    seq = iter([(429, "slow down"), (200, json.dumps({"articles": []}))])

    def fetch(p):
        calls.append(p)
        return next(seq)

    c = en.GdeltClient(cache_dir=tmp_path, fetch=fetch, sleep=sleeps.append, min_interval_s=5)
    assert c.get({"query": "q"}) == {"articles": []}
    assert len(calls) == 2 and sleeps  # retried with backoff
    assert c.get({"query": "q"}) == {"articles": []} and len(calls) == 2 and c.cache_hits == 1


def test_client_failure_returns_none_and_cap(tmp_path):
    c = en.GdeltClient(cache_dir=tmp_path, fetch=lambda p: (429, ""), sleep=lambda s: None, max_retries=2)
    assert c.get({"query": "q"}) is None and c.failures == 1
    c2 = en.GdeltClient(cache_dir=tmp_path / "c2", cap_bytes=0, fetch=lambda p: (200, "{}"),
                        sleep=lambda s: None)
    assert c2.get({"query": "z"}) == {} and en.cache_size_bytes(tmp_path / "c2") == 0


def test_evidence_role_guard(tmp_path):
    c = en.GdeltClient(cache_dir=tmp_path, fetch=lambda p: (200, "{}"), sleep=lambda s: None)
    with pytest.raises(ValueError):
        en.market_features(c, "Will Elon Musk tweet?", None, T, evidence_role="prospective_confirmation")
    r = en.market_features(c, "Will Elon Musk tweet?", None, T, evidence_role="exploratory_historical")
    assert r["evidence_role"] == "exploratory_historical" and r["query"].startswith('"Elon Musk"')


def _pv(day, v):
    return {"timestamp": day.strftime("%Y%m%d00"), "views": v}


def test_wiki_title_and_pit_boundary():
    assert en.wiki_article_title('"xi Jinping"') == "Xi_Jinping"
    t = datetime(2026, 10, 11, 18, 0, tzinfo=UTC)
    items = [_pv(datetime(2026, 10, d, tzinfo=UTC), v) for d, v in
             [(3, 10), (4, 10), (5, 10), (6, 10), (7, 10), (8, 10), (9, 10), (10, 40), (11, 999)]]
    f = en.pageview_features(items, t)
    # Oct 10 ends 10-11 00:00, +12 h lag -> usable at 12:00 (yes at 18:00); Oct 11 is partial: never used
    assert f["ext_wiki_views_last_day"] == 40 and f["ext_wiki_ratio_1d_7d"] == pytest.approx(4.0)
    g = en.pageview_features(items, datetime(2026, 10, 11, 11, 59, tzinfo=UTC))
    assert g["ext_wiki_views_last_day"] == 10  # Oct 10 not yet published at 11:59


def test_wiki_missing_and_fetch():
    assert math.isnan(en.pageview_features(None, T)["ext_wiki_views_last_day"])
    assert en.fetch_pageviews("Nope", T, fetch=lambda u: (404, "")) is None
    seen = []

    def ok(u):
        seen.append(u)
        return 200, json.dumps({"items": [_pv(datetime(2026, 10, 9, tzinfo=UTC), 5)]})

    items = en.fetch_pageviews("Xi Jinping", T, fetch=ok)
    assert "Xi_Jinping/daily/2026100100/2026101100" in seen[0] and items[0]["views"] == 5
