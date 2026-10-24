"""D118 design estimates: P(at least one complete matched pair) per population, design, scenario.

Design figures only, never acceptance criteria. Reproducible and read-only:

* fixed seed; every input file is hashed into the output; the D116 selection pages are verified
  against the selection inventory before use;
* population members are rebuilt with the production selection code (``selection._member``,
  ``sampling._band``) from the D116 complete-frame projections, so strata equal D116's;
* per-member availability comes from the contemporaneous Gamma snapshot (two-sided best quote),
  per-member trigger probabilities from the local CLOB book sweeps (|imbalance| >= 1/3 at the
  best level, the frozen ``SnapshotTriggerPolicy(1,3,...)`` rule).

Output: ``docs/implementation/d118/D118_DESIGN_ESTIMATES.json`` (original designs). ``--v2``
appends the 12-member rows (PL 4x3, 3x4, 2x6) after the original rows, so the seeded subset draws
of the original designs are unchanged, and writes ``D118_DESIGN_ESTIMATES_V2.json``.

Book sweeps are pinned (``PINNED_SWEEPS``, sha256-verified) to the eight sweeps the original file
used, so the original figures stay reproducible while the collector keeps adding sweeps. With
``--v2`` the candidate rows are also recomputed on every sweep present at run time and recorded as
a sensitivity block (never the primary figures).

    cd backend && python scripts/d118_design_estimates.py [--v2] [--out PATH] [--subsets 2000]
"""

import argparse
import hashlib
import itertools
import json
import math
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

import numpy as np

from astrolabe.research_panel.panel_declaration import (
    LIQUIDITY_FLOOR,
    PanelProtocol,
    reservation,
)
from astrolabe.research_panel.sampling import SamplingProtocol, _band
from astrolabe.research_panel.screening_worker import allocation
from astrolabe.research_panel.selection import _member

REPO = Path(__file__).resolve().parents[2]

DD = REPO / "data-dumps"
SELECTION = DD / "fs2_selection_panel_d116_integrated_1"
SNAPSHOT = DD / "research_lab" / "snapshots" / "20261011T002442Z_2173f20d"
SWEEPS = DD / "research_lab" / "book_sweeps"
D116_EVALUATION = DD / "fs2_d116_integrated_1_evaluation.json"
D097_EVIDENCE = REPO / "docs" / "implementation" / "PHASE_03_TEMPORAL_PILOT_EVIDENCE.json"
OUT = REPO / "docs" / "implementation" / "d118" / "D118_DESIGN_ESTIMATES.json"
OUT_V2 = REPO / "docs" / "implementation" / "d118" / "D118_DESIGN_ESTIMATES_V2.json"
PINNED_SWEEPS = (  # the sweep inventory of D118_DESIGN_ESTIMATES.json (script aec8418e)
    ("20261010T194225Z_94956338",
     "7867d18c044fa41beced573b3f2e788c3c6cf07b76d1c5910e0ba720824def17"),
    ("20261010T194347Z_d61a9354",
     "96f9f23786545d92a0965c2e4200992d5a00330f0e9b7fc935984f4fa69c713b"),
    ("20261010T194506Z_f1051015",
     "7ee4d96bee5df8e223cb894eff70c3165932df1e6e8af089017909ae23fc422f"),
    ("20261010T210152Z_e46bbf90",
     "151eda02dcaded8eb23ba9c89d92749247101d80ad00fe17f872240b3482246a"),
    ("20261010T210348Z_afeb30f2",
     "4de5442ed4fc5821666244a6f6ffa28edc900114c80e151cdc4d66c697f3ec06"),
    ("20261010T210603Z_0f474a80",
     "00ab8c6cbed2335862e7c90e8150a7f245db48aa883b0306ddeae603c7059778"),
    ("20261011T022944Z_eba4a73e",
     "d9f4cfc78f4f9f33fdc85fe3385c9cdaf45ac75f6cd80ba81859ba2eed334e84"),
    ("20261011T023104Z_4de8c806",
     "61eeb6384a544a51c2b11eea6e39cb2f4e148a7a9a8bef482e7898af711c1bad"),
)
SEED = 20261011
CHAIN = 0.95  # per-member probability that an assessable member completes origin/history/target
POPULATIONS = {
    "P0": "D116 temporal population: scheduled end after the selection declaration or unknown",
    "PL": "D118: P0 intersected with frame Gamma liquidity >= 1000 (liquidity missing, invalid "
          "or below 1000 excluded with zero inclusion)",
}
DESIGNS = [("P0", 4, 2), ("P0", 4, 4), ("PL", 2, 4), ("PL", 4, 2), ("PL", 4, 4), ("PL", 6, 4)]
RECOMMENDED = ("PL", 4, 4)
# V2: 12-member candidates after the 16-member dry-run abort (appended; original draws unchanged).
# 2x6 is included because the PanelProtocol / strata_limit bounds (1..256, k*m <= slots) allow it.
DESIGNS_V2 = [("PL", 4, 3), ("PL", 3, 4), ("PL", 2, 6)]
SCENARIOS = {
    "S1": "availability = member two-sided in the Gamma snapshot; trigger probability = pooled "
          "sweep rate over all two-sided sweep books (one rate for every member)",
    "S4": "availability as S1; trigger probability member-specific: Jeffreys posterior mean "
          "(k+0.5)/(n+1) over the member's own two-sided sweep books, else the pooled sweep rate "
          "of its liquidity band",
    "S4h": "S4 with every member's untriggered probability halved: p' = 1-(1-p)/2 (stress)",
    "S4q": "S4 with every member's untriggered probability quartered: p' = 1-(1-p)/4 (harshest "
           "defined stress; motivated by both pilots: 10 of 10 assessable members triggered)",
}
UNTRIGGERED_SCALE = {"S1": 1.0, "S4": 1.0, "S4h": 0.5, "S4q": 0.25}


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


