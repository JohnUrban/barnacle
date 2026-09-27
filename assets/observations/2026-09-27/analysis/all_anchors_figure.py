#!/usr/bin/env python3
"""Offline, source-backed comparison; no model fitting or network calls.

Run with ~/.barnacle/venv/bin/python from any directory. Data/interpretation
receipt is all_anchors_data.json. Historical hindcasts are reference values,
not newly evaluated as-issued forecasts. PNG and PDF are generated here.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
NAVY, STEM, MODEL, GRAY = "#17365d", "#2e6da4", "#d97706", "#6c7076"


def draw():
    data = json.loads((HERE / "all_anchors_data.json").read_text())
    events = data["events"]
    assert len({e["episode_id"] for e in events}) == len(events)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
    fig, ax = plt.subplots(figsize=(20, 9.6))
    fig.subplots_adjust(left=.055, right=.90, top=.79, bottom=.23)
    fig.text(.055, .955, "Recorded flood levels at Bay & Central", fontsize=22,
             weight="bold", color=NAVY)
    fig.text(.055, .917, "Historical comparison updated through September 27, 2026 · each flood episode shown separately",
             fontsize=13, color="#444444")
    colors = {"grate_SW":"#222222", "gutter_walkway":"#2f8f5f", "curb":"#c0392b",
              "lawn_step":"#7c4dbc", "porch_step_base":"#a08060", "porch_step1_top":"#6d4c2f"}
    for lm in data["landmarks"]:
        key, y = lm["key"], lm["in_vs_sw"]
        ax.axhline(y, color=colors[key], ls=":" if key=="porch_step_base" else "--",
                   lw=1.15, alpha=.75, zorder=1)
        dy = -1.05 if key=="lawn_step" else (.65 if key=="porch_step_base" else .16)
        ax.text(1.008, y+dy, f"{lm['label']}\n+{y:.1f}″", transform=ax.get_yaxis_transform(),
                color=colors[key], fontsize=9, va="center")
    reconstructed = {"reconstruction", "inferred_peak", "historical_bound"}
    for i,e in enumerate(events):
        y, kind = e["level_in_vs_sw"], e["evidence_kind"]
        infer = kind in reconstructed
        c = GRAY if infer else NAVY
        ax.vlines(i, 0, y, color=c if infer else STEM,
                  lw=2.3, linestyle="--" if infer else "-", zorder=2)
        if e["range_low_in"] is not None:
            assert e["range_low_in"] <= y <= e["range_high_in"]
            ax.errorbar(i,y,yerr=[[y-e["range_low_in"]],[e["range_high_in"]-y]],
                        fmt="none",ecolor=c,elinewidth=1.5,capsize=5,zorder=3)
        ax.plot(i,y,marker="s" if infer else "o",ms=9,mfc="white" if infer else NAVY,
                mec=c,mew=1.7,zorder=4)
        label=f"+{y:.1f}″"
        if kind=="reconstruction":label="~"+label+"\nreconstructed"
        elif kind=="inferred_peak":label="~"+label+"\ninferred crest"
        elif kind=="historical_bound":label="~"+label+"\n08:12 bracket"
        ax.annotate(label,(i,e["range_high_in"] if e["range_high_in"] is not None else y),
                    xytext=(0,27 if kind=="inferred_peak" else 10),textcoords="offset points",ha="center",fontsize=10.5,
                    weight="bold",color=c)
        if e["model_hindcast_in"] is not None:
            ax.plot(i+.20,e["model_hindcast_in"],"D",ms=7,color=MODEL,
                    mec="white",mew=.8,zorder=4)
    ax.set_xticks(range(len(events)),[e["label"] for e in events],fontsize=9)
    ax.tick_params(axis="x",length=0,pad=12)
    ax.set_xlim(-.55,len(events)-.45)
    ax.set_ylim(-.5,31)
    ax.set_yticks(range(0,31,5))
    ax.set_ylabel("Street water level · inches above SW grate",fontsize=12)
    ax.grid(axis="y",color="#ededed",lw=.7)
    ax.set_axisbelow(True)
    for side in ("top","right"):ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#bbbbbb")
    ax.spines["left"].set_color("#bbbbbb")
    ax.text(11.5,30.1,"First two reported garage-entry floods",ha="center",
            fontsize=11,weight="bold",color=NAVY)
    ax.text(11,28.6,"~90% of garage",ha="center",fontsize=10,color=NAVY)
    ax.text(12,29.4,"whole garage",ha="center",fontsize=10,color=NAVY)
    fig.legend(handles=[
        Line2D([],[],marker="o",color=STEM,mfc=NAVY,mec=NAVY,lw=2,
               label="Tape / landmark observation or reported bracket"),
        Line2D([],[],marker="s",color=GRAY,mfc="white",mec=GRAY,ls="--",
               label="Historical reconstruction / inferred level"),
        Line2D([],[],marker="D",color=MODEL,ls="none",
               label="Historical tank hindcast (where available)"),
    ],loc="upper left",bbox_to_anchor=(.05,.875),ncol=3,frameon=False,fontsize=10)
    notes=[
        "October 30: ~20.8″ is a model-aided reconstruction from memory and post-peak photos, NOT a measured crest or lower bound.",
        "John confirms both September morning floods were higher. December 19 shows an observation-time bracket; its peak was not observed.",
        "Whiskers are reported brackets or declared reference windows, not statistical confidence intervals. August 7 includes a recession backcast.",
        "Orange diamonds retain historical hindcasts, NOT as-issued forecasts. No new model comparison is claimed for the four added episodes.",
        "Comparison cohort: nine prior reference entries + Sep 13 e02 + Sep 26 e01/e02 + Sep 27 e01. Sources and exact values: all_anchors_data.json.",
    ]
    for j,text in enumerate(notes):fig.text(.055,.145-j*.023,text,fontsize=9,color="#555555")
    fig.savefig(HERE/"all_anchors.png",dpi=160,facecolor="white")
    fig.savefig(HERE/"all_anchors.pdf",facecolor="white")


if __name__ == "__main__":
    draw()
    print("Wrote all_anchors.png and all_anchors.pdf (offline; no production changes)")
