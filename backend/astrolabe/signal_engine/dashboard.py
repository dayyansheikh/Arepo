# ruff: noqa: E501
"""Compact ``signal_engine/dashboard.json`` (schema ``se-dash-v1``, < 100 KB) that ``scripts/lab/lab_host.py`` embeds
in the /lab snapshot as ``signal_engine``. Prospective rows and the development/historical block are kept apart, and
embargoed models carry only ``embargoed_until`` (no numbers) until their date."""

from __future__ import annotations

import json
from pathlib import Path

from . import config as C
from . import specs as SP
from . import store as S

KEEP = ("model_id", "role", "target", "window_days", "n", "log_loss", "brier", "cal_slope", "cal_intercept", "auc",
        "coverage", "days")


def _row(r: dict) -> dict:
    out = {k: r[k] for k in KEEP if k in r}
    g = r.get("gain_vs_champion")
    if g:
        out.update({"gain": g["mean"], "gain_lo": g["lo"], "gain_hi": g["hi"], "days_positive": g["days_positive"],
                    "n_days": g["n_days"], "n_clusters": g["n_clusters"]})
    m = r.get("gain_vs_market_mid")  # res_7d only: gain over the market-price reference (scoring.REF_MODEL)
    if m:
        out.update({"gain_vs_mid": m["mean"], "gain_vs_mid_lo": m["lo"], "gain_vs_mid_hi": m["hi"]})
    return out


def _family(spec: dict) -> str:
    if spec.get("broad"):
        return f"combination ({spec['learner']})"
    iso = spec.get("isolates") or []
    return "+".join(iso) if iso else ("baseline" if spec["learner"] == "logreg" else f"baseline ({spec['learner']})")


def _attribution(paths: S.Paths, reg: dict, now: float) -> list[dict]:
    """Primary-target family attribution of each active LightGBM model's newest fit (development diagnostic).
    Families under an active embargo token are dropped entirely (no value, no share), so nothing about them leaks."""
    from . import training as T

    active = {e["token"]: e["until"] for e in C.EMBARGO if now < S.epoch(e["until"])}
    out = []
    for mid, spec in SP.active_models(reg).items():
        if spec["learner"] != "lgbm" or SP.embargo_of(spec, now):
            continue
        fit = T.latest_fit(paths, mid, now)
        if fit is None:
            continue
        try:
            art = json.loads((Path(fit["_dir"]) / f"{C.PRIMARY_TARGET}.json").read_text())
        except (OSError, ValueError, KeyError):
            continue
        a = art.get("attribution")
        if not a:
            continue
        fams = {f: v for f, v in a["families"].items() if f not in active}
        out.append({"model_id": mid, "fit_time": art.get("fit_time"), "target": C.PRIMARY_TARGET, "method": a["method"],
                    "block": a["block"], "rows": a["rows"], "families": fams,
                    "hidden": sorted(f for f in a["families"] if f in active),
                    "label": "development diagnostic (mean |SHAP| on the fit's validation block), not a score"})
    return out


CHECKS = ("c1_days", "c2_ci", "c3_days_positive", "c4_calibration", "c5_secondary", "c6_coverage", "c7_cooldown")


def _promotion(dec: dict | None, emb: dict) -> dict | None:
    """Compact view of the leaderboard's promotion decision: per candidate the rule's checks, the event-clustered lower
    bound and the two-way (event + day) bound with its event and day components, and whether it may be promoted at all
    (section 21). Informational; the decision itself is
    the leaderboard file. Embargoed models never appear (the rule skips them; re-checked here and in lab_host)."""
    if not isinstance(dec, dict):
        return None
    from . import promotion as PR

    cands = []
    for mid, c in (dec.get("checks") or {}).items():
        if emb.get(mid) or not isinstance(c, dict):
            continue
        g, tw = c.get("gain") or {}, c.get("gain_twoway") or {}
        cands.append({"model_id": mid, "pass": bool(c.get("pass")), "eligible": c.get("eligible", True) is not False,
                      "ineligible_since": c.get("ineligible_since"), "days": c.get("days"),
                      "age_days": c.get("age_days"), "days_to_min": max(0.0, PR.MIN_DAYS - (c.get("age_days") or 0.0)),
                      "checks": {k: bool(c.get(k)) for k in CHECKS},
                      "gain": g.get("mean"), "lo_event": g.get("lo"), "lo_twoway": tw.get("lo"),
                      "se_event": tw.get("se_event"), "se_day": tw.get("se_day"), "n_days": tw.get("n_days")})
    return {"rule": dec.get("rule"), "at": dec.get("at"), "K": dec.get("K"), "level": dec.get("level"),
            "min_days": PR.MIN_DAYS, "promote": dec.get("promote"), "reason": dec.get("reason"), "candidates": cands,
            "label": "promotion-rule status (forecast quality, primary target); not an edge claim"}


