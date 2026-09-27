# Owner clarification and earlier same-date observations

Author: Codex (GPT-6), 2026-09-27. **Supplement by the original audit author;
NOT the required independent reply. Audit remains OPEN.** The next responder
should use index 03 or the next unused index.

John confirms both September 26 and September 27 morning floods exceeded
October 30, 2025, the former witnessed benchmark: the first two instances of
garage entry, flooding the whole garage on September 26 and about 90% on
September 27. [Exact statement](../../assets/observations/2026-09-27/owner-ranking-followup.txt).
This is direct owner evidence `[STATED]`, supplementing the existing tape peaks;
it does not establish an exact garage elevation or change October's reconstructed
peak into a measured value. The current archive index and all three event
READMEs now identify the superseded benchmark. Historical narratives remain.

**Earlier precedent confirmed:** [May 30](../../assets/observations/2026-05-30/README.md)
explicitly documents AM and PM high tides in one date directory. The AM check
is dry and the PM report concerns post-peak flooding evidence; it is not two
quantitatively measured flood crests. [September 13](../../assets/observations/2026-09-13/flood-measurements.txt)
documents two flood rounds, rain then compound, in one dated notes file.
Thus date folders did not historically guarantee one tide or one flood.

These narrative distinctions do not solve the daily-max consumer limitation
found in R3. The proposed registry should include historical multi-episode
dates, not only September 26. Preserve date paths and assign date-scoped
episode IDs; do not renumber storm aliases or move linked images blindly.
No folder migration or event-registry implementation is included in this update.

John offered original notes. Suggested destinations are in the new
[archive index](../../assets/observations/README.md); originals have not yet
been received or compared. Keep the retrospective captures alongside the
originals with clear provenance, then reconcile rather than overwrite them.

Additional R5 follow-up: historical-ranking prose in
`forecast/flood_forecast_daily.py` (around line 5520 at the reviewed commit)
still calls October 30 a worst *measured* event. That source wording needs
correction in the reviewed surface-repair work; frozen model references and
historical calibration anchors should remain intact. This documentation update
does not claim that generated website copy has been repaired.

Recording-time self-correction: Codex initially appended this retrospective
clarification using `_station_local_now().isoformat()`, which is naive. An
additional `landmark_key=none` metadata row supplies the offset through
`parse_station_local_time()`; the original row is retained under the append-only
rule. Neither row is a new flood-time measurement. This reinforces R6: callers
must normalize the helper's result before persisting it.
