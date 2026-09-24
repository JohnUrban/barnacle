"""Independent round-07 null/missing decay-timescale probe. Research-root argument; stdout JSON."""
import sys, importlib.util, json
from pathlib import Path
root = Path(sys.argv[1]).resolve()
sys.path[:0] = [str(root), str(root / "history/scripts")]
spec = importlib.util.spec_from_file_location("T", root / "tests/test_as_issued_validation.py")
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)
from as_issued import street as S, report as R, fidelity as F
out = {}
for case in ["tau_null", "tau_missing", "tau_zero", "tau_negative", "baseline"]:
    f, r, a = T._v106()
    dec = f["water_series_input"]["decay"]
    if case == "tau_null": dec["tau_h"] = None
    if case == "tau_missing": del dec["tau_h"]
    if case == "tau_zero": dec["tau_h"] = 0
    if case == "tau_negative": dec["tau_h"] = -1
    row = {"rule_problems": F.rule_problems(f)}
    try:
        rep, ps = S.evaluate(T.FakeCtx({"b": f}, r, a),
                            [T._entry("2026-09-24T08:00", "curb", "POINT", point=4.24)])
        json.dumps({"report": rep, "pairs": ps, "events": R.per_event(ps, {})},
                   allow_nan=False, default=str)
        b0 = rep["B0_published_by_version"]["v0.10.6"]["(0,6]"]
        row.update(classes=rep["class_counts"], strict_json="passed",
                   B0_point_pairs=b0["point_pairs"], B0_unscorable=b0["unscorable"])
    except Exception as e:
        row["error"] = f"{type(e).__name__}: {e}"
    try: row["f1"] = F.f1_astronomy(f, a)
    except Exception as e: row["f1_error"] = f"{type(e).__name__}: {e}"
    out[case] = row
print(json.dumps(out, indent=2, allow_nan=False))
