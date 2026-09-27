# Originals received, episode IDs assigned, comparison refreshed

Codex (GPT-6), 2026-09-27. **Implementation supplement by the audit author,
not an independent reply. Audit remains OPEN; next responder uses index04.**

John approved unique episode IDs and `e01/`, `e02/` subfolders, supplied three
original note files, and requested an updated all-anchors figure. He further
clarified that October 30's remembered magnitude was affected by the surprise
of a first flood experience; photos were after the peak. Both measured September
morning floods were higher. The exact follow-up is preserved and logged as
retrospective metadata, not a new flood-time observation.

## Completed within that scope

- [Original-note reconciliation](../../assets/observations/2026-09-27/analysis/README.md):
  all 80 nonempty lines accounted for as timestamp-mapped entries or context;
  byte hashes retained, no original wording changed, no duplicate water rows.
  Time ranges, an AM/PM typo and untimed gate visits are explicit. Imported
  originals contain no credentials/contact details requiring redaction; photos
  have not been supplied or published in this work.
- [Episode index](../../assets/observations/EPISODES.md) and
  [registry](../../assets/observations/episodes.json): 27 archive records,
  including negative checks and reconstructions; this is not a count of
  measured floods. Every existing non-metadata ledger row at the indexed
  cutoff is associated once by content hash. May19 retention is linked to
  May18; Aug29 residue to Aug27, as their own notes state. Metadata rows are
  explicitly excluded. Date-scoped IDs never get renumbered; storm IDs/aliases
  remain separate. Existing linked files were not moved.
- Every indexed episode has an `eNN/README.md` home. Dates point to their
  episodes; future episode-specific photos belong in the episode folder.
- [Updated PNG](../../assets/observations/2026-09-27/analysis/all_anchors.png),
  PDF, renderer and source/value receipt: thirteen comparison entries, including
  both second floods, evidence types visibly distinguished, no fabricated new
  hindcasts. October 30 is reconstructed; December19 is an observation-time
  bracket; August7 includes inferred crest timing/height. Historical fit
  constants and goldens remain unchanged.

## Still open

The registry is a source index, not a stealth replacement for production or
Heron's statistical grouping. The daily-max site still needs episode-aware
display work; as-issued pairing, gauge/Battery QC, gate/rain attribution,
timestamp repairs, transport/publication isolation and public-source wording
remain under R2–R7. Photos and independent review remain pending.

Review the new registry associations and figure receipts independently. Do not
equate R1's improved provenance with completion of the scientific event study.
Run `python3 history/scripts/check_observation_episodes.py`; it verifies IDs,
aliases, paths, row hashes, coverage and metadata exclusion without changing data.
