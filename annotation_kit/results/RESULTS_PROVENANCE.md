# Human annotation results: provenance and reproduction

## Frozen study artifact

The completed three-rater R2 collection was exported from the study's Cloudflare D1 collector on
21 July 2026 in two audit forms: a 450-row long table and an independently preserved 150-row compact
pivot. Before pseudonymization, a local non-networked script verified that the two exports contained
the same complete label vectors for all three raters and all 150 items.

The restricted exports and the source-to-pseudonym mapping are retained by the study team and are not
part of this public package. The public matrix uses only `R1`, `R2`, and `R3`; this numbering is a
release pseudonym and carries no rank or role meaning.

## Public files

- `human_labels_deidentified.csv`: 450 rows with exactly four fields:
  `rater_id,item_id,benchmark,annotator_label`.
- `../reference/annotation_answer_key.csv`: identifier-free reference labels with
  `item_id,benchmark,reference_label,reference_basis`. These are the native shared-task corpus
  labels: 25 EXACT and 25 NARROW items within each benchmark.
- `score_output.txt`: the frozen stdout from the scorer command below.

The public results exclude source annotator identifiers, mention text and spans, SCTIDs, concept
descriptions, free-text notes, and collection timestamps. Item IDs `A001`–`A150` are release-local
identifiers and do not encode source terminology identifiers.

## Reproduce the reported agreement

From the repository root, run:

```bash
python3 annotation_kit/score_multi_annotator.py \
  annotation_kit/results/human_labels_deidentified.csv \
  annotation_kit/reference/annotation_answer_key.csv
```

The frozen run reproduces all reported anchors: each rater answered 150 items; the three NARROW
counts are 53, 72, and 90. Rater-versus-reference Cohen kappa was 0.613 (bootstrap 95% CI
0.480–0.734; 80.7% raw agreement) for R1, 0.627 (0.501–0.742; 81.3%) for R2, and 0.667
(0.544–0.785; 83.3%) for R3. Pairwise Cohen kappa was 0.408 for R1–R2, 0.630 for R1–R3, and
0.555 for R2–R3; Fleiss kappa was 0.519. Majority-vote consensus versus the reference was kappa
0.733 (0.613–0.840). Rater numbering is intentionally not connected to manuscript annotator row
numbers.

`MANIFEST.sha256` records the exact matrix, reference key, scorer, frozen stdout, and this provenance
document used for the release.