def load_members():
    """D116 sampling members, rebuilt page by page with the production selection code."""
    policy = json.loads((SELECTION / "selection_policy.json").read_bytes())
    inventory = json.loads((SELECTION / "inventory.json").read_bytes())
    plan = json.loads((SELECTION / "selection_plan.json").read_bytes())
    edges = SamplingProtocol("a" * 64, 1, 1, 1, 1)
    members = []
    for entry in inventory["pages"]:
        folder = SELECTION / "pages" / entry["capture_id"]
        data = (folder / "projection.json").read_bytes()
        if hashlib.sha256(data).hexdigest() != entry["projection_hash"]:
            raise ValueError("D116 selection projection differs from its inventory")
        ack = json.loads((folder / "projection_ack.json").read_bytes())
        for row in json.loads(data)["rows"]:
            member = _member(row, ack["durable_ack"], policy["declared_at"])
            if member is None:
                continue
            members.append((
                member.market_id, member.token_id, member.close_stratum,
                _band(member.probability, edges.probability_edges),
                _band(member.liquidity, edges.liquidity_edges), member.liquidity,
                member.category, member.time_stratum,
            ))
    fidelity = {
        "sampling_members": len(members),
        "d116_plan_frame_size": plan["frame_size"],
        "temporal_eligible": sum(m[2] != "past" for m in members),
        "d116_plan_selection_eligible_member_count": plan["selection_eligible_member_count"],
        "temporal_strata": len({m[2:5] + m[6:8] for m in members if m[2] != "past"}),
        "d116_plan_eligible_strata": plan["stratum_draw"]["eligible_strata"],
    }
    fidelity["reproduces_d116"] = (
        fidelity["sampling_members"] == fidelity["d116_plan_frame_size"]
        and fidelity["temporal_eligible"]
        == fidelity["d116_plan_selection_eligible_member_count"]
        and fidelity["temporal_strata"] == fidelity["d116_plan_eligible_strata"]
    )
    return members, fidelity, policy["declared_at"]


def load_snapshot():
    import pandas as pd

    frame = pd.read_csv(SNAPSHOT / "rows.csv.gz", usecols=["market_id", "best_bid", "best_ask"],
                        dtype={"market_id": str})
    bid, ask = frame["best_bid"], frame["best_ask"]
    two = (bid.notna() & ask.notna() & (bid > 0) & (ask < 1) & (bid < ask)).to_numpy()
    return dict(zip(frame["market_id"].to_numpy(), two, strict=True))


