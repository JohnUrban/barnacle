#!/usr/bin/env python3
"""Validate the offline episode registry and source associations, read-only.

Does not alter production event grouping, fit goldens, or the observation ledger.
New ledger rows beyond the indexed cutoff are reported, not silently assigned.
"""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "assets/observations/episodes.json"


def row_hash(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":")).encode()).hexdigest()


def validate(registry=None):
    d = registry if registry is not None else json.loads(REGISTRY.read_text())
    assert d["schema_version"] == 1
    with (ROOT / d["ledger_file"]).open(newline="") as f:
        rows = list(csv.DictReader(f))
    ids, aliases, assigned = set(), set(), {}
    for e in d["episodes"]:
        eid = e["episode_id"]
        assert eid == f"{e['date']}-e{e['ordinal']:02d}", eid
        assert eid not in ids, f"duplicate episode ID {eid}"
        ids.add(eid)
        assert (ROOT / e["directory"] / "README.md").is_file(), eid
        for alias in e["aliases"]:
            assert alias not in aliases, f"ambiguous alias {alias}"
            aliases.add(alias)
        for path in e["source_paths"]:
            assert (ROOT / path).is_file(), path
        for ref in e["ledger_rows"]:
            n = ref["csv_row"]
            assert n not in assigned, f"row {n} assigned more than once"
            assert row_hash(rows[n-2]) == ref["sha256"], f"row identity changed: {n}"
            assert rows[n-2]["landmark_key"] != "none", f"metadata assigned to {eid}"
            assigned[n] = eid
    for ref in d["excluded_ledger_rows"]:
        n = ref["csv_row"]
        assert n not in assigned, f"excluded row {n} also assigned"
        assert row_hash(rows[n-2]) == ref["sha256"], f"excluded row changed: {n}"
        assert rows[n-2]["landmark_key"] == "none", f"real observation excluded: {n}"
        assigned[n] = "metadata"
    end = d["indexed_through_csv_row"]
    assert set(assigned) == set(range(2, end+1)), "registry coverage gap"
    assert end <= len(rows)+1
    return {"episodes": len(ids), "indexed_rows":end-1,
            "new_rows_needing_review":len(rows)+1-end,
            "note":"Registered episodes include negative checks and reconstructions; this is not a flood count."}


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2))
