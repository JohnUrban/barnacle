"""All-anchors model-vs-measured comparison: ALL EIGHT measured
floods — the six frozen v0.10.1 anchors plus the two post-cutover
events (Aug 7 #7, Sep 1 #8), whose hindcasts (‡) come from the
committed event_hindcast recipe, not the frozen fixture.

2026-09-03 refresh (audit-sweep loop closure): added Aug 7 — the one
measured flood that had NEVER been in this figure (it post-dated the
original six-anchor build and the #8 refresh only appended Sep 1) —
and fixed the stale six-event xlim that had been CLIPPING Oct 30
(the largest measured flood) out of the committed PNG while the
title said "six" and the docstring said "7".

Replicates the 2026-07-09 four_rain_floods.png grammar (peak stems,
landmark palette, sub-labels with rate + bay state) with the v0.10.1
tank hindcast beside each measured peak.
"""
import runpy
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
ns = runpy.run_path(str(HERE / "all_anchors_model.py"))
R = ns["RESULTS"]
for k, (v, t) in R.items():
    print(f"{k:12s} +{v:.2f} @ {t:%H:%M}")

NAVY_DOT, NAVY_STEM = "#17365d", "#2e6da4"
MODEL = "#d97706"

# (label, measured, yerr_lo, yerr_hi, meas_annot, model_val, model_tag)
events = [
    ("Dec 19 2025\nsteady 0.44 in/hr\nbay HIGH (4.04)",
     11.15, 1.05, 1.05, "+11.2″\n(band 10.1–12.2″)",
     R["dec19_at_obs"][0], "†"),
    ("Aug 3 2026 — #6\nburst 2.84 in/hr × 14 min\nbay LOW (2.3)",
     13.8, 0.1, 0.1, "+13.8″\n(13.7–13.9)",
     R["aug3"][0], ""),
    ("Sep 1 2026 — #8\n~2.0 in/hr × 10 min\nbay DEAD LOW (−0.7)",
     13.9, 0.2, 0.3, "+13.9″\n(13.7–14.2)",
     12.0, "‡"),
    ("Jul 6 2026\nburst 2.95 in/hr\nbay LOW (2.6)",
     15.4, 0.4, 0.4, "+15.4″\n(15.0–15.8)",
     R["jul6"][0], ""),
    ("Aug 7 2026 — #7\npulses 2.1→4.4 in/hr\nbay DEAD LOW (0.77)",
     15.4, 0.4, 0.4, "+15.4″\n(15.0–15.8)",
     16.9, "‡"),
    ("Jul 9 2026 — #4\nburst 5.53 in/hr\nbay at grates (3.2)",
     18.7, 0.0, 0.0, "+18.7″\n(measured)",
     R["jul9"][0], ""),
    ("Jul 18 2026 — #5\nbox 2.4–3.8 in/hr *\nbay LOW, ebbing neap (2.2)",
     19.9, 0.0, 0.0, "+19.9″\n(measured)",
     R["jul18"][0], "*"),
    ("Oct 30 2025\nburst 2.71 in/hr\nbay HIGH (4.81)",
     20.8, 0.0, 0.0, "+20.8″\n(photo anchor ≥)",
     R["oct30"][0], ""),
]

fig, ax = plt.subplots(figsize=(13.5, 7.4))

# landmark ladder (site chart grammar)
landmarks = [
    (0.0, "#222222", "-", 1.4, "SW grate 0″"),
    (3.1, "#2f8f5f", "--", 1.0, "gutter"),
    (7.7, "#c0392b", "--", 1.0, "curb"),
    (13.7, "#7c4dbc", "--", 1.0, "lawn step"),
    (13.9, "#a08060", ":", 1.0, "porch base"),
    (22.7, "#6d4c2f", "--", 1.6, "1st porch step TOP +22.7″"),
]
for y, c, ls, lw, lbl in landmarks:
    ax.axhline(y, color=c, ls=ls, lw=lw, alpha=0.75, zorder=1)
    if y == 22.7:                       # label at left; Oct 30 owns the right
        ax.text(-0.5, y + 0.25, lbl, color=c, fontsize=9,
                fontweight="bold", ha="left")
    elif y == 13.7:                     # lawn step below its line: porch base above
        ax.text(7.62, y - 0.85, lbl, color=c, fontsize=9)
    else:
        ax.text(7.62, y + 0.25, lbl, color=c, fontsize=9,
                fontweight="bold" if y == 0.0 else "normal")

