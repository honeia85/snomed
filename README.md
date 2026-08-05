# A Granularity Blind Spot in the Evaluation of SNOMED CT Concept Normalization

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21803815.svg)](https://doi.org/10.5281/zenodo.21803815)

Code and identifier-free analysis data for:

> Jo Y, Nam Y, Kim Y, Kim E, Hong P. **A Granularity Blind Spot in the Evaluation of
> SNOMED CT Concept Normalization.** Manuscript prepared for submission to
> *Journal of Biomedical Semantics*, 2026.

Exact-match accuracy treats a terminology as a flat list of codes. This repository contains
identifier-free scored outputs and analysis code behind our finding that benchmark mismatch is
concentrated on mentions that native corpus annotators marked as more specific than their assigned target.
Systems failed to reproduce those targets more often, whereas the estimated conditional-proximity
difference was small and its confidence interval included zero overall despite different directions
across benchmarks.

## Quick start

After modifying release files, regenerate and verify the checksum inventory with
`python3 code/build_manifest.py` and `shasum -a 256 -c MANIFEST.sha256`.

Python 3.10 or newer is recommended.

```bash
python3 -m pip install -r requirements.txt
python3 data/canonical_run/canonical/pooled_incidence_rr.py   # primary effect measure
python3 data/canonical_run/canonical/pooled_incidence_or.py
python3 data/canonical_run/canonical/reproduce_canonical.py
python3 data/canonical_run/canonical/same_lineage_sensitivity.py
python3 data/canonical_run/canonical/conditional_proximity_by_benchmark.py
python3 annotation_kit/score_multi_annotator.py \
  annotation_kit/results/human_labels_deidentified.csv \
  annotation_kit/reference/annotation_answer_key.csv
```

The five canonical checks run from the repository root on a CPU and do not rerun model inference or
need ontology content. They print the pooled Mantel–Haenszel risk ratio 1.725 (mention-clustered 95% CI 1.63–1.83), which is
the manuscript's primary effect measure, the pooled Mantel–Haenszel OR 3.886 (95% CI 3.33–4.56) and
the per-system ORs 2.77/5.54/3.57/3.39/5.42, the geometric-mean decomposition 1.812 × 1.031,
and the binary same-lineage sensitivity (positive NARROW-minus-EXACT uplift in 9/14 cells;
bootstrap 95% CI excluding zero in 6/14). They also reproduce the conditional-proximity
difference—mean Wu–Palmer credit among NARROW errors minus that among EXACT errors—after first
estimating it within each system×benchmark cell and then weighting cells equally: +0.007 (95% CI
−0.022 to +0.037) overall, +0.018 (−0.038 to +0.073) for DisTEMIST, −0.086 (−0.131 to −0.041) for
MedProcNER and +0.071 (+0.024 to +0.119) for SympTEMIST.

## Release contents

```text
code/                                  licensed-user map builder, scorer and analysis utilities
data/canonical_run/per_mention/        28 identifier-free oracle/training-only per-item files
data/canonical_run/canonical/          tables, statistics and core reproduction scripts
data/external_audit/                   identifier-free xMEN rows and aggregate external audits
data/ontology/FROZEN_MAP_HASHES.sha256 verification hashes; no ontology objects
annotation_kit/                        generic app/rubric, ID-free labels and agreement scorers
figures/                               five main and six supplementary figures, 300 dpi or higher
```

The 28 canonical CSVs use the schema:

```text
benchmark,candidate_space,system,item_id,semantic_rel,exact,is_a,wup,relation_type
```

`item_id` is a release-local identifier shared across systems for the same benchmark row.
`candidate_space=train` denotes the training-only sensitivity space. `relation_type` is one of
`exact`, `ancestor`, `descendant`, `sibling` or `unresolved`. No mention text, prediction/reference
identifier, identifier-linked description record or ontology map is included.

These rows support recalculation of the Spanish-benchmark score and relation summaries, the credit-gap
table, the decomposition and the pooled incidence analysis. Recall@5 remains available only in the
deposited aggregate tables because ranked candidate lists are not redistributed. The rows do not
support public re-derivation of Wu–Palmer scores from the original identifier pairs. A licensed user
may use the map-building and scoring utilities on independently obtained source data; a later live
terminology build may differ from the private frozen analysis object.

## Identifier-free release boundary

The complete source corpora and identifier-linked study objects are not redistributed. The public
tree excludes terminology identifiers, identifier-linked description records, ancestor/depth maps,
caches and the 150-item annotation text/gloss collection. Figure 1 reproduces one
manuscript-disclosed worked example without ontology identifiers or release-local row keys; that
single visual example is not included as reusable annotation data. Verification digests of the
private frozen maps are retained in `data/ontology/FROZEN_MAP_HASHES.sha256`. See
`NOTICE_SNOMED.md`.

The source corpora remain available from their original distributors:

| resource | source |
|---|---|
| DisTEMIST | https://doi.org/10.5281/zenodo.6408476 |
| MedProcNER / ProcTEMIST | https://doi.org/10.5281/zenodo.7929830 |
| SympTEMIST | https://doi.org/10.5281/zenodo.8413866 |
| MedMentions | https://github.com/chanzuckerberg/MedMentions |

## Licensed-user map generation

Users with an applicable licence may build ontology objects in their own authorized environment:

```bash
python3 code/build_ontology_ols4.py --codes all_codes.txt --out private_ontology.json
```

Generated identifiers, identifier-linked descriptions, maps and caches are intentionally ignored by
the repository.
This release records the private frozen-object hashes but does not interpret OLS metadata as an
official RF2 edition date or promise a bit-identical live rebuild.

## Human annotation kit

`annotation_kit/annotation_app.html` is a generic browser template containing synthetic
demonstration rows only. The completed study is represented by 150 release-local reference labels
and a three-rater deidentified label matrix. It contains no real mention text, translations, concept
descriptions, rater names, notes or timestamps. See `annotation_kit/README_START_HERE.md`.

## Selected claim map

| manuscript claim | source |
|---|---|
| Table 1 overall scores (manuscript Table 1) | `data/canonical_run/canonical/table2_overall.csv` (historical filename) |
| credit gaps (manuscript Table 2) | `data/canonical_run/canonical/table3_creditgap.csv` (historical filename) |
| pooled OR 3.89 (3.33–4.56) | `data/canonical_run/canonical/pooled_incidence_or.py` |
| pooled MH risk ratio 1.72 (95% CI 1.63–1.83), I² 92.4% | `data/canonical_run/canonical/pooled_incidence_rr.py` |
| per-system ORs | `data/canonical_run/canonical/extra_stats.json` |
| incidence 1.81 × proximity 1.03 | `data/canonical_run/canonical/decomposition.csv` |
| geometric-mean gap ratio 1.87 (95% CI 1.71–2.05) | `data/additional_analyses/robustness_analyses_summary.json` |
| equal-cell conditional-proximity differences overall and by benchmark | `data/canonical_run/canonical/conditional_proximity_by_benchmark.py`, `conditional_proximity_by_benchmark.csv` |
| binary same-lineage sensitivity | `data/canonical_run/canonical/is_a_sensitivity.csv`, `same_lineage_sensitivity.py` |
| oracle/training-only sensitivity | `data/canonical_run/candidate_space_bootstrap.csv` |
| relation composition | `data/canonical_run/canonical/relation_type.csv` |
| metric robustness | `data/canonical_run/canonical/metric_robustness.json` |
| xMEN audits | `data/external_audit/xmen_overall.csv`, `xmen_byrel.csv`, `medmentions_xmen_scored.csv` |
| participant graph-resolvable ratios 2.84–3.20 | `data/external_audit/ieeta_rescored_committed.csv` |
| three-rater agreement | `annotation_kit/results/` |

## Interpretation boundaries

The evaluated systems are baselines, not leaderboard claims. MedMentions uses a depth proxy rather
than native-corpus granularity labels. Hierarchy-aware proximity locates an error in the ontology; it does
not establish clinical correctness or safety.

## Citation and licence

See `CITATION.cff`, `LICENSE` and `THIRD_PARTY_NOTICES.md`. Source code is MIT licensed.
Author-generated identifier-free data, labels, figures and documentation are CC BY 4.0. No licence
is granted here to SNOMED CT content or quoted third-party material; `NOTICE_SNOMED.md` defines that
boundary. Versioned GitHub Releases are archived through Zenodo. The concept DOI
https://doi.org/10.5281/zenodo.21803815 resolves to the latest release; cite the version-specific DOI
shown on that record. Version 1.0.7 corrects rater-role terminology and documentation without changing
data, code behavior or reported results. Earlier tags remain available as version history.

## Contact

Pa Hong (papa.hong@samsung.com), corresponding author.