def triggered(bid_size, ask_size):
    b, a = decimal(bid_size), decimal(ask_size)
    if b is None or a is None or b <= 0 or a <= 0:
        return None
    return 3 * abs(b - a) >= b + a  # |b-a|/(b+a) >= 1/3, exact decimal arithmetic


def pinned_sweep_files():
    files = []
    for name, digest in PINNED_SWEEPS:
        path = SWEEPS / name / "rows.csv.gz"
        if sha(path) != digest:
            raise ValueError(f"pinned book sweep differs from its recorded sha256: {name}")
        files.append(path)
    return files


def load_sweeps(files=None):
    import pandas as pd

    per_token = defaultdict(lambda: [0, 0])
    files = pinned_sweep_files() if files is None else files
    books = trig = 0
    for path in files:
        for chunk in pd.read_csv(path, usecols=["token_id", "state", "bid_size_1", "ask_size_1"],
                                 dtype=str, chunksize=50000):
            columns = chunk[["token_id", "state", "bid_size_1", "ask_size_1"]]
            for token, state, b, a in columns.itertuples(index=False):
                if state != "two_sided":
                    continue
                verdict = triggered(b, a)
                if verdict is None:
                    continue
                record = per_token[token]
                record[0] += 1
                record[1] += verdict
                books += 1
                trig += verdict
    return dict(per_token), books, trig, files


def model(members, snapshot, sweeps, pooled):
    """Per-member availability a_i and trigger probability p_i under S4 (and pooled for S1)."""
    band_counts = defaultdict(lambda: [0, 0])
    for m in members:
        record = sweeps.get(m[1])
        if record:
            band_counts[m[4]][0] += record[0]
            band_counts[m[4]][1] += record[1]
    band_rate = {band: (k + 0.5) / (n + 1) for band, (n, k) in band_counts.items()}
    avail_band = defaultdict(lambda: [0, 0])
    for m in members:
        if m[0] in snapshot:
            avail_band[m[4]][0] += 1
            avail_band[m[4]][1] += bool(snapshot[m[0]])
    avail_rate = {band: k / n for band, (n, k) in avail_band.items() if n}
    out = {}
    coverage = Counter()
    for m in members:
        if m[0] in snapshot:
            a = float(bool(snapshot[m[0]]))
            coverage["availability_from_snapshot"] += 1
        else:
            a = avail_rate.get(m[4], 0.0)
            coverage["availability_from_band_rate"] += 1
        record = sweeps.get(m[1])
        if record and record[0]:
            p = (record[1] + 0.5) / (record[0] + 1)
            coverage["trigger_from_own_sweeps"] += 1
        else:
            p = band_rate.get(m[4], pooled)
            coverage["trigger_from_band_rate"] += 1
        out[m[0]] = (a, p)
    return out, dict(coverage), {k: round(v, 4) for k, v in sorted(band_rate.items())}, {
        k: round(v, 4) for k, v in sorted(avail_rate.items())}


def no_pair_given(av, pr, c2):
    """Rows of r members -> (P(no complete pair), E[pairs drawn]); exact over 3^r states."""
    r = av.shape[1]
    # 0 unavailable, 1 triggered, 2 untriggered
    states = np.array(list(itertools.product((0, 1, 2), repeat=r)))
    prob = np.ones((av.shape[0], len(states)))
    for j in range(r):
        s = states[:, j]
        col = np.where(s == 0, 1 - av[:, [j]],
                       np.where(s == 1, av[:, [j]] * pr[:, [j]], av[:, [j]] * (1 - pr[:, [j]])))
        prob *= col
    t, u = (states == 1).sum(1), (states == 2).sum(1)
    pairs = np.minimum(t, u)  # triggered_per_stratum = m >= r; one control per trigger
    return prob @ ((1 - c2) ** pairs), prob @ pairs


def subset_index(n, m, rng, subsets):
    """Within-stratum draws of min(m, n) members: exact enumeration or seeded random subsets."""
    r = min(m, n)
    if r < 2:
        return None
    if math.comb(n, r) <= subsets:
        return np.array(list(itertools.combinations(range(n), r)))
    return np.array([rng.choice(n, r, replace=False) for _ in range(subsets)])