xs = range(len(events))
for x, (lbl, meas, elo, ehi, annot, model, tag) in zip(xs, events):
    ax.vlines(x, 0, meas, color=NAVY_STEM, lw=3.5, zorder=2)
    if elo or ehi:
        ax.errorbar([x], [meas], yerr=[[elo], [ehi]], fmt="none",
                    ecolor=NAVY_DOT, elinewidth=1.4, capsize=5, zorder=3)
    ax.plot([x], [meas], "o", ms=11, color=NAVY_DOT, zorder=4)
    ax.annotate(annot, xy=(x, meas + max(ehi, 0.15)),
                xytext=(0, 8), textcoords="offset points",
                ha="center", fontsize=10, fontweight="bold", zorder=5)
    ax.plot([x + 0.22], [model], "D", ms=9, color=MODEL,
            markeredgecolor="white", markeredgewidth=1.2, zorder=4)
    dy = -16 if lbl.startswith("Aug 7") else -4   # clear the twin +15.4 annot
    ax.annotate(f"model +{model:.1f}″{tag}", xy=(x + 0.22, model),
                xytext=(9, dy), textcoords="offset points",
                ha="left", va="center", fontsize=8.5, color=MODEL,
                fontweight="bold", zorder=5)

ax.set_xticks(list(xs))
ax.set_xticklabels([e[0] for e in events], fontsize=8.5)
ax.set_xlim(-0.55, 7.7)
ax.set_ylim(-0.8, 27)
ax.set_ylabel("peak street water (inches vs SW grate)", fontsize=11)
ax.grid(axis="y", color="0.93", zorder=0)
ax.set_axisbelow(True)
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)

ax.set_title("All eight measured floods — every one is rain-driven;\n"
             "measured peak vs v0.10.1 tank on measured MRMS rain",
             fontsize=14, fontweight="bold", pad=14)

ax.legend(handles=[
    Line2D([], [], marker="o", ls="-", color=NAVY_STEM, mfc=NAVY_DOT,
           mec=NAVY_DOT, ms=9, lw=3, label="measured peak (tape / landmark)"),
    Line2D([], [], marker="D", ls="none", color=MODEL, mec="white",
           ms=8, label="v0.10.1 tank hindcast (one pass, all events)"),
], loc="upper left", fontsize=9, frameon=True)

fig.text(0.5, 0.015,
    "One hindcast pass: v0.10.1 (K=1.296M, γ=0.78, k_out=3.50/h, lag 15 min), "
    "production stage curve, step-held MRMS frames, dt=2 min, V=0 start, bay fixed at event level.\n"
    "* Jul 18: MRMS underread the storm core (catchment-box rates) — the gap is input, "
    "not physics.   † Dec 19: model at the 08:12 observation time; "
    "modeled crest +%.1f″ @07:34 was unobserved.   Oct 30: photo-anchor lower bound "
    "(≥5.25 NAVD88).\n"
    "‡ Aug 7 / Sep 1: post-cutover events (not among the six frozen v0.10.1 "
    "anchors); hindcast via the committed event_hindcast recipe, same physics, "
    "one pass." % R["dec19"][0],
    ha="center", fontsize=7.5, color="#666666")

fig.tight_layout(rect=(0, 0.045, 1, 1))
out = HERE / "all_anchors.png"
fig.savefig(out, dpi=150, bbox_inches="tight")
print("wrote", out)
