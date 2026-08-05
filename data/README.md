# Data dictionary

All public tables are UTF-8 CSV with a header row unless noted otherwise. This release contains
identifier-free derived metrics and aggregates only.

## `data/canonical_run/per_mention/`

Twenty-eight files named `<benchmark>_<space>_<system>_per_mention.csv` cover 14 system×benchmark
cells under the primary oracle and training-only candidate spaces.

| column | meaning |
|---|---|
| `benchmark` | benchmark display name |
| `candidate_space` | `oracle` or `train` (`train` is the training-only sensitivity space) |
| `system` | evaluated system |
| `item_id` | release-local benchmark item ID, aligned across systems |
| `semantic_rel` | native-corpus granularity stratum, `EXACT` or `NARROW` |
| `exact` | exact-match indicator, 0 or 1 |
| `is_a` | exact or ancestor/descendant consistency indicator, 0 or 1 |
| `wup` | Wu–Palmer credit computed with the private frozen map |
| `relation_type` | `exact`, `ancestor`, `descendant`, `sibling` or `unresolved` |

The files contain no mention text, prediction/reference identifier or identifier-linked concept description. They
recalculate the reported Table 1 exact/is-a/Wu–Palmer columns, credit gaps, decomposition, incidence
results and relation profiles. Recall@5 remains a deposited aggregate rather than a per-item rerun.

## `data/canonical_run/canonical/`

| file | content |
|---|---|
| `table2_overall.csv` | overall performance reported in Table 1; historical filename retained |
| `table3_creditgap.csv` | credit-gap rows reported in Table 2; historical filename retained |
| `decomposition.csv` | per-cell error-incidence and conditional-proximity decomposition |
| `pooled_incidence_rr.py` | primary panel-weighted Mantel–Haenszel risk ratio and mention-resampling CI |
| `pooled_incidence_or.py` | pooled Mantel–Haenszel OR and mention-resampling CI |
| `reproduce_canonical.py` | identifier-free Table 1, Table 2, decomposition and OR recalculation |
| `same_lineage_sensitivity.py` | binary same-lineage sensitivity with synchronized bootstrap |
| `conditional_proximity_by_benchmark.py` | equal-cell conditional-proximity estimates and fixed-stratum bootstrap intervals overall and by benchmark |
| `conditional_proximity_by_benchmark.csv` | frozen overall and benchmark-specific estimates reproduced by the companion script |
| `extra_stats.json` | per-system ORs and other canonical statistics |
| `confirmatory.json` | additive-gap intervals, permutation and McNemar results |
| `relation_type.csv` | relation-type composition by benchmark, system and stratum |
| `proximity_creditshare.json` | sibling credit shares and the pooled LLM-only proximity diagnostic; this is not the current all-cell headline estimand |
| `metric_robustness.json` | four-metric rank checks |
| `medmentions_rescore.json` | MedMentions depth-proxy and Table 1 values |
| `depth_proxy_validation.json` | depth-proxy logistic OR and AUC |
| `pooled_stats.json` | stored pooled-statistic summary |

The five canonical CPU checks are `pooled_incidence_rr.py`, `pooled_incidence_or.py`,
`reproduce_canonical.py`, `same_lineage_sensitivity.py` and
`conditional_proximity_by_benchmark.py`.

Other canonical files provide candidate-space sensitivity, the DisTEMIST seen/ancestor-seen split,
and the provenance map. `score_modal.py` is a licensed-private re-derivation utility; its raw inputs
and locally generated ontology objects are not deposited.

## `data/external_audit/`

`xmen_overall.csv` and `xmen_byrel.csv` contain the aggregate Spanish xMEN audit, while the per-item
`medmentions_xmen_scored.csv` replaces source span and prediction/reference identifiers with
release-local `MM-####` item IDs while retaining derived metric, depth-band and semantic-type fields.
For the participant audit, `ieeta_rescored_committed.csv` is the source for the manuscript and
Supplementary Figure S6 graph-resolvable ratios of 2.84–3.20; `ieeta_medprocner_scored.csv` is an
auxiliary integral/end-to-end score summary and is not the source of those ratios. DisTEMIST and
SympTEMIST have no scoreable participant outputs in this release.

## `data/ontology/`

`FROZEN_MAP_HASHES.sha256` records verification digests for the eight private frozen ancestor/depth
objects. The maps and terminology caches themselves are not distributed and cannot be reconstructed
from the hashes. Licensed users may build current maps with the utilities under `code/`; see
`NOTICE_SNOMED.md` at the repository root.
