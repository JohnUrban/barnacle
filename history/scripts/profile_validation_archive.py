"""Read-only readiness census for the items 2/5 validation handoff.

Run from the repository root. This profiles inputs, not forecast skill.
"""
import collections
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from forecast.replay_archive import expand, validate_file
from forecast.wind_shadow import check_bundle, validate_file as validate_wind


def stamp(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def main():
    files, records = [], []
    for path in sorted((ROOT / "data/replay_inputs").glob("*.jsonl")):
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        files.append({"path": str(path.relative_to(ROOT)), "rows": len(rows),
                      "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                      "validator_problems": validate_file(path)})
        for line, row in enumerate(rows, 1):
            blocks, problems = {}, []
            for name, block in (("qpf", row.get("qpf_hourly")),
                                ("outlook", row.get("outlook_hourly")),
                                ("nwps", (row.get("nwps") or {}).get("hourly"))):
                if block is None:
                    blocks[name] = None
                    continue
                lengths = {k: len(v) for k, v in block.items() if isinstance(v, list)}
                if len(set(lengths.values())) > 1:
                    problems.append(f"{name}: unequal array lengths {lengths}")
                    continue
                points = expand(block)
                times = [p[0] for p in points]
                if times != sorted(set(times)):
                    problems.append(f"{name}: duplicate or unordered target times")
                blocks[name] = {"count": len(points),
                                "first": times[0].isoformat() if times else None,
                                "last": times[-1].isoformat() if times else None}
            corrections = row.get("advisory_corrections") or []
            records.append({"path": str(path.relative_to(ROOT)), "line": line,
                            "generated_utc": row["generated_utc"],
                            "model_version": row["model_version"],
                            "nonzero_correction_anchors": sum(p["ft"] != 0 for p in corrections),
                            "correction_anchors": len(corrections),
                            "nwps_issued": (row.get("nwps") or {}).get("issued"),
                            "unavailable": row["unavailable"], "blocks": blocks,
                            "tank_init": row["tank_init"], "shape_problems": problems})
    times = [r["generated_utc"] for r in records]
    wind = []
    for path in sorted((ROOT / "data/wind_shadow").glob("*.jsonl")):
        for line, raw in enumerate(path.read_text().splitlines(), 1):
            r = json.loads(raw)
            wind.append({"path": str(path.relative_to(ROOT)), "line": line,
                         **{k: r.get(k) for k in ("candidate_id", "collection", "status",
                            "issuance_utc", "written_utc", "nominal_issuance_hour_utc",
                            "bundle_sha256", "manifest_sha256", "runtime_sha256", "github_run_id")},
                         "validator_problems": validate_wind(path)})
    result = {"scope": "Input readiness only; no outcomes scored",
              "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "files": files, "record_count": len(records),
              "first_issuance": min(times) if times else None,
              "last_issuance": max(times) if times else None,
              "span_hours": (stamp(max(times)) - stamp(min(times))).total_seconds() / 3600 if times else None,
              "duplicate_issuances": len(times) - len(set(times)),
              "versions": dict(collections.Counter(r["model_version"] for r in records)),
              "records_with_nonzero_correction": sum(r["nonzero_correction_anchors"] > 0 for r in records),
              "records": records, "wind_records": wind, "wind_bundle": check_bundle()}
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
