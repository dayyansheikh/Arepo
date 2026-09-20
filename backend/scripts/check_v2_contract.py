"""Read-only structural checks for the canonical v2 contract and supplied package.

No application imports, settings, database or network access. Run from any directory.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / "docs/research/2026-09-20"
ARCH = ROOT / "docs/architecture"
ENTITIES = {
    "source_registry", "market_identity_version", "condition_identity", "token_outcome_version",
    "event_group_membership", "source_observation", "book_snapshot", "book_level",
    "trade_observation", "wallet_state_version", "information_event_version", "research_origin",
    "feature_definition", "feature_value", "prediction", "outcome_observation", "label_version",
    "experiment_run", "archive_manifest", "artifact_manifest", "target_definition",
}
TYPES = {
    "TEXT", "HASH", "HEX32", "ADDRESS", "UINT_TEXT", "INT64", "UTC", "DECIMAL_TEXT", "ENUM",
    "JSON", "ID_LIST", "DECIMAL_VECTOR", "TYPED_VECTOR", "TYPED_OBJECT", "TYPED_NUMBER",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def main() -> None:
    manifest = json.loads((RESEARCH / "MANIFEST.json").read_text())
    require(len(manifest["files"]) == 13, "Expected all 13 supplied research artefacts")
    for item in manifest["files"]:
        data = (RESEARCH / item["file"]).read_bytes()
        require(len(data) == item["bytes"], f"Size changed: {item['file']}")
        require(hashlib.sha256(data).hexdigest() == item["sha256"],
                f"Research source hash changed: {item['file']}")
    fields = read_csv(ARCH / "FEATURE_STORE_V2_FIELDS.csv")
    keys = {f"{r['entity']}.{r['field']}" for r in fields}
    require(len(keys) == len(fields), "Duplicate canonical fields")
    require({r["entity"] for r in fields} == ENTITIES, "Missing or unaccounted entity")
    for row in fields:
        key = f"{row['entity']}.{row['field']}"
        require(row["type"] in TYPES, f"Undefined type: {key}")
        require(row["nullable"] in {"true", "false"}, f"Undefined nullability: {key}")
        require(bool(row["meaning"] and row["units"]), f"Missing meaning/units: {key}")
        require(row["storage"] in {"stored", "derived_as_of_view"}, f"Unknown storage: {key}")
        require(not row["reference"] or row["reference"] in keys, f"Dangling FK: {key}")
    for entity in ENTITIES:
        for common in ("id", "schema_version", "recorded_at", "provenance_class", "missing_fields"):
            require(f"{entity}.{common}" in keys, f"Missing {entity}.{common}")
    research_fields = read_csv(RESEARCH / "FEATURE_STORE_V2_DICTIONARY.csv")
    expected = {f"{r['entity']}.{r['field']}" for r in research_fields}
    mapping = read_csv(ARCH / "FEATURE_STORE_V2_RECONCILIATION.csv")
    require(len(expected) == len(mapping) == 140, "Expected 140 unique dictionary mappings")
    require({r["research_field"] for r in mapping} == expected, "Research mapping incomplete")
    for row in mapping:
        require(row["canonical_field"] in keys, f"Unresolved mapping: {row['research_field']}")
        require(bool(row["resolution"] and row["note"]), "Missing reconciliation explanation")
    features = read_csv(RESEARCH / "FEATURE_RESEARCH_REGISTER.csv")
    experiments = read_csv(RESEARCH / "EDGE_EXPERIMENTS.csv")
    feature_ids = {r["feature_id"] for r in features}
    require(feature_ids == {f"F{i:02d}" for i in range(1, 61)}, "Feature IDs incomplete")
    require({r["experiment_id"] for r in experiments} == {f"H{i:02d}" for i in range(1, 61)},
            "Experiment IDs incomplete")
    cards = (RESEARCH / "EDGE_HYPOTHESIS_LIBRARY.md").read_text()
    for row in experiments:
        require(row["feature_id"] in feature_ids, "Unknown experiment feature")
        require(row["status"] == "Designed; not executed; no edge established", "Evidence drift")
        for key, value in row.items():
            require(bool(value), f"Empty experiment clause: {row['experiment_id']}.{key}")
            if key != "source_urls":
                require(value in cards, f"CSV/card disagreement: {row['experiment_id']}.{key}")
    phases = sorted((ROOT / "docs/implementation/phases").glob("PHASE_*.md"))
    require(len(phases) == 11, "Expected 11 phase plans")
    headings = [
        "Objective", "Why this phase exists", "Research basis", "Dependencies",
        "Current repository state", "In scope", "Out of scope", "Ordered implementation tasks",
        "Likely modules/files", "Data model, API and migration implications", "Tests required",
        "Acceptance criteria", "Exit checklist", "Protected boundaries", "Handoff/output",
    ]
    for phase in phases:
        body = phase.read_text()
        for heading in headings:
            require(f"## {heading}\n" in body, f"Missing {heading}: {phase.name}")
    print(f"PASS: 13 hashes; {len(fields)} fields / 21 entities; 140 mappings; "
          "60 feature/experiment cards; 11 phase contracts. No database accessed.")


if __name__ == "__main__":
    main()
