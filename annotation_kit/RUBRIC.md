# Granularity-relation annotation rubric: EXACT vs NARROW

## Task

For each locally supplied item, judge the granularity relation between the clinical mention and its
assigned target concept. Record `EXACT` or `NARROW`. Judge specificity only: do not judge whether the
target is correct, whether a better target exists, or whether the mention span was selected well.

## Labels

- `NARROW`: the mention is more specific than the assigned target. It adds information that the
  broader target lacks, such as laterality, subtype, site, severity, acuity, cause, time course or
  multiplicity.
- `EXACT`: the mention and target are at the same level of specificity, including synonyms and
  clinically equivalent wording.

Decision shortcut: if the mention is not more specific than the target, choose `EXACT`. There is no
`BROAD` category in this two-label task.

## Generic worked examples

| mention | assigned target | label | reason |
|---|---|---|---|
| example symptom | example symptom | `EXACT` | Same information and specificity. |
| left-sided example symptom | example symptom | `NARROW` | The mention adds laterality. |
| chronic example condition | example condition | `NARROW` | The mention adds time course. |

For composite mentions, ask whether the assigned target captures the specificity of the whole
mention. If genuinely unsure, make the best binary judgment and use a private study note if the
protocol permits one.

## Public-template boundary

The released HTML contains synthetic demonstration rows only. It does not contain the study's real
mentions, translations, terminology identifiers or concept descriptions. A study lead must insert
locally authorized items and keep the reference labels hidden until annotation is complete.
