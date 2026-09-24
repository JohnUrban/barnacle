# Round 08 — post-close correction: seven-day continuous chart failed to render

2026-09-23. John reported the blank top plot immediately after round 07.
Codex reproduced the failure in both committed and public outlook.html.

**Confirmed defect and audit miss.** The data and canvas were present, but
Python consumed the escape before the apostrophe in the JavaScript label
`Burst scenario at this hour's tide`. The emitted JavaScript put that text in
single quotes without escaping the apostrophe: Node and browsers reject the
whole continuous-chart script with `SyntaxError: Unexpected identifier 's'`.
The separate lower high-tide chart script still parsed successfully.

The label change came with round-04 repair `017ab4a63`. Earlier probes parsed
the embedded JSON and checked data, rather than executing the surrounding
JavaScript. Codex's recovery visual check covered the landing chart, not this
outlook chart. Matching deployed bytes to committed bytes likewise proved
identity, not browser execution. The round-07 release close-out therefore missed
this real display regression; its unqualified completeness claim was too broad.
This report preserves that error honestly instead of rewriting round 07.

## Correction and validation

- Use double quotes around the JavaScript label, preserving the intended text.
- Regenerate only docs/outlook.html from the existing forecast JSON. No fresh
  weather acquisition, no version or numerical forecast changes, no ledger or
  alert-state writes. Rule-5(c) display bug fix; model stays v0.10.5.
- `tests/test_outlook_javascript.py` executes every generated inline script in
  Node's VM with a minimal document/Chart constructor. It asserts both chart
  constructors run, carry actual forecast points, and retain the intended label.
  This catches the escaping failure that JSON-only tests missed. It does not
  pretend a constructor stub is visual verification of Chart.js itself.
- Artifact gate and full regression suite run on the completed patch. The live
  page is checked after deployment to confirm the plot visibly renders.

No parallel forecast arm uses this chart's JavaScript label. The landing chart,
widget, maps, email, ntfy and SMS receive no policy/data change. The separate
high-tide chart is covered by the new execution test too.

Release stamping/ledger/replay conclusions from round 07 still hold. This is a
post-close display correction, not a new model or an implementation of v0.10.6.
