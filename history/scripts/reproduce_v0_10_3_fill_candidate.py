#!/usr/bin/env python3
"""Verify the offline v0.10.3 stage-storage continuity candidate.

This command is read-only.  It proves the candidate inversion is equivalent
to adding rain storage above the exact tide-set base volume, verifies frozen
candidate hindcasts, and confirms production remains stamped v0.10.2.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from forecast import flood_forecast_daily as ff  # noqa: E402
from history.scripts import assess_model_v0_11 as assessment  # noqa: E402
from history.scripts import reproduce_v0_10_1 as production  # noqa: E402


CANDIDATE_PATH = REPO_ROOT / "model" / "data" / "v0.10.3-fill-candidate.json"
BUDGETS = (
    0.0, 1e-6, 0.001, 0.01, 0.1, 1.0, 10.0, 100.0, 1_000.0,
    10_000.0, 100_000.0, 500_000.0, 2_000_000.0,
)


def load_candidate() -> dict:
    with CANDIDATE_PATH.open(encoding="utf-8") as handle:
        candidate = json.load(handle)
    if candidate.get("schema_version") != 1:
        raise ValueError("unsupported fill-candidate schema")
    return candidate


def verify_candidate() -> dict:
    candidate = load_candidate()
    if ff.CURRENT_MODEL_VERSION != candidate["production_base_version"]:
        raise AssertionError("offline candidate base no longer matches production")
    if candidate["parameters_changed"]:
        raise AssertionError("fill-only candidate must not change parameters")

    curve = ff._load_stage_curve()
    worst_reference_error = 0.0
    worst_production_correction = 0.0
    for hundredth in range(0, 2401):
        base = hundredth / 100.0
        base_volume = production._volume_at_stage(curve, base)
        for budget in BUDGETS:
            expected = production._stage_at_volume(
                curve, base_volume + budget
            )
            actual = assessment.corrected_pluvial_fill(curve, base, budget)
            worst_reference_error = max(
                worst_reference_error, abs(actual - expected)
            )
            current = ff._pluvial_fill(curve, base, budget)
            worst_production_correction = max(
                worst_production_correction, actual - current
            )
    if worst_reference_error > 1e-10:
        raise AssertionError(
            f"candidate differs from reference inversion by "
            f"{worst_reference_error:.12g} inches"
        )
    expected_correction = candidate["expected_worst_sampled_correction_in"]
    if not math.isclose(
        worst_production_correction,
        expected_correction,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise AssertionError("sampled production correction changed")

    base_fixture = production.load_fixture()
    original = ff._pluvial_fill
    try:
        ff._pluvial_fill = assessment.corrected_pluvial_fill
        hindcasts = production.hindcast_metrics(base_fixture)
    finally:
        ff._pluvial_fill = original
    expected_hindcasts = candidate["expected_hindcasts"]
    if hindcasts.keys() != expected_hindcasts.keys():
        raise AssertionError("candidate hindcast event set changed")
    for event_id, expected in expected_hindcasts.items():
        actual = hindcasts[event_id]
        if actual.keys() != expected.keys():
            raise AssertionError(f"{event_id} candidate field set changed")
        for key, expected_value in expected.items():
            actual_value = actual[key]
            if isinstance(expected_value, float):
                if not math.isclose(
                    actual_value, expected_value, rel_tol=0.0, abs_tol=1e-10
                ):
                    raise AssertionError(f"{event_id} {key} changed")
            elif actual_value != expected_value:
                raise AssertionError(f"{event_id} {key} changed")

    return {
        "candidate_model_version": candidate["candidate_model_version"],
        "production_model_version": ff.CURRENT_MODEL_VERSION,
        "worst_reference_error_in": worst_reference_error,
        "worst_production_correction_in": worst_production_correction,
        "hindcasts": hindcasts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = verify_candidate()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(
            f"{result['candidate_model_version']} fill candidate: reference "
            f"error {result['worst_reference_error_in']:.3g} in; maximum "
            f"production correction "
            f"{result['worst_production_correction_in']:.3f} in"
        )
        for event_id, row in result["hindcasts"].items():
            print(
                f"{event_id:6s}: peak +{row['peak_stage_in']:.3f} in at "
                f"{row['peak_local'][11:16]} local"
            )
        print("verification: PASS (offline candidate; production unchanged)")


if __name__ == "__main__":
    main()
