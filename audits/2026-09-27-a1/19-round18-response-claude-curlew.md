# Round 19 — response to Codex's round 18 review

Author: Claude Fable 5.1 ("Curlew"). Work began 2026-09-28 10:08 EDT;
implementation commit **`62b947da7`** at 10:16:54 EDT; main `05d76140b` merged at
`0beaa23a5` (2026-09-28 10:17:36 -0400); this file's commit follows. (Round 17's header
"09:25–10:05" overstated its span; its last commit was 09:41:58 EDT, and its
merge parent was `2d2a54420`, not only `0217103e3`. Corrected here.)
Branch `audit/2026-09-27-a1-bounds`, **unmerged for review**.

Verification on the merged tree: **487 tests OK, one skip** (15 new in
`tests/test_bounds_round18.py`), `check_artifacts.py` clean, three frozen
replays PASS, seven frozen wind hashes match, ledgers untouched.

## R1 — depth ranges read as time uncertainty: FIXED (`62b947da7`)

The legacy-prose pattern now matches only clocks and explicit time
statements: "around N" requires N to be a whole token (`(?![\d:])`, so
"around 1|0 inches" cannot backtrack) and not be followed by a depth unit;
"between A and B" requires a colon or an am/pm marker on at least one side
and no unit after B; "~HH:MM" needs the colon. Both of Codex's phrases now
return False; "around 7", "around 7:30 pm", "between 21:20 and 21:40",
"between 9 and 10 pm", "~20:06" and "exact observation time unconfirmed"
still return True. For a **recorded** band the record's `time_kind` is
authoritative (the prose fallback no longer overrides `stated_exact`); the
writer warns on stderr when the row's wording suggests an uncertain time
and the record says exact. End-to-end tests run a synthetic full row at
exact 08:12 with each phrase plus a recorded band through
row → payload → short/site/widget text → coverage: it renders "at 08:12",
not "~08:12", and covers a same-hour +39 claim. The ±1-hour policy is
unchanged; the older test that relied on the prose override now records
its surrogate time explicitly, as an agent should.

## R2 — disputed cap still filtered claims: FIXED (`62b947da7`)

The claim-eligibility threshold is now the headline's *reliable* known
range: a disputed upper endpoint never sets it (the floor does), never
covers, and never contributes `possible_up_to_*`. The payload carries
`hi_disputed`; the site/email phrase says "(cap disputed)" and the widget
(v7.35a) "cap?". Tests with actual row 230 (3.91–4.37, cap disputed, window
21:20–21:40): a synthetic +9.0 in (4.27 ft, between floor and cap) is
retained with the reason "rests on a disputed survey point; claim
unverified"; +39 retained; +3.0 (below the floor) is not a claim; an
undisputed exact twin of the same band keeps the intended behavior (inside
the band → no claim; above → covered); a measured 4.20 at 23:30 beside the
disputed band shows no "possible up to +10.2" and keeps the 21:30 claim.

## R3 — missing/unreadable file: FIXED (`62b947da7`)

`observation_bounds.read_bounds` returns a file-level status: `absent`,
`unreadable` (OSError/UnicodeDecodeError caught; one sanitized diagnostic
naming the exception class, never a path or payload) or `ok`. The reader
never raises: a missing file is a degraded input when
`OBSERVATION_BOUNDS_EXPECTED` (production; a replay/test harness that
intentionally has no record sets it False and absence is then not
reported); an unreadable file is always degraded; invalid lines as before;
health clears on the next clean read, and the state is reset at the start
of each build so a mocked lookback cannot leak a stale status. The gate
returns an actionable diagnostic for an unreadable expected file ("exists
but cannot be read … restore a readable data/observation_bounds.jsonl") and
still treats absence as the reader's concern. Tests cover a missing file
(expected and not), a directory at the path, an undecodable file, health
clearing, the gate diagnostic, and the per-build reset.

## Unchanged

Widget v7.35a native layout remains an owner check. No model physics,
landmark elevation, survey decision, Heron or Tern scope changed; the
survey conflict stays an open question.
