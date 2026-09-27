#!/usr/bin/env python3
"""Event #10 (storm 2026-09-25-coastal) standard hydrographs — PLAYBOOK step 7,
audit 2026-09-27-a1 R2/R4/R5/R6. Supersedes
../../2026-09-26/analysis/corner_vs_gauge.png (retained as the forensic
record; that figure drew every qualitative report at the SW-grate line and
compared naive times to parsed ledger times).

Per tide, three stacked panels sharing the time axis:
  rain    MRMS PrecipRate catchment box mean, 6-min stride (in/hr); missing
          archive frames are marked; "no frames" panels say so
  reports qualitative/untimed reports in their own strip: dry report (down
          triangle), water reported but not measured (up triangle), gate
          state report (square). Hollow = surrogate/window/approximate
          time, drawn across its window. Nothing here sits on a water level.
  water   street tape (landmark elevation + depth, each at its stated time;
          whiskers = reported range, half-marker = bound), Sandy Hook raw
          archived preliminary series (flags retained, GMT transport) with
          the production despike, The Battery, landmark lines, and the
          gate note for THAT panel with the confidence the owner stated.
All times parse through the shared station helpers and are compared as UTC
instants; the axis shows station-local wall time.
Run: ~/.barnacle/venv/bin/python event10_hydrographs.py
"""
import csv
import datetime as dt
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))
from forecast import flood_forecast_daily as ff  # noqa: E402

UTC = dt.timezone.utc
ELEV = {k: e for k, _l, e, _s in ff.LANDMARKS}
INTERVALS = json.loads((HERE / "observation_intervals.json").read_text())
INTERVAL_BY_HASH = {r["sha256"]: r for r in INTERVALS["records"]}
MRMS = REPO / "history/data/mrms/mrms_extracted.csv"
LEDGER = REPO / "data/labeled_observations.csv"
LANDMARK_LINES = [("grate_SW", "#222222", "SW grate"), ("curb", "#c0392b", "curb"),
                  ("lawn_step", "#7c4dbc", "lawn step"),
                  ("porch_step1_top", "#6d4c2f", "1st porch step top ≈ garage entry (proxy)")]
TIDES = [
    ("2026-09-25-e01", "Fri 9/25 PM — no local flooding reported", "2026-09-25 17:00", "2026-09-26 00:30",
     "gate: believed closed by owner; NO direct report this evening"),
    ("2026-09-26-e01", "Sat 9/26 AM — crest 5.70 ft 09:06–09:13, whole garage", "2026-09-26 04:00", "2026-09-26 13:30",
     "gate: closure INFERRED from behavior; no direct report this morning"),
    ("2026-09-26-e02", "Sat 9/26 PM — late minor flood, crest 4.20–4.24 ft 22:11–22:29", "2026-09-26 17:30", "2026-09-27 00:00",
     "gate: SEEN closed 18:19 (photo, direct); untimed later visit 'almost certainly' closed (ledger 21:58 surrogate)"),
    ("2026-09-27-e01", "Sun 9/27 AM — crest 5.62 ft 09:44–10:06, garage ~90%", "2026-09-27 04:00", "2026-09-27 13:30",
     "gate: untimed visit between 08:24 and 08:36 'almost certainly' closed — not visual confirmation"),
]


def local(t_aware):
    return t_aware.astimezone(ff.STATION_TZ).replace(tzinfo=None)


def gauge(prefix):
    files = sorted((HERE / "gauge-sources").glob(f"{prefix}-*Z.json"))
    rows = json.loads(files[-1].read_text())["data"]
    out = []
    for r in rows:
        if r.get("v"):
            t = dt.datetime.strptime(r["t"], "%Y-%m-%d %H:%M").replace(tzinfo=UTC)
            out.append((t, float(r["v"]) + ff.MLLW_TO_NAVD88_OFFSET, r.get("q"), r.get("f")))
    return out, files[-1].name


def rain():
    out = []
    for r in csv.DictReader(MRMS.open()):
        if r["product"] == "PrecipRate" and r["utc"] >= "2026-09-25":
            out.append((dt.datetime.fromisoformat(r["utc"].replace("Z", "+00:00")),
                        float(r["box_mean"]) / 25.4))
    return sorted(out)


def ledger_rows():
    with LEDGER.open(newline="") as f:
        return [(ff._observation_row_hash(r), r) for r in csv.DictReader(f)]


def in_window(t_utc, a, b):
    ta = ff.parse_station_local_time(a).astimezone(UTC)
    tb = ff.parse_station_local_time(b).astimezone(UTC)
    return ta <= t_utc <= tb


