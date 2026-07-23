# A hierarchy-aware evaluation and toolkit for SNOMED CT concept normalization

Code and identifier-free analysis data for:

> Jo Y, Nam Y, Kim Y, Kim E, Hong P. **What exact match hides on fine-grained clinical mentions: a
> hierarchy-aware evaluation and toolkit for SNOMED CT normalization.** Manuscript prepared for
> *Database* (Oxford), 2026.

Exact-match accuracy treats a terminology as a flat list of codes. This repository contains
identifier-free scored outputs and analysis code behind our finding that the resulting loss is
concentrated on mentions that human annotators marked as more specific than their assigned target.
Systems erred more often on those mentions, whereas the estimated conditional-proximity difference
was small and its confidence interval included zero.

## Quick start

Python 3.10 or newer is recommended.

```bash
python3 -m pip install -r requirements.txt
python3 data/canonical_run/canonical/pooled_incidence_or.py
python3 data/canonical_run/canonical/reproduce_canonical.py
python3 annotation_kit/score_multi_annotator.py \
  annotation_kit/results/human_labels_deidentified.csv \
  annotation_kit/reference/annotation_answer_key.csv
```

The two canonical checks run from the repository root on a CPU and do not rerun model inference or
need ontology content. They print the pooled Mantel–Haenszel OR 3.886 (95% CI 3.33–4.56), the
per-system ORs 2.77/5.54/3.57/3.39/5.42, and the geometric-mean decomposition 1.812 × 1.031.

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

These rows support direct recalculation of the reported tables and core statistics. They do not
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

The automated κ = 0.84 reported in the paper is a separate machine re-annotation consistency check;
its raw inference artifacts are not part of this analysis-level release.

## Selected claim map

| manuscript claim | source |
|---|---|
| Table 2 overall scores | `data/canonical_run/canonical/table2_overall.csv` |
| Table 4 credit gaps | `data/canonical_run/canonical/table3_creditgap.csv` |
| pooled OR 3.89 (3.33–4.56) | `data/canonical_run/canonical/pooled_incidence_or.py` |
| per-system ORs | `data/canonical_run/canonical/extra_stats.json` |
| incidence 1.81 × proximity 1.03 | `data/canonical_run/canonical/decomposition.csv` |
| oracle/training-only sensitivity | `data/canonical_run/candidate_space_bootstrap.csv` |
| relation composition | `data/canonical_run/canonical/relation_type.csv` |
| metric robustness | `data/canonical_run/canonical/metric_robustness.json` |
| xMEN audits | `data/external_audit/xmen_overall.csv`, `xmen_byrel.csv`, `medmentions_xmen_scored.csv` |
| participant graph-resolvable ratios 2.84–3.20 | `data/external_audit/ieeta_rescored_committed.csv` |
| three-rater agreement | `annotation_kit/results/` |

## Interpretation boundaries

The evaluated systems are baselines, not leaderboard claims. MedMentions uses a depth proxy rather
than human granularity labels. Hierarchy-aware proximity locates an error in the ontology; it does
not establish clinical correctness or safety.

## Citation and licence

See `CITATION.cff` and `LICENSE`. Source code is MIT licensed. Author-generated identifier-free data,
labels, figures and documentation are CC BY 4.0. No licence is granted here to SNOMED CT content;
`NOTICE_SNOMED.md` defines that boundary. After acceptance and before publication, the accepted GitHub
tag will be archived on Zenodo and its DOI added to the citation metadata.

## Contact

Pa Hong (papa.hong@samsung.com), corresponding author.
