"""Versioned lossless local codec and corruption checks, not archive/deletion authority.

No filesystem or database side effects. A complete object backend, independent restore
report and scientific equivalence gate remain required by V2_MIGRATION_AND_ARCHIVE.md.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime
from decimal import Decimal

from .admission import AdmissionError, content_hash, prepare
from .schema import FIELD_SPECS
from .types import canonical_json

CODEC = "arepo-fs2-jsonl-v1"


def encode_records(records):
    lines = []
    identities = set()
    counts = Counter()
    for entity, row in records:
        validated = prepare(entity, row)
        identity = (entity, validated["id"])
        if identity in identities:
            raise AdmissionError("duplicate record in preservation inventory")
        identities.add(identity)
        counts[entity] += 1
        lines.append(canonical_json({"entity": entity, "row": validated}))
    data = ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")
    manifest = {
        "codec": CODEC,
        "sha256": hashlib.sha256(data).hexdigest(),
        "byte_count": len(data),
        "row_count": len(lines),
        "entity_counts": dict(counts),
        "field_contract_hash": content_hash(FIELD_SPECS),
        "ordered_keys_hash": content_hash([json.loads(line)["row"]["id"] for line in lines]),
        "verification_state": "local_codec_only",
    }
    return data, manifest


def decode_records(data: bytes, manifest: dict):
    if (
        manifest.get("codec") != CODEC
        or manifest.get("field_contract_hash") != content_hash(FIELD_SPECS)
        or manifest.get("sha256") != hashlib.sha256(data).hexdigest()
        or manifest.get("byte_count") != len(data)
    ):
        raise AdmissionError("preservation bytes or schema failed integrity check")
    records = []
    for line in data.decode("utf-8").splitlines():
        item = json.loads(line)
        if not isinstance(item, dict) or set(item) != {"entity", "row"}:
            raise AdmissionError("invalid preservation envelope")
        entity, row = item["entity"], item["row"]
        if entity not in FIELD_SPECS or not isinstance(row, dict):
            raise AdmissionError("invalid preserved entity")
        for name, spec in FIELD_SPECS[entity].items():
            value = row.get(name)
            if value is None:
                continue
            if spec["type"] == "DECIMAL_TEXT":
                if not isinstance(value, dict) or set(value) != {"$decimal"}:
                    raise AdmissionError("preserved decimal tag missing")
                row[name] = Decimal(value["$decimal"])
            elif spec["type"] == "UTC":
                if not isinstance(value, dict) or set(value) != {"$utc"}:
                    raise AdmissionError("preserved UTC tag missing")
                row[name] = datetime.fromisoformat(value["$utc"].replace("Z", "+00:00"))
        records.append((entity, prepare(entity, row)))
    # Canonical bytes, exact inventory and numerical types all have to agree.
    roundtrip, verified = encode_records(records)
    if roundtrip != data or verified != manifest:
        raise AdmissionError("preservation inventory or canonical numerical representation differs")
    return records
