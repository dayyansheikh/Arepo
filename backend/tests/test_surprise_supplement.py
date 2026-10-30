"""E011 descriptive supplement on synthetic line files."""

from __future__ import annotations

from astrolabe.research_lab import surprise_snapshot as ss
from astrolabe.research_lab import surprise_supplement as sup


def _lab(aid, hit, hit2, mv):
    return {"alert_id": aid, "what": "label", "status": "evaluated", "hit_6h": hit,
            "hit_2h": hit2, "sharp_any_6h": hit, "fwd_move_6h": mv, "fwd_move_24h": mv}


def test_supplement_outputs_and_same_episodes_as_analyze(tmp_path):
    t0 = ss._epoch(ss.REGISTERED_UTC) + 1860  # first capture 14:31Z
    lines, outs, passes = [], [], []
    for p in range(12):
        if p == 5:  # a missed pass
            continue
        cap = t0 + p * 7200
        passes.append({"capture_id": f"c{p}", "t": cap, "status": "ok", "n_eligible": 27000,
                       "requests": 800, "seconds": 210.0 + p})
        for k in range(4):
            i = p * 4 + k
            aid = f"a{i}"
            lines.append({"type": "alert", "alert_id": aid, "market_id": f"m{i % 30}",
                          "event_id": f"e{i % 17}", "t": cap + 300, "capture_t": cap,
                          "evidence_role": "prospective_confirmation",
                          "fee_category": "sports" if k % 2 else "politics"})
            outs.append(_lab(aid, k == 0, k == 0 and p % 2 == 0, 0.2 if k == 0 else 0.0))
            for j in range(3):
                cid = f"{aid}_{j}"
                lines.append({"type": "control", "alert_id": cid, "control_for": aid,
                              "market_id": f"x{i}_{j}", "t": cap + 300,
                              "control_match": "stratum" if j else "price_band",
                              "evidence_role": "prospective_confirmation"})
                outs.append(_lab(cid, False, False, 0.0))
    lines.append({"type": "control_shortfall", "alert_id": "a0", "wanted": 3, "got": 2})
    ss.append_jsonl(tmp_path / "alerts.jsonl", lines)
    ss.append_jsonl(tmp_path / "outcomes.jsonl", outs)
    ss.append_jsonl(tmp_path / "passes.jsonl", passes)
    s = sup.supplement(tmp_path, n_boot=100, end_utc=ss.utc_iso(t0 + 11 * 7200 + 60))
    a = ss.analyze(tmp_path, n_boot=50, end_utc=ss.utc_iso(t0 + 11 * 7200 + 60))
    assert (s["n_episodes"], s["n_episodes_analysed"]) == (a["n_episodes"],
                                                           a["n_episodes_analysed"])
    assert s["c_label_2h"]["rate_control"] == 0.0 and s["c_label_2h"]["rate_alert"] > 0
    assert s["d_abs_move_ge_0.15"]["6h"]["rate_control"] == 0.0
    e = s["e_sports_vs_non_sports"]
    assert e["sports"]["n"] + e["non_sports"]["n"] == s["n_episodes_analysed"]
    assert e["sports"]["rate_alert"] == 0.0  # only k == 0 (politics) hits
    f = s["f_control_match"]
    assert f["lines"] == {"stratum": 88, "price_band": 44} and f["control_shortfall_lines"] == 1
    g = s["g_passes"]
    assert g["missed_slots"] == [ss.utc_iso(t0 + 5 * 7200)]
    assert g["captures_with_alerts"] == 11 and g["passes_logged"] == 11
    assert g["seconds"]["max"] == 221.0 and g["requests"]["median"] == 800.0
    assert "verdict" not in s
