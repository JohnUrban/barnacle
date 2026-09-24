"""Round-06 receipts (audit 2026-09-24-a4): full-chain boundary cases and
positive controls (evaluate -> per_event -> strict JSON), fidelity entry points,
and r3-vs-r4 equality on the real archive with only the NEW fields removed
('unscorable' summaries and per-pair '*_why' reasons, plus run stamps).
Run: python3 history/scripts/as_issued/round06_receipts.py  (writes
history/reports/as_issued/round06-receipts.json, strict JSON)."""
import importlib.util
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from as_issued import archive as A, fidelity as F  # noqa: E402

ROOT = A.ROOT
spec = importlib.util.spec_from_file_location("T", os.path.join(ROOT, "tests", "test_as_issued_validation.py"))
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)


def run_case(case, dry=True):
    try:
        rep, pairs, events, text = T._full_chain(case, dry=dry)
    except Exception as e:  # noqa: BLE001 — a receipt must record, not hide, a failure
        return {"error": f"{type(e).__name__}: {e}"}
    b0 = rep["B0_published_by_version"]["v0.10.6"]["(0,6]"]
    return {"classes": rep["class_counts"], "reasons": sorted({p["class_note"] for p in pairs if p["class_note"]}),
            "B1_verdict": rep["verdicts"]["B1 decay vs persisted (EXACT only)"],
            "B0_point_pairs": b0["point_pairs"], "B0_mae_ft": b0.get("mae_ft"), "B0_cells": b0["threshold"],
            "B0_unscorable": b0["unscorable"], "strict_json": "passed"}


def fidelity_case(case):
    f, r, a = T._mutate(case)
    rp = r.get(f["generated_utc"])
    try:
        out = [F.f1_astronomy(f, a), F.f2_tank(f, "HEAD", rp, F._tank()), F.f3_parity(f, rp), F.f4_reading(f, a)]
        json.dumps(out, allow_nan=False, default=str)
        return {"statuses": [o.get("status") for o in out]}
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}


def strip(d):
    drop = {"evaluated_utc", "repo_head", "revision", "generated_utc", "unscorable"}
    if isinstance(d, dict):
        return {k: strip(v) for k, v in d.items() if k not in drop and not k.endswith("_why")}
    if isinstance(d, list):
        return [strip(x) for x in d]
    return d


def main():
    out = {"boundary_and_malformed": {c: run_case(c) for c in ("baseline",) + T.MALFORMED + ("time_bad",)},
           "positive_controls": {"EXACT": run_case("baseline"), "EXACT wet": run_case("exact_wet"),
                                 "NEAR": run_case("near_wet"), "published-only B0 (wet, rain not archived)":
                                 run_case("published_only", dry=False), "APPROX-TIDE": run_case("published_only")},
           "fidelity_entry_points": {c: fidelity_case(c) for c in T.MALFORMED + ("time_bad",)}}
    rep = os.path.join(ROOT, "history", "reports", "as_issued")
    eq = {}
    for a, b in (("study-a-advisory-r3.json", "study-a-advisory-r4.json"), ("study-b-street-r3.json", "study-b-street-r4.json"),
                 ("study-b-events-r3.json", "study-b-events-r4.json"), ("readiness-summary-r3.json", "readiness-summary-r4.json")):
        with open(os.path.join(rep, a)) as fa, open(os.path.join(rep, b)) as fb:
            eq[f"{a} == {b}"] = strip(json.load(fa)) == strip(json.load(fb))
    out["r3_vs_r4_without_new_fields"] = eq
    path = os.path.join(rep, "round06-receipts.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1, sort_keys=True, allow_nan=False)
        f.write("\n")
    print(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
