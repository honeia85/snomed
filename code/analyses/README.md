# Additional analyses

Code for the analyses added for the *Journal of Biomedical Semantics* submission.

| script | what it computes | runs from this deposit? |
|---|---|---|
| `robustness_analyses.py` | dependence-preserving bootstrap interval for the geometric-mean NARROW/EXACT credit-gap ratio; exploratory within-system Breslow–Day tests with Holm sensitivity; descendant-availability restriction | partly — ratio intervals and heterogeneity tests run from the identifier-free rows; descendant availability additionally needs gold concepts and the licensed frozen graph |
| `M3_label_noise.py` | descriptive agreement matrix and κ for the balanced 150-mention three-rater sample; no population misclassification correction | yes — uses the deposited three-rater and reference labels |
| `M2_adjusted_incidence.py` | modified-Poisson model of exact-match error on the granularity label, adjusted for mention length, gold-code training frequency, candidate-space density and depth, clustered on source document (SympTEMIST) | no — needs the corpus annotation offsets, which are obtained from the publicly available SympTEMIST release |
| `N8_semantic_rel_values.py` | census of the `semantic_rel` values the three corpora carry, and how many rows each contributed | yes, with network access — downloads all three documented Zenodo releases |

**Paths.** Run `M3_label_noise.py` and the public parts of `robustness_analyses.py` directly from
the repository root. `robustness_analyses.py` reuses the deposited descendant-availability output
when licensed inputs are absent. Authorized users can set `CREDITGAP_SOURCE_ROOT` to the private
source tree containing `08_rerun_colab/` to rerun that component. Every reported output is also
deposited under `data/additional_analyses/`.
