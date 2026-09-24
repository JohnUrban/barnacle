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
from as_issued import advisory as AD, archive as A, fidelity as F, noaa, obs as O, report as R, street as S  # noqa: E402

OUT = os.path.join(A.ROOT, "history", "reports", "as_issued")


def _write(name, obj):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    with open(path, "w") as f:
        # strict JSON as a final BACKSTOP (a4 round 05): a non-finite number reaching an
        # output is a bug; admission handling, not this, is what keeps it out
        json.dump(obj, f, sort_keys=True, default=str, separators=(",", ":"), allow_nan=False)
        f.write("\n")
    return path


def readiness():
    head = A._git("rev-parse", "HEAD").decode().strip()
    inv = A.inventory()
    rows = F.run(inv["rows"])
    summ = F.summarize(rows)
    meta = {"generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "repo_head": head,
            "note": "inputs only: no observation or outcome is read"}
    _write(f"readiness-inventory-{REVISION}.json", {**meta, **{k: v for k, v in inv.items() if k != "rows"}, "rows": inv["rows"]})
    _write(f"readiness-fidelity-{REVISION}.json", {**meta, "summary": summ, "rows": rows})
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
    reuse = next((a.split("=", 1)[1] for a in sys.argv[2:] if a.startswith("--reuse=")), None)
    if reuse:
        # offline reproduction: the saved raw outcome responses (hash-verified) and their evaluation time
        man = os.path.join(A.ROOT, reuse)
        with open(man) as f:
            now = dt.datetime.fromisoformat(json.load(f)["evaluated_utc"])
        levels = noaa.water_levels(noaa.load_bodies(man))
    elif pairs:
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
    marks = {k: e for k, _l, e, _s in ff.LANDMARKS}
    rep = AD.evaluate(pairs, marks)
    rep.update(evaluated_utc=now.isoformat(), replay_records=len(rows), skipped=skipped,
               outcome_manifest=os.path.relpath(man, A.ROOT) if man else None, repo_head=A._git("rev-parse", "HEAD").decode().strip())
    print(json.dumps(rep, indent=1, default=str))
    _write(f"study-a-advisory-{REVISION}.json", {"report": rep, "pairs": pairs})


REVISION = "r4"   # audit 2026-09-24-a4 round 05 completion; r1 (no suffix), r2 and r3 outputs are preserved unchanged


def load_normalized():
    """Normalization-manifest entries, each verified against the current ledger row hash."""
    from as_issued import normalization as N
    with open(N.OUT) as f:
        man = json.load(f)
    hashes, ledger_sha, _n = N.row_hashes()
    bad = [e["row"] for e in man["entries"] if hashes.get(e["row"]) != e["row_sha256"]]
    if bad:
        raise SystemExit(f"normalization manifest out of date for ledger rows {bad}; rebuild it")
    return man, ledger_sha


def street():
    """Study B (revision r2). Reads the normalization manifest; no network."""
    ctx = S.Context()
    man, sha = load_normalized()
    rep, pairs = S.evaluate(ctx, man["entries"])
    rep.update(ledger_sha256=sha, manifest_entries=len(man["entries"]),
               primary_entries=sum(e["primary"] for e in man["entries"]),
               repo_head=A._git("rev-parse", "HEAD").decode().strip(),
               evaluated_utc=dt.datetime.now(dt.timezone.utc).isoformat(), revision=REVISION)
    print(json.dumps({k: v for k, v in rep.items() if k.startswith(("class_counts", "verdicts", "events", "pairs", "exclusion"))},
                     indent=1, default=str))
    _write(f"study-b-street-{REVISION}.json", {"report": rep, "pairs": pairs})
    events = R.per_event(pairs, man["event_peaks"])
    _write(f"study-b-events-{REVISION}.json", {"per_event_published_line": events,
                                              "conditional_burst_scenarios": R.conditional_scenarios(ctx, events),
                                              "input_fault_annotations": input_faults(ctx, pairs)})


def input_faults(ctx, pairs):
    """Archive-evidenced input faults in the issuances behind the pairs (not inferred from errors)."""
    out = {}
    for p in pairs:
        s = next(x for x in ctx.issuances if x["blob"] == p["blob"])
        f = ctx.forecast(s)
        notes = []
        if f.get("tide_predictions_stale"):
            notes.append("tide_predictions_stale: astronomy synthesized from cached extremes (NOAA outage)")
        lg = [q.get("value_mllw") for q in (f.get("live_gauge_24h") or []) if isinstance(q.get("value_mllw"), (int, float))]
        if lg and max(lg) > 9.0:
            notes.append(f"published gauge levels up to {max(lg):.2f} ft MLLW (sensor malfunction; despike added "
                         "2026-07-09, commit b10568276)")
        if notes:
            out[str(p["issuance"])] = notes
    return out


if __name__ == "__main__":
    {"readiness": readiness, "advisory": advisory, "street": street}[sys.argv[1]]()
