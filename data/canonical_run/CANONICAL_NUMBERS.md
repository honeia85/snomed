# Canonical numbers and provenance map

This file identifies the single analysis run behind the submitted manuscript. It contains no
alternate or superseded run. The paper's credit-gap results are in Table 2, although the deposited
file retains its historical name `canonical/table3_creditgap.csv` for provenance.

## Run scope

- Qwen2.5-32B-Instruct revision `5ede1c97` and SapBERT.
- Frozen OLS4 analysis maps retrieved in July 2026.
- Three human-labelled Spanish benchmarks: DisTEMIST (*n* = 678), MedProcNER (*n* = 625) and
  SympTEMIST (*n* = 800).
- Fourteen system×benchmark cells: five DisTEMIST, four MedProcNER and five SympTEMIST.
- Primary oracle candidate space plus a training-only sensitivity space.

The 28 files under `per_mention/` are the identifier-free row-level analysis objects. Each contains
benchmark, candidate-space, system and release-local item metadata plus `semantic_rel`, `exact`,
`is_a`, `wup` and `relation_type`. No terminology identifiers or descriptions are included. The
scripts below read those fields rather than manuscript text or ontology maps.

## Reproduction commands

Run from the repository root:

```bash
python3 data/canonical_run/canonical/pooled_incidence_or.py
python3 data/canonical_run/canonical/reproduce_canonical.py
python3 data/canonical_run/canonical/same_lineage_sensitivity.py
python3 data/canonical_run/canonical/conditional_proximity_by_benchmark.py
```

Expected headline results from these commands and the deposited confirmatory output:

- pooled Mantel–Haenszel error-incidence OR 3.886, 95% CI 3.33–4.56;
- per-system ORs 2.77 / 5.54 / 3.57 / 3.39 / 5.42;
- geometric-mean gap decomposition 1.812 × 1.031;
- NARROW credit gap greater than EXACT in 14/14 cells (recalculated by
  `reproduce_canonical.py`), with the additive-gap interval excluding zero in 13/14 (deposited in
  `canonical/confirmatory.json`; the bootstrap itself is not rerun by the first two commands);
- binary same-lineage uplift greater on NARROW in 9/14 cells, with the synchronized
  fixed-stratum item-bootstrap 95% CI excluding zero in 6/14
  (`canonical/same_lineage_sensitivity.py`, B = 10,000, seed 42);
- equal-cell conditional-proximity difference (mean Wu–Palmer among NARROW errors minus mean
  Wu–Palmer among EXACT errors) +0.007, 95% CI −0.022 to +0.037 across all 14 cells; benchmark
  estimates were +0.018 (−0.038 to +0.073) for DisTEMIST, −0.086 (−0.131 to −0.041) for
  MedProcNER and +0.071 (+0.024 to +0.119) for SympTEMIST
  (`canonical/conditional_proximity_by_benchmark.py`, B = 10,000, seed 42).

## Current Table 1 values

| Benchmark | System | Exact | Is-a | Wu–Palmer | Recall@5 |
|---|---|---:|---:|---:|---:|
| DisTEMIST | lexical | 0.488 | 0.606 | 0.732 | 0.671 |
| DisTEMIST | SapBERT | 0.637 | 0.736 | 0.826 | 0.816 |
| DisTEMIST | SapBERT-ft | 0.677 | 0.785 | 0.857 | 0.873 |
| DisTEMIST | LLM reranker | 0.633 | 0.742 | 0.823 | 0.763 |
| DisTEMIST | LLM generator | 0.301 | 0.422 | 0.559 | — |
| MedProcNER | lexical | 0.443 | 0.603 | 0.761 | 0.691 |
| MedProcNER | SapBERT | 0.642 | 0.747 | 0.847 | 0.845 |
| MedProcNER | LLM reranker | 0.602 | 0.746 | 0.838 | 0.755 |
| MedProcNER | LLM generator | 0.250 | 0.429 | 0.602 | — |
| SympTEMIST | lexical | 0.409 | 0.502 | 0.611 | 0.550 |
| SympTEMIST | SapBERT | 0.584 | 0.639 | 0.741 | 0.748 |
| SympTEMIST | SapBERT-ft | 0.659 | 0.706 | 0.786 | 0.878 |
| SympTEMIST | LLM reranker | 0.551 | 0.621 | 0.700 | 0.634 |
| SympTEMIST | LLM generator | 0.254 | 0.341 | 0.462 | — |

## Claim-to-file map

| claim | canonical source |
|---|---|
| Table 1 overall scores | `canonical/table2_overall.csv` (historical filename) |
| Table 2 credit gaps and intervals | `canonical/table3_creditgap.csv`, `canonical/confirmatory.json` (historical filename) |
| pooled incidence OR and CI | `canonical/pooled_incidence_or.py`, `canonical/pooled_stats.json` |
| per-system incidence ORs | `canonical/extra_stats.json` |
| incidence/proximity decomposition | `canonical/decomposition.csv` |
| equal-cell conditional-proximity differences overall and by benchmark | `canonical/conditional_proximity_by_benchmark.py`, `canonical/conditional_proximity_by_benchmark.csv` |
| binary same-lineage sensitivity | `canonical/is_a_sensitivity.csv`, `canonical/same_lineage_sensitivity.py` |
| relation-type profile | `canonical/relation_type.csv` |
| sibling credit allocation and pooled LLM-only proximity diagnostic | `canonical/proximity_creditshare.json` (`prox_diff_NARROW_minus_EXACT` is the retained NARROW-minus-EXACT field; `prox_diff` is its legacy reverse-sign counterpart) |
| four-metric ranking robustness | `canonical/metric_robustness.json` |
| MedMentions depth-proxy check | `canonical/medmentions_rescore.json` |
| depth-proxy validity | `canonical/depth_proxy_validation.json` |
| oracle versus training-only candidate space | `candidate_space_bootstrap.csv`, `summary_by_space_5sys.csv` |
| code-seen / ancestor-seen / isolated split | `seen_novel_full_distemist.json` |

External xMEN and ieeta-pt checks are separate modules under `../external_audit/`; they are not
treated as independent replications of the canonical run. The three-annotator human reproducibility
study is documented in `annotation_kit/` and is likewise separate from the system-output run.

If a derived summary conflicts with these files, the canonical per-mention rows and the four
reproduction scripts above take precedence.