def stratum_terms(values, index, c2):
    if index is None:
        return 1.0, 0.0
    q, e = no_pair_given(values[index, 0], values[index, 1], c2)
    return float(q.mean()), float(e.mean())


def elementary(qs, k):
    e = [1.0] + [0.0] * k
    for q in qs:
        for j in range(k, 0, -1):
            e[j] += e[j - 1] * q
    return e[k]


def design_probability(strata, indices, k, scenario, c, pooled):
    scale = UNTRIGGERED_SCALE[scenario]
    qs, es, qd = [], [], []
    for values, index in zip(strata, indices, strict=True):
        v = values.copy()
        if scenario == "S1":
            v[:, 1] = pooled  # one pooled trigger rate for every member
        v[:, 1] = 1 - (1 - v[:, 1]) * scale
        q, e = stratum_terms(v, index, c * c)
        qd_value, _ = stratum_terms(v, index, 1.0)
        qs.append(q)
        es.append(e)
        qd.append(qd_value)
    n = len(strata)
    k = min(k, n)
    total = math.comb(n, k)
    return {
        "P_complete_pair": 1 - elementary(qs, k) / total,
        "P_pair_drawn": 1 - elementary(qd, k) / total,
        "E_pairs_drawn": k / n * sum(es),
        "E_complete_pairs": k / n * sum(es) * c * c,
        "eligible_strata": n,
    }


def required_free(k, m):
    p = PanelProtocol(
        scheduled_slots=k * m, triggered_slots=k * m, controls_per_trigger=1, cycles=1,
        target_attempts=1, scheduled_per_stratum=m, triggered_per_stratum=m,
        cadence_seconds=120, max_origin_delay_seconds=60, max_origin_save_seconds=5,
        horizon_seconds=60, tolerance_seconds=15, max_frame_age_seconds=3600,
        max_frame_interval_seconds=600, max_quote_age_seconds=60, max_identity_age_seconds=180,
        source_response_bytes=65536, source_run_retained_bytes=1048576)
    reserved = allocation({"reservation": reservation(p, storage_profile="compact-v1")},
                          windows=True)
    return 7 * 1024**3 + reserved["required_free_bytes"] + 34 * 1048576


def pilots(model_d116, snapshot, sweeps, pooled):
    """The ten assessable pilot members (D097: 6, D116: 4) were all triggered."""
    d116 = json.loads(D116_EVALUATION.read_bytes())
    rows = [(m["market_id"], m["token_id"], m["effective_assessment_state"], "D116")
            for m in d116["members"].values()]
    d097 = json.loads(D097_EVIDENCE.read_bytes())
    tokens = {a["market_id"]: a["token_id"] for a in d097["first_stage_assignments"]}
    rows += [(s["market_id"], tokens.get(s["market_id"]), s["state"], "D097")
             for s in d097["screening_states"]]
    members = []
    for market, token, state, run in rows:
        record = sweeps.get(token)
        if market in model_d116:
            a, p = model_d116[market]
            basis = "model"
        else:
            p = ((record[1] + 0.5) / (record[0] + 1)) if record and record[0] else pooled
            a = float(bool(snapshot.get(market, False)))
            basis = "own sweeps" if record and record[0] else "pooled"
        members.append({"run": run, "market_id": market, "observed_state": state,
                        "predicted_available": a, "p_trigger_S4": round(p, 4),
                        "basis": basis})
    assessable = [x for x in members if x["observed_state"] in ("triggered", "untriggered")]
    likelihood = {}
    for scenario, scale in UNTRIGGERED_SCALE.items():
        value = 1.0
        for x in assessable:
            p = pooled if scenario == "S1" else x["p_trigger_S4"]
            p = 1 - (1 - p) * scale
            value *= p if x["observed_state"] == "triggered" else 1 - p
        likelihood[scenario] = value
    return members, likelihood


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--subsets", type=int, default=2000)
    parser.add_argument("--v2", action="store_true",
                        help="append the 12-member designs and write the V2 file")
    args = parser.parse_args(argv)
    designs = DESIGNS + DESIGNS_V2 if args.v2 else DESIGNS
    out = args.out or (OUT_V2 if args.v2 else OUT)
    members, fidelity, reference = load_members()
    snapshot = load_snapshot()
    output = estimate(args, designs, members, fidelity, reference, snapshot, None)
    if args.v2:
        current = sorted(SWEEPS.glob("*/rows.csv.gz"))
        sensitivity = estimate(args, designs, members, fidelity, reference, snapshot, current)
        output["status"] = ("design figures only; not acceptance criteria; D118 pre-freeze V2 "
                            "(12-member candidates after the 16-member dry-run abort)")
        output["original_designs_note"] = (
            "rows of the original designs are drawn first with the same seed on the same pinned "
            "sweeps, so they equal D118_DESIGN_ESTIMATES.json; recommended_design is the original "
            "4x4 field and is superseded by twelve_member_candidates (choice follows the V2 dry "
            "run)")
        output["twelve_member_candidates"] = candidates(output["table"])
        output["sensitivity_all_sweeps_at_run_time"] = {
            "note": "not the primary figures: same model on every sweep present at run time",
            "book_sweeps": sensitivity["inputs"]["book_sweeps"],
            "pooled_sweep_trigger_rate": sensitivity["model_inputs"]["pooled_sweep_trigger_rate"],
            "likelihood_ratio_vs_S1": sensitivity["pilots"]["likelihood_ratio_vs_S1"],
            "candidates": candidates(sensitivity["table"], with_original=True),
        }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"fidelity": fidelity, "recommended": output["recommended_design"],
                      "candidates": output.get("twelve_member_candidates")}, indent=1))


