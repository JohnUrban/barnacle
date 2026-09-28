"""Offline independent round17 verification; takes an isolated candidate path.

Reruns round16's source-row cases, accepting the repaired NaN rejection,
then probes remaining timing, disputed-cap and unavailable-file paths.
Only temporary files and mocked input calls are used; never sends alerts.
"""
import contextlib
import copy
import io
import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

root = Path(sys.argv[1]).resolve()
old = Path(__file__).with_name("16-review-probes.py").read_text()
old = old[:old.index("    writer.append_bound(238, float(\"nan\")")]
old += '''    before = path.read_bytes() if path.exists() else None
    try:
        writer.append_bound(238, float("nan"), 4.16, "stated_landmarks", rec["landmarks"],
                            "synthetic invalid bound", "Codex probe", str(ledger), str(path))
        out["writer_nan"] = {"rejected": False}
    except ValueError:
        after = path.read_bytes() if path.exists() else None
        out["writer_nan"] = {"rejected": True, "bytes_unchanged": before == after}
'''
ns = {"__name__": "round16_recheck"}
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(old, "16-review-probes.py", "exec"), ns)
r = ns["out"]
r["candidate"] = "f14837961"
ff, ob = ns["ff"], None
from forecast import observation_bounds as ob, rendering

r["remaining_time_cases"] = {
    s: ff._lookback_time_uncertain(s)
    for s in ["around 10 inches over the grate", "between 1 and 2 inches above the curb",
              "around 1 inch over the grate", "around 7 it was across Central"]
}

# An exact observation with depth wording still gets a spurious approximate time.
row = copy.deepcopy(ns["rows"][238 - 2])
row["observed_qualitative"] = "between 1 and 2 inches above the curb"
rec = copy.deepcopy(ns["bounds"][238])
rec.update(sha256=ob.row_hash(row), lo_navd88=4.16 + 1/12,
           hi_navd88=4.16 + 2/12, time_kind="stated_exact", text="synthetic depth interval")
with contextlib.redirect_stdout(io.StringIO()):
    r["depth_range_with_explicit_exact_time"] = ns["lookback"]([row], [rec])

# Same committed observation and band; change only its dispute flag for A/B.
from tests.test_bounds_round16 import lookback, real, model
row230 = real(230)
band230 = copy.deepcopy(ns["bounds"][230])
band230["csv_row"] = 2
now = ff.parse_station_local_time("2026-09-26T23:00:00-04:00")
claim = model(9.0, "2026-09-27T01:30:00Z", "2026-09-26")
for label, rec in [("disputed", band230),
                   ("undisputed", dict(band230, disputed=False)),
                   ("no_cap", dict(band230, hi_navd88=None))]:
    lb, health = lookback([row230], claim, now=now, bounds_text=json.dumps(rec)+"\n")
    r["cap_" + label] = {"payload": lb, "health": health,
                         "short": rendering._lookback_phrase(lb, short=True)}

with tempfile.TemporaryDirectory() as td:
    missing = Path(td) / "missing.jsonl"
    with mock.patch.object(ff, "_REPO_ROOT", str(root)):
        got = ff._observation_bounds(str(missing))
        r["missing_bounds"] = {"records": len(got), "health": ff._bounds_health()}
        # A directory used as the input path reliably raises OSError without chmod.
        try:
            ff._observation_bounds(td)
            r["unreadable_bounds"] = {"raised": None, "health": ff._bounds_health()}
        except OSError as e:
            r["unreadable_bounds"] = {"raised": type(e).__name__}

print(json.dumps(r, indent=2, ensure_ascii=False, allow_nan=False))
