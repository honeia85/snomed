# Additional analyses

Code for the analyses added for the *Journal of Biomedical Semantics* submission.

| script | what it computes | runs from this deposit? |
|---|---|---|
| `robustness_analyses.py` | bootstrap intervals for the NARROW/EXACT credit-gap ratio; Breslow–Day homogeneity of the pooled odds ratio across benchmarks within system; the ontology-availability restriction of the incidence contrast | partly — the ratio intervals and Breslow–Day tests need only the identifier-free per-mention rows; the availability restriction additionally needs the gold concepts and the frozen is-a graph, which SNOMED CT licensing prevents us from redistributing |
| `M3_label_noise.py` | consensus-vs-reference misclassification matrix on the 150-mention sample and its matrix-method propagation through the pooled odds and risk ratios | yes — uses the deposited three-rater and reference labels |
| `M2_adjusted_incidence.py` | modified-Poisson model of exact-match error on the granularity label, adjusted for mention length, gold-code training frequency, candidate-space density and depth, clustered on source document (SympTEMIST) | no — needs the corpus annotation offsets, which are obtained from the publicly available SympTEMIST release |
| `N8_semantic_rel_values.py` | census of the `semantic_rel` values the three corpora carry, and how many rows each contributed | yes, with network access — downloads the cited corpus releases |

**Paths.** These scripts were written against the authors' working tree and resolve inputs
relative to it. Before running them from a clone, point the input paths at
`data/canonical_run/` in this repository. Every quantity they produce is also deposited as a
result file, so the outputs can be checked without re-running anything.
