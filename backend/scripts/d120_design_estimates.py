"""D120 design estimates: screen-then-activate pairing with group-disjoint pairs.

Design figures only, never acceptance criteria. Reproducible and read-only:

* every input is pinned by sha256 and the hashes are written into the output: the D118 complete
  frame (``fs2_capture_52eead5d...``, its sealed ``frame_report``), the D118 selection projections
  (checked against the selection inventory), eight research-lab CLOB book sweeps (four 2-sweep
  series, all before the D118 frame) and the nearest complete Gamma snapshot before the frame;
* the population is rebuilt with the production code: ``selection._member`` / ``sampling._band``
  for strata (reproducing the D118 plan: frame size, liquidity/temporal eligibility and strata),
  ``pairing.row_facts`` / ``pairing.fee_category`` / ``pairing.dependence_groups`` for category and
  dependence groups (union of every event id, every series slug and ``negRiskMarketID`` per row,
  plus the frozen underlying slug-token table, on the complete eligible frame);
* raw frame rows are matched to their projection rows by ``row_hash`` (production ``content_hash``)
  page by page, so no unverified row enters the model;
* per member: availability ``a`` = own two-sided share over the pinned sweeps, else two-sided in
  the snapshot, else the liquidity-band rate; trigger probability ``p`` = Jeffreys posterior mean
  over the member's own two-sided sweep books (|imbalance| >= 1/3 at the best level, the frozen
  ``SnapshotTriggerPolicy(1,3,...)`` rule), else the band rate (S4). S4h/S4q halve/quarter every
  untriggered probability (stress); S1 uses one pooled rate. Members are modelled as independent;
  chain completion per activated member is an assumed 0.95.

The Monte Carlo reproduces the D120 draw: strata drawn uniformly among strata with at least 8
dependence groups; within each drawn stratum, groups in random order, skipping groups claimed by an
earlier stratum, one uniform member per group; then trigger = uniform triggered member, control =
uniform untriggered member, one pair per stratum. PASS (single run) = triggers in scope >= 4, fill
>= 0.8 and >= 3 complete group-disjoint pairs; INCONCLUSIVE when fewer than 4 strata have a trigger.

    cd backend && python scripts/d120_design_estimates.py [--reps 4000] [--out PATH]
"""

import argparse
import gzip
import hashlib
import json
import sys
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

import numpy as np

from astrolabe.feature_store.admission import content_hash
from astrolabe.feature_store.capture import _strict_json
from astrolabe.research_panel import pairing
from astrolabe.research_panel.sampling import SamplingProtocol, _band
from astrolabe.research_panel.selection import _member