def main():
    sh, sh_file = gauge("sandy-hook")
    bat, bat_file = gauge("battery")
    rn = rain()
    rows = ledger_rows()
    fig, axes = plt.subplots(16, 1, figsize=(11.5, 25),
                             gridspec_kw={"height_ratios": [1, 0.55, 3.2, 0.45] * 4, "hspace": 0.08})
    for i, (eid, title, a, b, gate_note) in enumerate(TIDES):
        ax_r, ax_q, ax_w, spacer = axes[4 * i], axes[4 * i + 1], axes[4 * i + 2], axes[4 * i + 3]
        spacer.axis("off")
        t0 = local(ff.parse_station_local_time(a)); t1 = local(ff.parse_station_local_time(b))
        # --- rain
        rr = [(local(t), v) for t, v in rn if in_window(t, a, b)]
        if rr:
            ax_r.bar([t for t, _ in rr], [v for _, v in rr], width=6 / 1440, color="#1f6feb", alpha=.8)
            exp, t = [], ff.parse_station_local_time(a).astimezone(UTC)
            while t <= ff.parse_station_local_time(b).astimezone(UTC):
                exp.append(t); t += dt.timedelta(minutes=6)
            have = {t for t, _ in rn}
            for m in exp:
                if m not in have:
                    ax_r.axvline(local(m), color="#bbbbbb", lw=1, ls=":")
            ax_r.set_ylabel("rain in/hr", fontsize=8)
            ax_r.text(0.995, 0.85, f"MRMS box mean, {len(rr)} frames; dotted = missing archive frame",
                      transform=ax_r.transAxes, ha="right", fontsize=7, color="#555")
        else:
            ax_r.text(0.5, 0.5, "rain frames not cached for this window", transform=ax_r.transAxes,
                      ha="center", fontsize=8, color="#888")
        ax_r.set_title(f"{eid} · {title}", fontsize=10, loc="left")
        # --- reports strip + water
        tape, strip = [], []
        for h, r in rows:
            if r.get("observer") != "john":
                continue
            try:
                t_aware = ff.parse_station_local_time(r["observation_time_local"])
            except (ValueError, TypeError):
                continue
            t_utc = t_aware.astimezone(UTC)
            if not in_window(t_utc, a, b):
                continue
            iv = INTERVAL_BY_HASH.get(h, {})
            key = r["landmark_key"]
            tk = iv.get("time_kind", "stated_exact")
            win = iv.get("time_window_local")
            w0 = local(ff.parse_station_local_time(win[0])) if win else local(t_aware)
            w1 = local(ff.parse_station_local_time(win[1])) if win else local(t_aware)
            dk = iv.get("depth_kind", "point" if r["observed_depth_in"].strip() else "qualitative")
            elev = ELEV.get(key)
            if dk in ("point", "range", "approximate", "upper_bound", "lower_bound") and elev is not None:
                lo, hi = iv.get("depth_lo_in"), iv.get("depth_hi_in")
                try:
                    d = float(r["observed_depth_in"])
                except ValueError:
                    d = lo if lo is not None else hi
                tape.append((local(t_aware), elev + d / 12, dk,
                             None if lo is None else elev + lo / 12,
                             None if hi is None else elev + hi / 12, tk, w0, w1))
            else:
                qual = (r.get("observed_qualitative") or "").lower()
                if "tide_gate" in key:
                    kind = "gate"
                elif ("no flooding" in qual or "no evidence" in qual or "receded completely" in qual
                      or "intersection clear" in qual or "safe to drive" in qual):
                    kind = "dry"
                else:
                    kind = "wet"
                strip.append((local(t_aware), kind, tk, w0, w1))
        # strip
        ycode = {"dry": 0.25, "wet": 0.55, "gate": 0.85}
        mk = {"dry": "v", "wet": "^", "gate": "s"}
        col = {"dry": "#0b6b3d", "wet": "#d97706", "gate": "#444444"}
        for t, kind, tk, w0, w1 in strip:
            exact = tk == "stated_exact"
            if not exact:
                ax_q.plot([w0, w1], [ycode[kind]] * 2, color=col[kind], lw=2, alpha=.5)
            ax_q.plot([t], [ycode[kind]], marker=mk[kind], ms=7, mfc=col[kind] if exact else "white",
                      mec=col[kind], mew=1.3, ls="none")
        ax_q.set_ylim(0, 1.05); ax_q.set_yticks([0.25, 0.55, 0.85])
        ax_q.set_yticklabels(["dry report", "water reported,\nnot measured", "gate report"], fontsize=7)
        ax_q.grid(alpha=.15)
        # water
        g = [(local(t), v, q, f) for t, v, q, f in sh if in_window(t, a, b)]
        ax_w.plot([t for t, *_ in g], [v for _, v, *_ in g], color="#9a9a9a", lw=1.0,
                  label="Sandy Hook raw (archived preliminary, q=p)")
        desp = ff._despike_gauge([(t, v) for t, v, *_ in g])
        ax_w.plot([t for t, _ in desp], [v for _, v in desp], color="#555555", lw=1.8,
                  label="Sandy Hook despiked (production _despike_gauge)")
        bb = [(local(t), v) for t, v, *_ in bat if in_window(t, a, b)]
        ax_w.plot([t for t, _ in bb], [v for _, v in bb], color="#7aa6c2", lw=1.2, ls="--",
                  label="The Battery (bay QC reference)")
        pts = sorted(p for p in tape if p[2] in ("point", "range", "approximate"))
        if pts:
            ax_w.plot([p[0] for p in pts], [p[1] for p in pts], "-", color="#d97706", lw=1, alpha=.7)
        for t, w, dk, lo, hi, tk, w0, w1 in tape:
            exact_t = tk == "stated_exact"
            if dk == "range" and lo is not None and hi is not None:
                ax_w.plot([t, t], [lo, hi], color="#b45309", lw=1.6)
            if dk == "upper_bound":
                ax_w.plot([t], [w], marker="v", ms=7, mfc="white", mec="#b45309", mew=1.4, ls="none")
            elif dk == "lower_bound":
                ax_w.plot([t], [w], marker="^", ms=7, mfc="white", mec="#b45309", mew=1.4, ls="none")
            else:
                ax_w.plot([t], [w], marker="D", ms=5 if dk == "point" else 6,
                          mfc="#d97706" if dk == "point" and exact_t else "white",
                          mec="#0b3d6b", mew=1.1, ls="none")
            if not exact_t:
                ax_w.plot([w0, w1], [w, w], color="#0b3d6b", lw=1, alpha=.5)
        for key, c, lbl in LANDMARK_LINES:
            ax_w.axhline(ELEV[key], color=c, ls="--", lw=.9, alpha=.7)
            ax_w.text(t1, ELEV[key], " " + lbl, color=c, fontsize=7, va="center")
        ax_w.text(0.01, 0.97, gate_note, transform=ax_w.transAxes, fontsize=8, va="top",
                  bbox=dict(boxstyle="round", fc="white", ec="#cccccc", alpha=.9))
        ax_w.set_ylim(0, 6.3); ax_w.set_ylabel("ft NAVD88"); ax_w.grid(alpha=.2)
        for ax in (ax_r, ax_q, ax_w):
            ax.set_xlim(t0, t1)
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        ax_r.tick_params(labelbottom=False); ax_q.tick_params(labelbottom=False)
    handles = [
        Line2D([], [], marker="D", color="#d97706", mec="#0b3d6b", ls="-", lw=1, label="street tape (landmark + depth), stated time"),
        Line2D([], [], marker="D", color="white", mec="#0b3d6b", ls="none", label="approximate reading / surrogate or window time (bar = window)"),
        Line2D([], [], color="#b45309", lw=1.6, label="reported depth range"),
        Line2D([], [], marker="v", color="white", mec="#b45309", ls="none", label="upper bound (water at most here)"),
        Line2D([], [], marker="^", color="white", mec="#b45309", ls="none", label="lower bound (water at least here)"),
        Line2D([], [], color="#9a9a9a", lw=1, label="Sandy Hook raw (archived preliminary)"),
        Line2D([], [], color="#555555", lw=1.8, label="Sandy Hook despiked"),
        Line2D([], [], color="#7aa6c2", lw=1.2, ls="--", label="The Battery"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=8, frameon=False,
               bbox_to_anchor=(0.5, 0.005))
    fig.suptitle("Event #10 — storm 2026-09-25-coastal: rain forcing, owner reports and street water vs the bay gauge\n"
                 "Bay lines are GAUGE levels, not street measurements; gate state is per panel with the owner's stated confidence",
                 fontsize=11.5, y=0.995)
    fig.text(0.01, 0.0, f"sources: {sh_file}, {bat_file}, history/data/mrms/mrms_extracted.csv, data/labeled_observations.csv, "
             "observation_intervals.json · rendered " + dt.datetime.now(UTC).strftime("%Y-%m-%d %H:%MZ"), fontsize=6.5, color="#666")
    fig.subplots_adjust(top=0.965, bottom=0.04, left=0.07, right=0.80)
    fig.savefig(HERE / "event10_hydrographs.png", dpi=110)
    fig.savefig(HERE / "event10_hydrographs.pdf")
    print("wrote", HERE / "event10_hydrographs.png")


if __name__ == "__main__":
    main()