def live_status(paths: S.Paths, now: float) -> dict:
    """Latest refit and prediction from the engine's logs (no scores, no model numbers). The daily dashboard embeds it,
    and lab_host re-reads it on every push, so a refit that stops shows its real age within 10 minutes."""
    out = {}
    fits = S.read_logs(paths, "fits", now - 3 * 86400)
    if fits:
        last = max(S.epoch(f["fit_time"]) for f in fits)
        lf = [f for f in fits if S.epoch(f["fit_time"]) == last]
        out["last_refit"] = {"at": S.iso_s(last), "models": len(lf),
                             "targets_ok": sum(1 for f in lf for t in f["targets"].values() if t.get("status") == "ok")}
    preds = S.read_logs(paths, "predictions", now - 2 * 86400)
    if preds:
        lp = preds[-1]
        out["last_prediction"] = {"capture_id": lp["capture_id"], "at": lp["written_utc"][:19] + "Z",
                                  "models": len({p["model_id"] for p in preds if p["capture_id"] == lp["capture_id"]})}
    try:  # input coverage written by the tick (section 31); inputs only, no scores
        from . import input_health as IH

        ih = IH.read(paths)
    except Exception:  # noqa: BLE001 - the monitor never breaks the dashboard
        ih = None
    if ih is not None:
        out["inputs"] = ih
    return out


def build(paths: S.Paths, reg: dict, champion: str, now: float, lb: dict | None, history_days: int = 28) -> dict:
    models = reg["models"]
    emb = {m: SP.embargo_of(s, now) for m, s in models.items()}
    out = {"schema": "se-dash-v1", "generated_at": S.iso_s(now), "engine_version": C.ENGINE_VERSION,
           "primary_target": C.PRIMARY_TARGET,
           "champion": {"model_id": champion, "spec_sha256": models[champion]["_sha256"], "family": _family(models[champion])},
           "models": [{"model_id": m, "family": _family(s), "learner": s["learner"], "status": s["_status"],
                       "embargoed_until": emb[m]["until"] if emb[m] else None,
                       "embargo_tests": emb[m]["tests"] if emb[m] else None} for m, s in models.items()],
           "note": "Signal strength / forecast quality only; not probability of profit, not an edge claim."}
    out.update(live_status(paths, now))
    if lb:
        days = lb.get("days_scored", 0)
        out["prospective"] = {"generated_at": lb["generated_utc"][:19] + "Z", "days_scored": days,
                              "status": "bootstrapping" if days < 14 else "scoring",
                              "rows": [_row(r) if not r.get("embargoed_until") else
                                       {"model_id": r["model_id"], "embargoed_until": r["embargoed_until"]}
                                       for r in lb["rows"] if r.get("embargoed_until") or r.get("window_days") == 14]}
        out["promotion"] = _promotion(lb.get("promotion"), emb)
    else:
        out["prospective"] = {"status": "bootstrapping", "days_scored": 0, "rows": []}
    # family gains over time: the 14-day primary-target gain of each daily leaderboard
    series = []
    d = paths.sub("leaderboard")
    for p in sorted(d.glob("2*.json"))[-history_days:] if d.exists() else []:
        try:
            old = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        for r in old.get("rows", []):
            g = r.get("gain_vs_champion")
            if (r.get("window_days") == 14 and r.get("target") == C.PRIMARY_TARGET and g
                    and r["model_id"] in models and not emb.get(r["model_id"])):
                series.append({"date": old["generated_utc"][:10], "model_id": r["model_id"],
                               "family": _family(models[r["model_id"]]), "gain": g["mean"], "lo": g["lo"], "hi": g["hi"]})
    out["family_gains"] = series
    dev_p = paths.sub("dev", "latest.json")
    if dev_p.exists():
        try:
            dev = json.loads(dev_p.read_text())
            out["development"] = {"label": "development/historical", "generated_at": dev["generated_utc"][:19] + "Z",
                                  "test_days": dev.get("test_days"),
                                  "rows": [_row(r) if not r.get("embargoed_until") or S.epoch(r["embargoed_until"]) <= now else
                                           {"model_id": r["model_id"], "embargoed_until": r["embargoed_until"]}
                                           for r in dev["rows"]]}
        except (OSError, ValueError, KeyError):
            pass
    out["attribution"] = _attribution(paths, reg, now)
    out["embargo_tokens"] = [{"token": e["token"], "until": e["until"]} for e in C.EMBARGO if now < S.epoch(e["until"])]
    hist = SP.champion_history(paths)
    out["promotions"] = hist[-10:]
    return S.clean_json(out)
