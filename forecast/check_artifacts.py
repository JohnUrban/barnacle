#!/usr/bin/env python3
"""Publish gate (2026-07-18): refuse to ship corrupted artifacts.

Born from two incidents where git merge artifacts (autostash /
stash-pop conflicts) shipped conflict markers inside forecast.json —
iOS's strict JSON parser broke the widget both times while Python's
lenient one hid it. Run before ANY commit of docs/ or data/:
  1. no conflict markers anywhere in docs/ or data/
  2. every .json in docs/ parses under STRICT rules (json.loads
     forbidding NaN/Infinity — matches JSON.parse on iOS)
Exit 1 = do not commit.
"""
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
bad = []
for top in ("docs", "data"):
    for dirpath, _dirs, files in os.walk(os.path.join(ROOT, top)):
        for fn in files:
            path = os.path.join(dirpath, fn)
            try:
                with open(path, "rb") as f:
                    blob = f.read()
            except OSError:
                continue
            if b"<<<<<<< " in blob or b">>>>>>> " in blob:
                bad.append((path, "conflict markers"))
                continue
            if fn.endswith(".json"):
                try:
                    json.loads(blob.decode("utf-8"),
                               parse_constant=lambda c: (_ for _ in ()).throw(
                                   ValueError(f"non-strict constant {c}")))
                except Exception as e:
                    bad.append((path, f"strict-parse: {e}"))
for path, why in bad:
    print(f"PUBLISH GATE FAIL: {os.path.relpath(path, ROOT)} — {why}")
if bad:
    sys.exit(1)
print(f"publish gate: clean")
