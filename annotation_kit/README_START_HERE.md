# Granularity annotation kit: public identifier-free release

This folder separates the reusable task mechanics from licensed study content. The HTML app contains
two synthetic demonstration rows. It does **not** contain the study's 150 mention texts, English
glosses, terminology identifiers or concept descriptions.

## Reuse the template

1. Read `RUBRIC.md`.
2. In a private, locally authorized copy of `annotation_app.html`, replace the synthetic `ITEMS`
   array with the items for your study. Use release-local IDs rather than terminology identifiers in
   exported labels.
3. Give every rater the same blinded item set. Use study-issued rater IDs; do not ask for names.
4. Collect CSVs locally or configure a secured backend under your institution's policy.
5. Freeze all rater labels before revealing the reference labels.

## Reproduce this study's agreement statistics

The public study outputs are deliberately content-free:

- `reference/annotation_answer_key.csv`: 150 release-local item IDs, benchmark and native corpus
  reference labels, balanced at 25 EXACT and 25 NARROW items within each benchmark;
- `results/human_labels_deidentified.csv`: three pseudonymous raters × 150 items;
- `results/score_output.txt`: frozen scorer output;
- `score_multi_annotator.py`: agreement scorer.

Run from the repository root:

```bash
python3 annotation_kit/score_multi_annotator.py \
  annotation_kit/results/human_labels_deidentified.csv \
  annotation_kit/reference/annotation_answer_key.csv
```

The released labels contain no rater names, notes, timestamps, mention text, translations,
terminology identifiers or concept descriptions.

## Files

| file | role |
|---|---|
| `annotation_app.html` | generic browser template with synthetic rows |
| `RUBRIC.md` | generic EXACT/NARROW definition |
| `reference/annotation_answer_key.csv` | identifier-free native corpus reference labels |
| `results/` | deidentified three-rater matrix, provenance and frozen output |
| `score_human_iaa.py` | single-rater reference-agreement scorer |
| `score_multi_annotator.py` | multi-rater, Fleiss and consensus scorer |
| `google_sheets_collector.gs` | optional unauthenticated demonstration backend; harden before use |
| `COLLECTION_SETUP.md` | security caveats and setup notes for the demonstration backend |
