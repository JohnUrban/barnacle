"""Read-only round-03 checks: python verify_repairs.py CANDIDATE_ROOT.

The candidate can be a git-archive snapshot. Historical inputs and git objects
come from the real repo containing this script; candidate code is imported from
CANDIDATE_ROOT. No network, alerts, production writes, or recalibration.
"""
import contextlib
import datetime as dt
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(CANDIDATE))
sys.path.insert(0, str(CANDIDATE / 'tests'))
from forecast import flood_forecast_daily as ff, replay_archive as ra
import test_selective_recovery as rec
import test_outlook as to

assert Path(ff.__file__).is_relative_to(CANDIDATE)
raw = subprocess.check_output([
    sys.executable, str(Path(__file__).with_name('verify_candidate.py')),
    str(CANDIDATE)], text=True)
out = json.loads(raw)
out['candidate'] = 'b95b2982958d6fc676e79f64c240411069840441'
out['candidate_root'] = str(CANDIDATE)
# Round 01's immutable probe calls any successful build "unexpected success".
# Verify the repaired health behavior explicitly instead of retaining that label.
bad_mean = {'mean_ft': .54, 'n_hours': 8000,
            'computed_utc': '2026-09-23T00:00:00'}
with patch.object(ff._surge_mean, 'load', return_value=bad_mean):
    f = rec.build()
assert f['input_health']['surge_mean']['status'] == 'degraded'
assert f['water_series']
out['malformed_mean_whole_build'] = {
    'built_with_water_series': True,
    'health': f['input_health']['surge_mean']}
assert all(abs(p['difference_ft']) <= .011
           for p in out['outlook_fallback_comparisons'])
assert out['synthetic_mixed_version_score']['n'] == 1
assert out['selected_state_provenance']['age_min'] == 600

f['outlook_7d'] = to._build()
record = ra.build_record(f, to._fixture_data(), {}, [(to.NOW, .1234567)])
with tempfile.TemporaryDirectory() as d:
    p = Path(ra.append(record, d))
    before = p.read_bytes()
    ra.append(record, d)
    assert p.read_bytes() == before + before
    assert ra.validate_file(p) == []
missing = ra.build_record(f, {}, {}, None)
assert missing['nwps'] is None and missing['qpf_hourly'] is None
out['archive'] = {
    'append_preserves_prefix': True, 'gate_accepts_record': True,
    'raw_nwps_hours': len(ra.expand(record['nwps']['hourly'])),
    'outlook_hours': len(ra.expand(record['outlook_hourly'])),
    'qpf_in_hr': ra.expand(record['qpf_hourly'])[0][1]['in_hr'],
    'unavailable': missing['unavailable']}

# Reproduce Claude's B/C/D without altering its scientific logic. Redirect
# only ROOT to the existing data/git store; ff remains the candidate import.
p = CANDIDATE / 'history/scripts/v0106_rain_comparison.py'
source = p.read_text()
anchor = 'ROOT = Path(__file__).resolve().parents[2]'
assert source.count(anchor) == 1
source = source.replace(anchor, f'ROOT = Path({str(ROOT)!r})')
ns = {'__file__': str(p), '__name__': '__main__'}
with contextlib.redirect_stdout(io.StringIO()) as captured:
    exec(compile(source, str(p), 'exec'), ns)
expected = (CANDIDATE / 'history/reports/2026-09-24-v0.10.6-rain-comparison.txt').read_text()
assert expected.startswith(captured.getvalue().rstrip())
five = ns['cd'][ns['cd'].event != '2025-10-30']
band = ns['df'][ns['df'].bay_v5 < 3]
out['rain_comparison'] = {
    'parts_B_C_D_reproduce': True,
    'five_other_events_as_coded': {
        k: round(float(five[k].abs().mean()), 6)
        for k in ['baybias_v5', 'baybias_v6', 'err_v5', 'err_v6']},
    'center_bay_below_3': {
        'n': len(band), 'unchanged_peaks': int((band.d_peak_in == 0).sum()),
        'minimum_peak_change_in': float(band.d_peak_in.min())},
    'sep13_partial_input_result': ns['res'],
    'interpretation': 'Not a complete as-issued flood-skill comparison; see round 03.'}

old = subprocess.check_output(['git', 'show', '2c65a971a:data/labeled_observations.csv'], cwd=ROOT)
new = subprocess.check_output(['git', 'show', 'fd30bba7f:data/labeled_observations.csv'], cwd=ROOT)
assert new.startswith(old)
out['oct30_ledger_correction'] = {'prefix_preserved': True,
                                  'lines_added': len(new[len(old):].splitlines())}
print(json.dumps(out, indent=2))