REPO = Path(__file__).resolve().parents[2]
DD = REPO / "data-dumps"
FRAME = DD / "fs2_capture_52eead5d6a984264a9eb0828502fb697"
SELECTION = DD / "fs2_selection_panel_d118_control_pairing_1"
LAB = DD / "research_lab"
SNAPSHOT = LAB / "snapshots" / "20261011T081844Z_24399984"
OUT = REPO / "docs" / "implementation" / "d120" / "D120_DESIGN_ESTIMATES.json"
PINNED_SHA256 = {  # every model input; a mismatch refuses to run
    "frame_report": ("fs2_capture_52eead5d6a984264a9eb0828502fb697/frame_report.json",
                     "c87995cd3608c824af20f468a8f1140d2a8835e10a9e1c994d3b20a838ceb4bb"),
    "selection_inventory": ("fs2_selection_panel_d118_control_pairing_1/inventory.json",
                            "f224f03608d1fa101de8914961ed07afc836c94a9863a8954d48de21f9ba0682"),
    "snapshot_rows": ("research_lab/snapshots/20261011T081844Z_24399984/rows.csv.gz",
                      "55668d80733cf3599f9dd921288bf6fe4e01530901095b205d1bf1afe37ba986"),
}
PINNED_SWEEPS = {  # four complete 2-sweep series on 2026-10-11, all before the D118 frame
    "20261011T022944Z_eba4a73e": "d9f4cfc78f4f9f33fdc85fe3385c9cdaf45ac75f6cd80ba81859ba2eed334e84",
    "20261011T023104Z_4de8c806": "61eeb6384a544a51c2b11eea6e39cb2f4e148a7a9a8bef482e7898af711c1bad",
    "20261011T042652Z_b6267963": "0d582675d67696cec2a5d685bf105c3e04bf02ace6e9bc7272376244b7bf9626",
    "20261011T042817Z_4a74b788": "8ec2286279ff0de29fad009f2223e21fb25f825a69553afb1d688e04f3d38ff0",
    "20261011T062543Z_2c949680": "2387ac3cde5619f888ec7f6d25d4ec3b4cd3edc7d4ff9c6173ecefb512fc15dc",
    "20261011T062706Z_14acad4b": "40162b90ec9fc076515d5ab2b127fa26a13569f6bb5d903d24d643c377cd23d1",
    "20261011T082521Z_e0a9b847": "2d1e89685cef60ee7eb5b4b6c802eae27938117351ba3c6fa63a1686ff702d6e",
    "20261011T082643Z_077269f2": "314e138233cdb1ef053ee6c7afd38fca38fca1f793d51a794f4c9efca47d2d41",
}
SEED = 20261011
CHAIN = 0.95
SCALES = {"S1": 1.0, "S4": 1.0, "S4h": 0.5, "S4q": 0.25}
SCENARIOS = {
    "S1": "pooled two-sided sweep trigger rate for every member",
    "S4": "member-specific Jeffreys trigger probability (own sweeps, else band rate)",
    "S4h": "S4 with every untriggered probability halved (stress)",
    "S4q": "S4 with every untriggered probability quartered (harshest defined stress)",
}
SHAPES = ((6, 16), (6, 12))
MIN_GROUPS = 8
VARIANTS = {
    "PL_all": {"exclude": (), "underlying": True,
               "note": "D118 population (temporal and frame liquidity >= 1000), all categories"},
    "PL_all_no_underlying": {"exclude": (), "underlying": False,
                             "note": "as PL_all without the underlying slug-token table"},
    "PL_exclude_sports": {"exclude": ("sports",), "underlying": True,
                          "note": "category policy parameter: sports excluded"},
}


