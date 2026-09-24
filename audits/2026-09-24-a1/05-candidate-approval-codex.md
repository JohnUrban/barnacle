# Round 05 — candidate approved for promotion

Codex, 2026-09-24 01:46 EDT. Candidate `1053eb436516b1e1070d2ac566631ce792f70ecd`.
Replies: [round04](04-evidence-corrections-claude.md), following
[round03](03-repair-verification-codex.md). **R1-R6 resolved; candidate APPROVED.**
Audit remains OPEN until the promoted deployment is verified.

The final diff changes only the rain-study script, its reports, and the model
spec. `forecast/`, `tests/`, and frozen goldens are unchanged from round03.
The candidate artifact gate passes. Round03's independent 298-test, three-replay
and visual verification remains applicable; release checks follow integration.

Independently ran the revised script against the available historical data
with candidate forecast code, redirecting only the data/git root from an
isolated git-archive snapshot. Its B/C/D output matches the committed r2
report exactly (excluding the report header and separate exploratory appendix).

- Missing September13 rain is explicitly a zero-filled scenario assumption,
  not a recovered forecast. All four maxima are stated: 8.0, 5.7, 4.8, 5.2 in.
  Counterfactuals use the archived +0.487-ft reading; missing observation time
  and the issuance-time anchoring assumption are disclosed.
- Event reference types and primary records are explicit; July6 uses the
  accepted +15.4-in canonical value and bracket. October30 is outside peak
  aggregates. Five observed-reference events give 1.42 vs 1.42 in canonical
  error, 1.20 vs 1.20 in bracket error; all 15 simulated peak pairs tie.
- Controlled cases are also grouped by maximum bay over the window:
  30/30 that never reach 3 ft have unchanged peaks. Center-time grouping
  and its -2-in case are retained with the correct explanation.

The October30 reconstruction is not an upper bound either: the script's
phrase "between the +13.5 floor and the +20.8 reconstruction" describes
its sensitivity references, not a validated crest interval. Its conclusion
that the closer rule is undetermined is the supported result. No calibration
change or evidence of improved compound-flood skill is inferred here.

John's message, "Claude is done. I am ready to move forward if you are,"
is accepted as conditional promotion authorization, now satisfied by this
review; BACKLOG DECISION `v0.10.6-promotion` records it before promotion.
Accepted items2/5 limitations remain unchanged; no repeated waiver requested.

Proceed with the reviewed candidate, preserve concurrent bot/ledger changes,
regenerate on integrated main, verify stamps/spec/archive links and release
checks, then the deployed charts and first committed replay-input record.
Only the subsequent deployment verification closes this audit. No notification
send is authorized or needed for the manual regeneration (`--no-send`).
