"""Entry points. Run from the repository root:
  python3 -m history.scripts.as_issued.cli readiness   (inputs only: inventory + fidelity)
  python3 -m history.scripts.as_issued.cli advisory    (Study A; fetches gauge outcomes)
  python3 -m history.scripts.as_issued.cli street      (Study B; reads the observation ledger)
Outputs go to history/reports/as_issued/.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from as_issued import advisory as AD, archive as A, fidelity as F, noaa, obs as O, street as S  # noqa: E402

OUT = os.path.join(A.ROOT, "history", "reports", "as_issued")


def _write(name, obj):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    with open(path, "w") as f:
        json.dump(obj, f, sort_keys=True, default=str, separators=(",", ":"))
        f.write("\n")
    return path


def readiness():
    head = A._git("rev-parse", "HEAD").decode().strip()
    inv = A.inventory()
    rows = F.run(inv["rows"])
    summ = F.summarize(rows)
    meta = {"generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "repo_head": head,
            "note": "inputs only: no observation or outcome is read"}
    _write("readiness-inventory.json", {**meta, **{k: v for k, v in inv.items() if k != "rows"}, "rows": inv["rows"]})
    _write("readiness-fidelity.json", {**meta, "summary": summ, "rows": rows})
    print(json.dumps(summ, indent=1, default=str))


def advisory():
    """Study A. Gauge outcomes for every paired target are fetched once with raw
    bodies retained (history/data/as_issued/outcomes_advisory/)."""
    now = dt.datetime.now(dt.timezone.utc)
    inv = A.inventory()
    by_gen = {r["generated_utc"]: r for r in inv["rows"]}
    p30, p6, hilo = F.load_astronomy()
    rows = A.replay_records()
    pairs, skipped = AD.build_pairs(rows, lambda g: A.load_forecast(by_gen[g]["blob"]) if g in by_gen else None, hilo)
    levels, man = {}, None
    if pairs:
        d = os.path.join(A.ROOT, "history", "data", "as_issued", "outcomes_advisory")
        t0 = min(p["target"] for p in pairs) - dt.timedelta(hours=1)
        t1 = min(max(p["target"] for p in pairs) + dt.timedelta(hours=1), now)
        if t1 > t0:
            ents = noaa.fetch_range("water_level", t0, t1, d, extra={"datum": "MLLW"}, chunk_days=30)
            man = os.path.join(d, f"manifest-{now:%Y%m%dT%H%MZ}.json")
            with open(man, "w") as f:
                json.dump({"purpose": "Study A outcomes", "evaluated_utc": now.isoformat(), "responses": ents}, f, indent=1)
            levels = noaa.water_levels(noaa.load_bodies(man))
    AD.attach_outcomes(pairs, levels, now)
    from forecast import flood_forecast_daily as ff
    marks = {k: ff.LANDMARKS_BY_KEY[k] if hasattr(ff, "LANDMARKS_BY_KEY") else e for k, _l, e, _s in ff.LANDMARKS}
    rep = AD.evaluate(pairs, marks)
    rep.update(evaluated_utc=now.isoformat(), replay_records=len(rows), skipped=skipped,
               outcome_manifest=os.path.relpath(man, A.ROOT) if man else None, repo_head=A._git("rev-parse", "HEAD").decode().strip())
    print(json.dumps(rep, indent=1, default=str))
    _write("study-a-advisory.json", {"report": rep, "pairs": pairs})


def street():
    """Study B. Reads the observation ledger; no network."""
    ctx = S.Context()
    observations, sha = O.load()
    rep, pairs = S.evaluate(ctx, observations)
    rep.update(ledger_sha256=sha, observations_total=len(observations),
               observations_eligible=sum(o["eligible"] for o in observations),
               observation_exclusions={" ; ".join(o["reasons"]) or "no classifiable level": 1 for o in observations if not o["eligible"]},
               repo_head=A._git("rev-parse", "HEAD").decode().strip(),
               evaluated_utc=dt.datetime.now(dt.timezone.utc).isoformat())
    from collections import Counter
    rep["observation_exclusions"] = dict(Counter(" ; ".join(o["reasons"]) or "no classifiable level"
                                                 for o in observations if not o["eligible"]))
    print(json.dumps({k: v for k, v in rep.items() if k.startswith(("class_counts", "verdicts", "events", "pairs", "exclusion"))},
                     indent=1, default=str))
    _write("study-b-street.json", {"report": rep, "pairs": pairs,
                                   "observations": [{k: v for k, v in o.items()} for o in observations]})


if __name__ == "__main__":
    {"readiness": readiness, "advisory": advisory, "street": street}[sys.argv[1]]()