def candidates(table, with_original=False):
    chosen = DESIGNS_V2 + ([RECOMMENDED] if with_original else [])
    result = {}
    for pop, k, m in chosen:
        rows = [r for r in table if r["population"] == pop and r["design"] == f"{k}x{m}"]
        result[f"{k}x{m}"] = {
            "population": pop, "strata_limit": k, "per_stratum": m,
            "P_complete_pair_by_scenario": {r["scenario"]: r["P_complete_pair"] for r in rows},
            "E_complete_pairs_by_scenario": {r["scenario"]: r["E_complete_pairs"] for r in rows},
            "required_free_bytes": required_free(k, m),
        }
    return result


def estimate(args, designs, members, fidelity, reference, snapshot, sweep_paths):
    rng = np.random.default_rng(SEED)
    sweeps, books, trig, sweep_files = load_sweeps(sweep_paths)
    pooled = trig / books
    per_member, coverage, band_rate, avail_rate = model(members, snapshot, sweeps, pooled)
    floor = Decimal(LIQUIDITY_FLOOR)
    populations = {"P0": [], "PL": []}
    excluded = Counter()
    for m in members:
        if m[2] == "past":
            excluded["temporal"] += 1
            continue
        populations["P0"].append(m)
        liquidity = decimal(m[5]) if m[5] is not None else None
        if liquidity is None:
            excluded["liquidity_missing_or_invalid"] += 1
        elif liquidity < floor:
            excluded["liquidity_below_1000"] += 1
        else:
            populations["PL"].append(m)
    strata, summaries = {}, {}
    for name, rows in populations.items():
        groups = defaultdict(list)
        for m in rows:
            groups[m[2:5] + m[6:8]].append(per_member[m[0]])
        strata[name] = [np.array(v, dtype=float) for _, v in sorted(groups.items())]
        sizes = sorted(len(v) for v in groups.values())
        values = np.array([per_member[m[0]] for m in rows])
        summaries[name] = {
            "members": len(rows), "strata": len(groups),
            "strata_with_at_least_2": sum(s >= 2 for s in sizes),
            "strata_with_at_least_4": sum(s >= 4 for s in sizes),
            "mean_availability": round(float(values[:, 0].mean()), 4),
            "mean_trigger_probability_S4_available": round(
                float(values[values[:, 0] > 0, 1].mean()), 4),
            "mean_stratum_availability_uniform_over_strata": round(float(np.mean(
                [v[:, 0].mean() for v in strata[name]])), 4),
        }
    indices = {}
    for pop, _, m in designs:
        if (pop, m) not in indices:
            indices[pop, m] = [subset_index(len(v), m, rng, args.subsets) for v in strata[pop]]
    table = []
    for (pop, k, m), scenario in itertools.product(designs, SCENARIOS):
        result = design_probability(strata[pop], indices[pop, m], k, scenario, CHAIN,
                                    pooled)
        table.append({"population": pop, "design": f"{k}x{m}", "strata_limit": k,
                      "per_stratum": m, "scheduled_slots": k * m, "scenario": scenario,
                      **{key: round(v, 4) if isinstance(v, float) else v
                         for key, v in result.items()},
                      "required_free_bytes": required_free(k, m)})
    pilot_members, likelihood = pilots(per_member, snapshot, sweeps, pooled)
    recommended = [r for r in table if (r["population"], r["strata_limit"], r["per_stratum"])
                   == RECOMMENDED]
    values = {r["scenario"]: r["P_complete_pair"] for r in recommended}
    output = {
        "status": "design figures only; not acceptance criteria; D118 pre-freeze",
        "generated_by": "backend/scripts/d118_design_estimates.py",
        "script_sha256": sha(Path(__file__)),
        "seed": SEED, "subsets_per_stratum": args.subsets, "chain_completion_c": CHAIN,
        "inputs": {
            "d116_selection_inventory_ack": json.loads(
                (SELECTION / "inventory_ack.json").read_bytes())["payload_hash"],
            "d116_selection_plan_sha256": sha(SELECTION / "selection_plan.json"),
            "d116_selection_policy_sha256": sha(SELECTION / "selection_policy.json"),
            "d116_selection_pages_verified": "every projection.json sha256 equals inventory",
            "snapshot": {"path": str(SNAPSHOT.relative_to(REPO)),
                         "rows_sha256": sha(SNAPSHOT / "rows.csv.gz"),
                         "manifest_sha256": sha(SNAPSHOT / "manifest.json")},
            "book_sweeps": [{"path": str(p.relative_to(REPO)), "sha256": sha(p)}
                            for p in sweep_files],
            "d116_evaluation_sha256": sha(D116_EVALUATION),
            "d097_evidence_sha256": sha(D097_EVIDENCE),
            "population_reference_at": reference,
        },
        "definitions": {
            "populations": POPULATIONS,
            "scenarios": SCENARIOS,
            "availability": "Gamma snapshot best_bid/best_ask both present with 0 < bid < ask < 1 "
                            "(proxy for a two-sided CLOB book at screening)",
            "trigger": "|bid_size_1 - ask_size_1| / (bid_size_1 + ask_size_1) >= 1/3 on a "
                       "two-sided sweep book (exact decimal comparison)",
            "pair": "within one drawn stratum, triggered T and untriggered U screened members "
                    "give min(T, U) drawn pairs (triggered_per_stratum = per-stratum count, one "
                    "control per trigger, controls only from the same stratum)",
            "complete_pair": "both pair members complete origin, history and target; each "
                             "independently with probability c",
            "strata_draw": "uniform without replacement over all eligible strata (exact "
                           "elementary-symmetric expectation); within-stratum subsets enumerated "
                           "exactly when C(n, r) <= subsets, else that many seeded random "
                           "subsets",
            "independence": "members treated as independent; neg-risk/same-event dependence "
                            "is not modelled",
            "required_free_bytes": "7 GiB frame cap + panel/window/runtime reservation incl. "
                                   "2 GiB reserve + 34 MiB, as the frozen script computes",
        },
        "fidelity": fidelity,
        "population_exclusions_from_P0_frame": dict(excluded),
        "population_summaries": summaries,
        "model_inputs": {"pooled_sweep_trigger_rate": round(pooled, 4),
                         "sweep_two_sided_books": books, "coverage": coverage,
                         "trigger_rate_by_liquidity_band": band_rate,
                         "availability_by_liquidity_band": avail_rate},
        "pilots": {"members": pilot_members, "likelihood_of_observed_states": likelihood,
                   "likelihood_ratio_vs_S1": {k: (v / likelihood["S1"]) if likelihood["S1"]
                                              else None for k, v in likelihood.items()}},
        "table": table,
        "recommended_design": {
            "population": RECOMMENDED[0], "design": f"{RECOMMENDED[1]}x{RECOMMENDED[2]}",
            "P_complete_pair_by_scenario": values,
            "range": [min(values.values()), max(values.values())],
            "harshest_scenario": min(values, key=values.get),
        },
    }
    return output


if __name__ == "__main__":
    main()
