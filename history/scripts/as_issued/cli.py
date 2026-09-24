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
from as_issued import archive as A, fidelity as F  # noqa: E402

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


if __name__ == "__main__":
    {"readiness": readiness}[sys.argv[1]]()
