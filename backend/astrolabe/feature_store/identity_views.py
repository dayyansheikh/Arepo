"""Conservative as-of version selection and dependence views over validated records."""

from __future__ import annotations

from .admission import content_hash
from .types import utc_datetime


def select_as_known(rows, *, subject_fields, cutoff, effective_at=None):
    """No future supersession/metadata leakage, and no resurrection after a correction.

    Versions are complete subject snapshots. Select latest known version, then test
    its [valid_from, valid_to) interval. Unknown interval bounds are not evidence of
    historic applicability: effective_at requests exclude them. Omitting effective_at
    asks only what was known, not when the source asserts it applied in the world.
    """
    cutoff = utc_datetime(cutoff)
    if effective_at is not None:
        effective_at = utc_datetime(effective_at)
    chosen = {}
    for row in rows:
        known = max(utc_datetime(row["observed_from_at"]), utc_datetime(row["recorded_at"]))
        if known > cutoff:
            continue
        subject = tuple(row[field] for field in subject_fields)
        old = chosen.get(subject)
        if old is not None and known == old[0] and row["id"] != old[1]["id"]:
            raise ValueError("conflicting versions at the same knowledge time")
        if old is None or known > old[0]:
            chosen[subject] = (known, row)
    result = []
    for _, row in chosen.values():
        if effective_at is not None:
            start, end = row.get("valid_from_at"), row.get("valid_to_at")
            if start is None or effective_at < utc_datetime(start):
                continue
            if end is not None and effective_at >= utc_datetime(end):
                continue
        result.append(row)
    return sorted(result, key=lambda row: row["id"])


def dependence_components(market_ids, memberships, *, view, cutoff):
    """Compute connected groups; unknown membership never implies independence.

    Evaluation-only later evidence is an explicit separate view. Output identifies
    unresolved markets and is not eligible as a model feature under that view.
    """
    if view not in {"as_known", "conservative_evaluation"}:
        raise ValueError("explicit group view required")
    markets = set(market_ids)
    if len(markets) != len(market_ids):
        raise ValueError("market inventory must be unique")
    rows = [r for r in memberships if r["mapping_view"] == view]
    rows = select_as_known(rows, subject_fields=("event_group_id", "member_identity_id"),
                           cutoff=cutoff)
    versions = {row["group_version"] for row in rows}
    if len(versions) > 1:
        raise ValueError("select one whole graph version; cannot mix split definitions")
    parent = {m: m for m in markets}

    def root(value):
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    groups = {}
    known = set()
    for row in rows:
        member, group = row["member_identity_id"], row["event_group_id"]
        if member not in markets:
            raise ValueError("group member absent from declared inventory")
        if group is None or not row["mapping_evidence_ids"]:
            continue
        groups.setdefault(group, []).append(member)
        known.add(member)
    for members in groups.values():
        first = root(members[0])
        for member in members[1:]:
            parent[root(member)] = first
    components = {}
    for member in sorted(markets):
        components.setdefault(root(member), []).append(member)
    result = {
        "view": view, "cutoff": cutoff, "components": sorted(components.values()),
        "unresolved_market_ids": sorted(markets - known),
        "model_feature_eligible": (view == "as_known" and not (markets - known)
                                   and bool(rows)
                                   and all(r.get("provenance_class") == "prospective"
                                           for r in rows)),
        "split_ready": not (markets - known),
        "group_version": next(iter(versions), None),
        "evidence_membership_ids": sorted(row["id"] for row in rows),
    }
    result["split_manifest_hash"] = content_hash(result)
    return result