def sha(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def decimal(value):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() else None


def raw_rows(capture):
    data = (FRAME / capture / "raw.bin").read_bytes()
    try:
        data = gzip.decompress(data)
    except OSError:
        pass
    return _strict_json(data)["markets"]


def load_population():
    """D118 sampling members with production strata and pairing facts (verified by row hash)."""
    policy = json.loads((SELECTION / "selection_policy.json").read_bytes())
    inventory = json.loads((SELECTION / "inventory.json").read_bytes())
    plan = json.loads((SELECTION / "selection_plan.json").read_bytes())
    inventory_ack = json.loads((SELECTION / "inventory_ack.json").read_bytes())
    if hashlib.sha256((SELECTION / "inventory.json").read_bytes()).hexdigest() != (
            inventory_ack["payload_hash"]):
        raise ValueError("D118 selection inventory differs from its acknowledgement")
    excluded = {e["market_id"]: e["reason"] for e in plan["exclusions"]}
    edges = SamplingProtocol("a" * 64, 1, 1, 1, 1)
    members, facts = [], {}
    for entry in inventory["pages"]:
        folder = SELECTION / "pages" / entry["capture_id"]
        data = (folder / "projection.json").read_bytes()
        if hashlib.sha256(data).hexdigest() != entry["projection_hash"]:
            raise ValueError("D118 selection projection differs from its inventory")
        ack = json.loads((folder / "projection_ack.json").read_bytes())
        rows = json.loads(data)["rows"]
        raw = None
        for row in rows:
            member = _member(row, ack["durable_ack"], policy["declared_at"])
            if member is None:
                continue
            if raw is None:
                raw = raw_rows(entry["capture_id"])
            source = raw[row["source_index"]]
            if content_hash(source) != row["row_hash"]:
                raise ValueError("raw frame row differs from its projection row hash")
            fact = pairing.row_facts(source)
            facts[member.market_id] = {k: fact[k] for k in (
                "event_ids", "series_slugs", "event_slugs", "neg_risk_market_id",
                "fee_type", "fee_category", "parent_event_ids")}
            members.append({
                "market_id": member.market_id, "token_id": member.token_id,
                "key": (member.time_stratum, member.close_stratum,
                        _band(member.probability, edges.probability_edges),
                        _band(member.liquidity, edges.liquidity_edges)),
                "eligible": member.market_id not in excluded,
                "category": fact["fee_category"],
            })
        del rows, raw
    pl = [m for m in members if m["eligible"]]
    fidelity = {
        "sampling_members": len(members), "d118_plan_frame_size": plan["frame_size"],
        "eligible": len(pl),
        "d118_plan_selection_eligible_member_count": plan["selection_eligible_member_count"],
        "eligible_strata_without_category": len({m["key"] for m in pl}),
        "d118_plan_eligible_strata": plan["stratum_draw"]["eligible_strata"],
    }
    fidelity["reproduces_d118"] = (
        fidelity["sampling_members"] == fidelity["d118_plan_frame_size"]
        and fidelity["eligible"] == fidelity["d118_plan_selection_eligible_member_count"]
        and fidelity["eligible_strata_without_category"] == fidelity["d118_plan_eligible_strata"])
    return members, facts, fidelity


def triggered(bid_size, ask_size):
    b, a = decimal(bid_size), decimal(ask_size)
    if b is None or a is None or b <= 0 or a <= 0:
        return None
    return int(3 * abs(b - a) >= b + a)


def load_sweeps(names):
    import pandas as pd

    per = defaultdict(lambda: [0, 0, 0])  # seen, two-sided assessable, triggered
    states = defaultdict(dict)  # token -> {(series, index): verdict}
    manifests = {}
    for name in names:
        folder = LAB / "book_sweeps" / name
        manifest = json.loads((folder / "manifest.json").read_bytes())
        manifests[name] = {"series_id": manifest["series_id"],
                           "series_index": manifest["series_index"],
                           "state": manifest["state"],
                           "rows_sha256": sha(folder / "rows.csv.gz"),
                           "manifest_sha256": sha(folder / "manifest.json")}
        position = (manifest["series_id"], manifest["series_index"])
        for chunk in pd.read_csv(folder / "rows.csv.gz", dtype=str, keep_default_na=False,
                                 usecols=["token_id", "state", "bid_size_1", "ask_size_1"],
                                 chunksize=50000):
            columns = chunk[["token_id", "state", "bid_size_1", "ask_size_1"]]
            for token, state, b, a in columns.itertuples(index=False):
                record = per[token]
                record[0] += 1
                verdict = triggered(b, a) if state == "two_sided" else None
                if verdict is not None:
                    record[1] += 1
                    record[2] += verdict
                states[token][position] = verdict
    flips = Counter()
    for by_position in states.values():
        for (series, index), verdict in by_position.items():
            later = by_position.get((series, index + 1))
            if verdict is None or later is None:
                continue
            flips[(verdict, later)] += 1
    t_total = flips[(1, 1)] + flips[(1, 0)]
    u_total = flips[(0, 0)] + flips[(0, 1)]
    persistence = {
        "basis": "same token assessable in consecutive sweeps of one series (about 80 s apart)",
        "pairs": sum(flips.values()),
        "unchanged_share": round((flips[(1, 1)] + flips[(0, 0)]) / max(sum(flips.values()), 1),
                                 4),
        "P_untriggered_next_given_triggered": round(flips[(1, 0)] / max(t_total, 1), 4),
        "P_triggered_next_given_untriggered": round(flips[(0, 1)] / max(u_total, 1), 4),
        "counts": {f"{a}->{b}": flips[(a, b)] for a in (1, 0) for b in (1, 0)},
    }
    return dict(per), persistence, manifests


def load_snapshot():
    import pandas as pd

    frame = pd.read_csv(SNAPSHOT / "rows.csv.gz", usecols=["market_id", "best_bid", "best_ask"],
                        dtype={"market_id": str})
    bid, ask = frame["best_bid"], frame["best_ask"]
    two = (bid.notna() & ask.notna() & (bid > 0) & (ask < 1) & (bid < ask)).to_numpy()
    return dict(zip(frame["market_id"].to_numpy(), two, strict=True))


def model(pl, sweeps, snapshot):
    band_n = defaultdict(lambda: [0, 0])
    for m in pl:
        record = sweeps.get(m["token_id"])
        if record:
            band_n[m["key"][3]][0] += record[1]
            band_n[m["key"][3]][1] += record[2]
    band_rate = {b: (k + 0.5) / (n + 1) for b, (n, k) in band_n.items()}
    pooled_n = sum(v[0] for v in band_n.values())
    pooled = sum(v[1] for v in band_n.values()) / max(pooled_n, 1)
    avail_band = defaultdict(lambda: [0, 0])
    for m in pl:
        if m["market_id"] in snapshot:
            avail_band[m["key"][3]][0] += 1
            avail_band[m["key"][3]][1] += bool(snapshot[m["market_id"]])
    avail_rate = {b: k / n for b, (n, k) in avail_band.items() if n}
    coverage = Counter()
    for m in pl:
        record = sweeps.get(m["token_id"])
        if record and record[0]:
            m["a"] = record[1] / record[0]
            coverage["availability_from_own_sweeps"] += 1
        elif m["market_id"] in snapshot:
            m["a"] = float(bool(snapshot[m["market_id"]]))
            coverage["availability_from_snapshot"] += 1
        else:
            m["a"] = avail_rate.get(m["key"][3], 0.0)
            coverage["availability_from_band_rate"] += 1
        if record and record[1]:
            m["p"] = (record[2] + 0.5) / (record[1] + 1)
            coverage["trigger_from_own_sweeps"] += 1
        else:
            m["p"] = band_rate.get(m["key"][3], pooled)
            coverage["trigger_from_band_rate"] += 1
    return {"pooled_trigger_rate": round(pooled, 4),
            "band_trigger_rate": {k: round(v, 4) for k, v in sorted(band_rate.items())},
            "band_snapshot_availability": {k: round(v, 4) for k, v in sorted(avail_rate.items())},
            "coverage": dict(coverage),
            "mean_a": round(float(np.mean([m["a"] for m in pl])), 4),
            "mean_p_given_available": round(float(
                sum(m["a"] * m["p"] for m in pl) / max(sum(m["a"] for m in pl), 1e-12)), 4)}, \
        pooled


def strata_for(pl, groups, exclude):
    strata = defaultdict(lambda: defaultdict(list))
    for i, m in enumerate(pl):
        if m["category"] in exclude:
            continue
        key = (*m["key"], pairing.STRATUM_CATEGORY_PREFIX + m["category"])
        strata[key][groups[m["market_id"]]].append(i)
    out = []
    for key, by_group in strata.items():
        gids = sorted(by_group)
        out.append({"key": key, "gids": gids, "members": [np.array(by_group[g]) for g in gids],
                    "n": sum(len(v) for v in by_group.values()),
                    "category": key[4][len(pairing.STRATUM_CATEGORY_PREFIX):]})
    return out


def simulate(drawable, pl, pooled, shape, reps):
    strata_n, per = shape
    rng = np.random.default_rng(SEED)
    a = np.array([m["a"] for m in pl])
    p = np.array([m["p"] for m in pl])
    cats = [m["category"] for m in pl]
    stats = {sc: Counter() for sc in SCALES}
    composition = {sc: {"screened": Counter(), "pairs": Counter()} for sc in SCALES}
    for _ in range(reps):
        chosen_strata = rng.choice(len(drawable), size=min(strata_n, len(drawable)),
                                   replace=False)
        claimed, drawn = set(), []
        for si in chosen_strata:
            s = drawable[si]
            picks = []
            for gi in rng.permutation(len(s["gids"])):
                gid = s["gids"][gi]
                if gid in claimed:
                    continue
                group = s["members"][gi]
                picks.append(int(group[rng.integers(len(group))]))
                claimed.add(gid)
                if len(picks) == per:
                    break
            drawn.append(np.array(picks, dtype=int))
        ua = [rng.random(len(c)) for c in drawn]
        ut = [rng.random(len(c)) for c in drawn]
        uc = rng.random((len(drawn), 2))
        for sc, scale in SCALES.items():
            r = stats[sc]
            triggers = pairs = complete = strata_t = scarcity = screened = 0
            for c, xa, xt, cc in zip(drawn, ua, ut, uc, strict=True):
                screened += len(c)
                for i in c:
                    composition[sc]["screened"][cats[i]] += 1
                avail = xa < a[c]
                prob = pooled if sc == "S1" else p[c]
                trig = avail & (xt < 1 - (1 - prob) * scale)
                unt = avail & ~trig
                if trig.any():
                    strata_t += 1
                    triggers += 1
                    if unt.any():
                        pairs += 1
                        composition[sc]["pairs"][cats[c[0]]] += 1
                        complete += bool(cc[0] < CHAIN and cc[1] < CHAIN)
                    else:
                        scarcity += 1
            fill_ok = triggers >= 4 and pairs >= 0.8 * triggers
            r["reps"] += 1
            r["screened"] += screened
            r["triggers"] += triggers
            r["pairs"] += pairs
            r["complete"] += complete
            r["fill_ok"] += fill_ok
            r["pass"] += fill_ok and complete >= 3
            r["triggers_lt_4"] += triggers < 4
            r["inconclusive_strata_with_trigger_lt_4"] += strata_t < 4
            r["any_scarcity"] += scarcity > 0
            r["fill_sum"] += pairs / triggers if triggers else 0
            r["runs_with_trigger"] += triggers > 0
            for k in (1, 2, 3, 4, 5, 6):
                r[f"complete_ge_{k}"] += complete >= k
    out = {}
    for sc in SCALES:
        r = stats[sc]
        n = r["reps"]
        screened_total = sum(composition[sc]["screened"].values())
        pairs_total = sum(composition[sc]["pairs"].values())
        out[sc] = {
            "P_fill_ok_and_ind_ge_3": round(r["pass"] / n, 3),
            "P_fill_ge_0.8_with_ge_4_triggers": round(r["fill_ok"] / n, 3),
            "P_triggers_in_scope_lt_4": round(r["triggers_lt_4"] / n, 3),
            "P_strata_with_trigger_lt_4": round(r["inconclusive_strata_with_trigger_lt_4"] / n,
                                                3),
            "P_any_control_scarcity": round(r["any_scarcity"] / n, 3),
            "E_screened": round(r["screened"] / n, 2),
            "E_triggers_in_scope": round(r["triggers"] / n, 3),
            "E_pairs": round(r["pairs"] / n, 3),
            "E_group_disjoint_complete_pairs": round(r["complete"] / n, 3),
            "mean_fill_given_trigger": round(r["fill_sum"] / max(r["runs_with_trigger"], 1), 3),
            **{f"P_group_disjoint_complete_pairs_ge_{k}": round(r[f"complete_ge_{k}"] / n, 3)
               for k in (1, 2, 3, 4, 5, 6)},
            "expected_run_category_share_screened": {
                k: round(v / screened_total, 4)
                for k, v in composition[sc]["screened"].most_common()} if screened_total else {},
            "expected_run_category_share_pairs": {
                k: round(v / pairs_total, 4)
                for k, v in composition[sc]["pairs"].most_common()} if pairs_total else {},
        }
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reps", type=int, default=4000)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args(argv)
    for name, digest in PINNED_SWEEPS.items():
        if sha(LAB / "book_sweeps" / name / "rows.csv.gz") != digest:
            raise ValueError(f"pinned sweep {name} differs from its recorded sha256")
    for name, (rel, digest) in PINNED_SHA256.items():
        if sha(DD / rel) != digest:
            raise ValueError(f"pinned input {name} differs from its recorded sha256")
    members, facts, fidelity = load_population()
    print("population loaded", fidelity, file=sys.stderr, flush=True)
    pl = [m for m in members if m["eligible"]]
    sweeps, persistence, manifests = load_sweeps(PINNED_SWEEPS)
    snapshot = load_snapshot()
    model_info, pooled = model(pl, sweeps, snapshot)
    del sweeps, snapshot
    report = {
        "schema_version": "d120-design-estimates-v1",
        "status": "design figures only; never acceptance criteria",
        "script": "backend/scripts/d120_design_estimates.py",
        "inputs": {
            "frame_root": FRAME.name,
            "pinned_sha256": {k: v[1] for k, v in PINNED_SHA256.items()},
            "frame_report_ack_sha256": sha(FRAME / "frame_report_ack.json"),
            "selection_root": SELECTION.name,
            "selection_inventory_sha256": sha(SELECTION / "inventory.json"),
            "selection_plan_sha256": sha(SELECTION / "selection_plan.json"),
            "snapshot": SNAPSHOT.name,
            "snapshot_manifest_sha256": sha(SNAPSHOT / "manifest.json"),
            "sweeps": manifests,
            "row_verification": "every eligible-frame raw row matched to its projection row_hash",
        },
        "seed": SEED, "reps": args.reps, "chain_completion_per_member": CHAIN,
        "scenarios": SCENARIOS, "untriggered_scale": SCALES,
        "fidelity": fidelity, "model": model_info, "trigger_persistence": persistence,
        "fee_category_map": {"version": pairing.FEE_CATEGORY_MAP_VERSION,
                             "prefixes": [list(x) for x in pairing.FEE_CATEGORY_PREFIXES]},
        "variants": {},
    }
    eligible_ids = {m["market_id"] for m in pl}
    links = Counter()
    for market in eligible_ids:
        f = facts[market]
        links["rows"] += 1
        links["with_event"] += bool(f["event_ids"])
        links["with_series"] += bool(f["series_slugs"])
        links["with_neg_risk"] += f["neg_risk_market_id"] is not None
        links["more_than_one_event"] += len(f["event_ids"]) > 1
        links["more_than_one_series"] += len(f["series_slugs"]) > 1
        links["with_parent_event_not_unioned"] += bool(f["parent_event_ids"])
        links["with_underlying_token"] += bool(pairing.underlyings(f))
    report["link_coverage_eligible"] = dict(links)
    report["eligible_category_counts"] = dict(Counter(m["category"] for m in pl).most_common())
    report["eligible_fee_type_counts"] = dict(Counter(
        facts[m["market_id"]]["fee_type"] for m in pl).most_common(40))
    groups_by_mode = {}
    for underlying in (True, False):
        groups_by_mode[underlying] = pairing.dependence_groups(facts, underlying=underlying)
        print("groups built", underlying, file=sys.stderr, flush=True)
    del facts
    for name, variant in VARIANTS.items():
        groups = groups_by_mode[variant["underlying"]]
        strata = strata_for(pl, groups, set(variant["exclude"]))
        drawable = [s for s in strata if len(s["gids"]) >= MIN_GROUPS]
        g = np.array([len(s["gids"]) for s in drawable])
        population = sum(s["n"] for s in strata)
        info = {
            "note": variant["note"], "exclude_categories": list(variant["exclude"]),
            "underlying_grouping": variant["underlying"],
            "grouping_policy": pairing.grouping_policy(variant["underlying"]),
            "members": population,
            "dependence_groups": len({groups[pl[int(i)]["market_id"]] for s in strata
                                      for grp in s["members"] for i in grp}),
            "strata_all": len(strata), "strata_drawable_ge_8_groups": len(drawable),
            "members_in_drawable_strata": int(sum(s["n"] for s in drawable)),
            "share_members_in_drawable_strata": round(
                sum(s["n"] for s in drawable) / max(population, 1), 4),
            "groups_per_drawable_stratum_quantiles": np.quantile(
                g, [0, .1, .25, .5, .75, .9, 1]).tolist() if len(g) else None,
            "drawable_strata_with_ge_16_groups": int((g >= 16).sum()) if len(g) else 0,
            "drawable_strata_with_ge_12_groups": int((g >= 12).sum()) if len(g) else 0,
            "drawable_strata_by_category": dict(Counter(
                s["category"] for s in drawable).most_common()),
            "drawable_members_by_category": dict(sorted(Counter(
                {c: sum(s["n"] for s in drawable if s["category"] == c)
                 for c in {s["category"] for s in drawable}}).items(),
                key=lambda kv: -kv[1])),
            "shapes": {},
        }
        for shape in SHAPES:
            info["shapes"][f"{shape[0]}x{shape[1]}"] = simulate(drawable, pl, pooled, shape,
                                                                 args.reps)
            print("simulated", name, shape, file=sys.stderr, flush=True)
        report["variants"][name] = info
    chosen = report["variants"]["PL_all"]["shapes"]["6x16"]
    report["headline"] = {
        "design": "PL_all, 6 strata x 16 screened groups, 1 pair per stratum, <= 12 origins",
        "P_pass_by_scenario": {sc: chosen[sc]["P_fill_ok_and_ind_ge_3"] for sc in SCALES},
        "honest_lower_bound_defined_scenarios": min(
            chosen[sc]["P_fill_ok_and_ind_ge_3"] for sc in ("S4", "S4h", "S4q")),
        "lower_bound_note": "S4q is the harshest defined stress, not a true lower bound: "
                            "availability is a sweep/snapshot proxy, members are modelled as "
                            "independent and chain completion is an assumed 0.95",
        "expected_state_disagreements_per_run_S4": round(
            chosen["S4"]["E_pairs"] * (persistence["P_untriggered_next_given_triggered"]
                                       + persistence["P_triggered_next_given_untriggered"]), 3),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1, sort_keys=False, default=str) + "\n")
    print(json.dumps(report["headline"], indent=1))


if __name__ == "__main__":
    main()
