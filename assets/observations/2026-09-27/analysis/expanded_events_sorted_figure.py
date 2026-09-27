#!/usr/bin/env python3
"""Additional lowest-to-highest vertical view; reads existing data unchanged.

Run with ~/.barnacle/venv/bin/python. Only writes expanded_events_sorted PNG/PDF
and a render manifest. No changes to source data, original plots or production.
"""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
NAVY, STEM, MODEL, GRAY, TEAL = '#17365d', '#2e6da4', '#d97706', '#6c7076', '#278579'


def draw():
    source = HERE / 'expanded_events_data.json'
    data = json.loads(source.read_text())
    landmarks = json.loads((HERE / 'all_anchors_data.json').read_text())['landmarks']
    events = sorted((e for e in data['events'] if e['level_in_vs_sw'] is not None),
                    key=lambda e: (e['level_in_vs_sw'], e['episode_id']))
    unranked = [e for e in data['events'] if e['level_in_vs_sw'] is None]
    assert len({e['episode_id'] for e in data['events']}) == len(events) + len(unranked)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11})
    fig, ax = plt.subplots(figsize=(26, 11))
    fig.subplots_adjust(left=.045, right=.915, top=.78, bottom=.28)
    fig.text(.045, .955, 'Recorded flood levels at Bay & Central — expanded comparison',
             fontsize=24, weight='bold', color=NAVY)
    fig.text(.045, .918,
             f'{len(events)} numeric reference levels, lowest to highest · same evidence as the chronological view · September 27, 2026',
             fontsize=14, color='#444444')
    colors = {'grate_SW': '#222222', 'gutter_walkway': '#2f8f5f', 'curb': '#c0392b',
              'lawn_step': '#7c4dbc', 'porch_step_base': '#a08060', 'porch_step1_top': '#6d4c2f'}
    for lm in landmarks:
        key, y = lm['key'], lm['in_vs_sw']
        ax.axhline(y, color=colors[key], ls=':' if key == 'porch_step_base' else '--',
                   lw=1.15, alpha=.75, zorder=1)
        dy = -1.0 if key == 'lawn_step' else (.7 if key == 'porch_step_base' else .16)
        ax.text(1.006, y+dy, f"{lm['label']}\n+{y:.1f}″", transform=ax.get_yaxis_transform(),
                color=colors[key], fontsize=9.5, va='center')
    inferred = {'reconstruction', 'inferred_peak', 'historical_bound', 'inferred_lower_bound'}
    labels = []
    for i, e in enumerate(events):
        y, kind = e['level_in_vs_sw'], e['evidence_kind']
        infer, bound = kind in inferred, 'lower_bound' in kind
        c = GRAY if infer else (TEAL if kind in ('photo', 'lower_bound') else NAVY)
        ax.vlines(i, 0, y, color=c if infer or kind in ('photo', 'lower_bound') else STEM,
                  lw=2.1, linestyle='--' if infer else '-', zorder=2)
        lo, hi = e.get('range_low_in'), e.get('range_high_in')
        if lo is not None and hi is not None:
            assert lo <= y <= hi
            ax.errorbar(i, y, yerr=[[y-lo], [hi-y]], fmt='none', ecolor=c,
                        elinewidth=1.5, capsize=4, zorder=3)
        marker = '^' if bound else ('s' if infer or kind == 'photo' else 'o')
        ax.plot(i, y, marker=marker, ms=8, mfc='white' if infer else c,
                mec=c, mew=1.6, zorder=4)
        if bound:
            ax.annotate('', (i, y+1.4), (i, y+.25),
                        arrowprops={'arrowstyle': '->', 'color': c, 'lw': 1.2})
        prefix = '≈' if infer or kind == 'photo' else ''
        label = f'{prefix}{y:.1f}″' + (' +' if bound else '')
        ax.annotate(label, (i, max(y+1.4 if bound else y, hi if hi is not None else y)),
                    xytext=(-14 if e['episode_id'] == '2026-08-27-e01' else 0, 9), textcoords='offset points', ha='center',
                    fontsize=10, weight='bold', color=c)
        if e.get('model_hindcast_in') is not None:
            ax.plot(i+.20, e['model_hindcast_in'], 'D', ms=6.5, color=MODEL,
                    mec='white', mew=.8, zorder=4)
        eid = e['episode_id']
        month = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][int(eid[5:7])-1]
        labels.append(f'{month} {int(eid[8:10])}\n{eid[:4]}\n{eid[-3:]}')
    ax.set_xticks(range(len(events)), labels, fontsize=9.5)
    ax.tick_params(axis='x', length=0, pad=12)
    ax.set_xlim(-.6, len(events)-.4)
    ax.set_ylim(-.5, 31)
    ax.set_yticks(range(0, 31, 5))
    ax.set_ylabel('Street water level · inches above SW grate', fontsize=13)
    ax.grid(axis='y', color='#ededed', lw=.7)
    ax.set_axisbelow(True)
    for side in ('top', 'right'): ax.spines[side].set_visible(False)
    for side in ('bottom', 'left'): ax.spines[side].set_color('#bbbbbb')
    fig.legend(handles=[
        Line2D([], [], marker='o', color=STEM, mfc=NAVY, mec=NAVY, lw=2,
               label='Tape / landmark or reported bracket'),
        Line2D([], [], marker='s', color=GRAY, mfc='white', mec=GRAY, ls='--',
               label='Reconstruction / inferred reference'),
        Line2D([], [], marker='s', color=TEAL, ls='none', label='Photo interpretation'),
        Line2D([], [], marker='^', color=TEAL, ls='none', label='Lower bound; arrow points upward'),
        Line2D([], [], marker='D', color=MODEL, ls='none', label='Historical model hindcast'),
    ], loc='upper left', bbox_to_anchor=(.04, .875), ncol=5, frameon=False, fontsize=10)
    notes = [
        'Sorted by the displayed reference value, not a definitive ranking of actual crests. Bounds and uncertain estimates may change the true order.',
        'April 18: likely lawn-step level, possibly higher (owner recollection + gauge). October 30: reconstructed crest. Neither is a direct peak measurement.',
        'August 27: approximate driveway-witness proxy, not a surveyed hard bound; actual crest missed. August 7: recession backcast. December 19: 08:12 bracket.',
        'Whiskers show source ranges / sample spreads, not confidence intervals. Orange diamonds are mixed-vintage historical hindcasts, not as-issued forecast skill.',
        'No numeric height to sort: Aug 2025 (Aug 21 tentative), Apr 17 2026, May 18 2026; dry checks: May 30 e01, May 31, Sep 25. All remain in the chronological view.',
        'Source: expanded_events_data.json. Same values, sources and evidence classes; existing chronological and original all_anchors figures retained unchanged.',
    ]
    for j, text in enumerate(notes):
        fig.text(.045, .18-j*.025, text, fontsize=10, color='#555555')
    for ext in ('png', 'pdf'):
        fig.savefig(HERE/f'expanded_events_sorted.{ext}', dpi=160, facecolor='white')
    plt.close(fig)
    manifest = {'source_file': source.name, 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                'sort': 'level_in_vs_sw ascending, episode_id tie-break',
                'plotted_episode_ids': [e['episode_id'] for e in events],
                'unranked_episode_ids': [e['episode_id'] for e in unranked],
                'qualification': 'Unranked records remain listed in figure notes; unavailable heights are not plotted as zero.'}
    (HERE/'expanded_events_sorted_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(f'Wrote sorted PNG/PDF: {len(events)} numeric points; {len(unranked)} unranked records listed in notes.')


if __name__ == '__main__':
    draw()
