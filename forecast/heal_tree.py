#!/usr/bin/env python3
"""Self-heal mechanical corruption in the working tree (2026-07-20).

Born from the 02:00 UTC twin-run race: two cron fires of the same
workflow rebased into each other, committed conflict markers, and
every subsequent run failed the publish gate forever — the gate
quarantined corruption but nothing healed it. This script makes the
bot self-healing for the ONLY corruption class we've ever seen
(merge artifacts in generated/append-only files):

  - data/predictions_log.csv: strip markers, dedup, sort (append-only
    union — the same repair applied by hand three times now)
  - data/*.json caches (alert_state, tide_predictions_cache,
    observed_peaks_cache is csv): if unparseable/marked, DELETE —
    every one of them regenerates or degrades gracefully
  - docs/**: marked files are deleted; the publish run regenerates
    every docs artifact it still needs

Run at workflow start (heal inherited corruption) — the publish gate
still runs before every push (catch NEW corruption).
"""
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
healed = []

log = os.path.join(ROOT, "data", "predictions_log.csv")
if os.path.exists(log):
    raw = open(log).read()
    if "<<<<<<< " in raw:
        header, seen, rows = None, set(), []
        for ln in raw.splitlines():
            if ln.startswith(("<<<<<<<", "=======", ">>>>>>>")) or not ln.strip():
                continue
            if header is None and not ln[0].isdigit():
                header = ln
                continue
            if ln not in seen:
                seen.add(ln)
                rows.append(ln)
        rows.sort()
        with open(log + ".tmp", "w") as f:
            f.write((header or "") + "\n" + "\n".join(rows) + "\n")
        os.replace(log + ".tmp", log)
        healed.append(f"predictions_log.csv unioned ({len(rows)} rows)")

for name in ("alert_state.json", "tide_predictions_cache.json"):
    p = os.path.join(ROOT, "data", name)
    if os.path.exists(p):
        blob = open(p, "rb").read()
        bad = b"<<<<<<< " in blob
        if not bad:
            try:
                json.loads(blob.decode("utf-8"))
            except Exception:
                bad = True
        if bad:
            os.remove(p)
            healed.append(f"{name} deleted (regenerates)")

for dirpath, _dirs, files in os.walk(os.path.join(ROOT, "docs")):
    for fn in files:
        p = os.path.join(dirpath, fn)
        try:
            if b"<<<<<<< " in open(p, "rb").read():
                os.remove(p)
                healed.append(f"docs: deleted {os.path.relpath(p, ROOT)}")
        except OSError:
            continue

if healed:
    print("HEALED:")
    for h in healed:
        print("  -", h)
else:
    print("tree healthy — nothing to heal")
