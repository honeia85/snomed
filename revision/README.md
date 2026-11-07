# A Granularity Blind Spot in the Evaluation of SNOMED CT Concept Normalization
## Revision analysis materials (version 1.1.0 target, 2026-11-07)

This archive contains the fixed evaluation panel, the per-item scores, the analysis code and the aggregate
tables used for the revision analyses of the manuscript submitted to the Journal of Biomedical Semantics.
It is a new deposit that accompanies the earlier archive, version 1.0.8, doi:10.5281/zenodo.21805578; that
version holds the annotation instructions and the earlier aggregates, and is not replaced by this one.

Contact: Pa Hong, MD, Department of Radiology, Samsung Changwon Hospital, Sungkyunkwan University School of
Medicine (corresponding author). The journal's peer-review policy states single-anonymous review, so author names are
not anonymised in this deposit.

## 1. Contents

```
code/04_ci/primary/inputs/panel_documents.csv  fixed panel keyed by public item_id and a document-cluster hash
code/04_ci/primary/inputs/scores.csv  per-item scores for the 28 cells in one table (no mention text, no concept codes)
code/02_analysis/                  analysis scripts used for the revision
code/03_verification/verify_cells.py       recomputes the 28 per-cell statistics of Tables 2-5
code/03_verification/recompute_aggregates.py  recomputes every reported aggregate statistic from component counts
code/04_ci/                        script, protocol and inputs that regenerate the confidence intervals
aggregates/                        aggregate tables cited in the manuscript and supplement
requirements.txt                   Python packages; Node.js 20+ for the .mjs scripts
SHA256SUMS.materials               SHA-256 of every file in this archive
```

### 1.1 Panel

`code/04_ci/primary/inputs/panel_documents.csv` columns: `benchmark`, `item_id`, `semantic_rel` (EXACT or NARROW) and
`document_cluster`, a salted hash of the source document. It has 2,103 rows and 245 clusters. Composition of
the initial 800-row draw was DisTEMIST 563 EXACT / 237 NARROW, MedProcNER 666 / 134, SympTEMIST 603 / 197;
unique (mention, gold code) de-duplication leaves 678 / 625 / 800 rows. No mention text, concept code or file
name is included.

### 1.2 Per-item scores

`code/04_ci/primary/inputs/scores.csv` holds one row per evaluated mention for all 28 cells, 19,780 rows, with
columns `cell`, `benchmark`, `candidate_space`, `system`, `item_id`, `semantic_rel`, `exact`, `is_a`, `wup` and
`relation_type`. `cell` is the system-by-benchmark-by-candidate-space key; rows are ordered as in the original
per-cell files so that recomputation follows the same summation order. No mention text, concept code, document text, ontology map or model output log is included:
the predicted and gold concepts appear only as pass/fail and hierarchy scores. These files let a reader recompute each in-house cell in the manuscript and the
supplement without re-running any model.

## 2. Requirements

Python 3.10 or later with the packages in `requirements.txt`; Node.js 20 or later for the `.mjs` scripts
(no npm packages are needed). A GPU is optional and only used by `code/02_analysis/nllb_condition.py`,
which downloads and runs two public checkpoints; that script falls back to CPU. Every other script reads
archived files and recomputes numbers.

## 3. What each script does, and what it needs

All scripts read a base directory that you set at the top of the file as `DATA_ROOT`, plus the inputs listed
below. Paths inside the archive are relative to it.

| script | calls a model? | inputs required |
|---|---|---|
| `code/03_verification/verify_cells.py` | no | `code/04_ci/primary/inputs/scores.csv` only |
| `code/03_verification/recompute_aggregates.py` | no | `aggregates/` only; recomputes the S8, S10, S11, S13, S14 and S15 statistics from their component counts and checks them against `expected/aggregate_expected.csv` |
| `code/02_analysis/fallback_bool_recount.mjs` | no | the archived re-ranker per-item predictions, the stored run dump, and an optional 28-cell gate file |
| `code/02_analysis/nllb_recount.mjs` | no | the archived alternative-translation predictions, translation arrays, stored result JSON, a source manifest, and the two condition scripts `nllb_condition.py` and `rerun_full.py` (`rerun_full.py` is not included here) |
| `code/04_ci/primary/run_primary.sh` | no | the panel, the document mapping and the per-item scores, all included here; regenerates the primary Mantel-Haenszel interval |
| `code/04_ci/reconstructed/run_reconstructed.sh` | no | protocol, matrix and preflight files, all included here; regenerates the reconstructed-panel intervals |
| `code/02_analysis/nllb_condition.py` | **yes** | the reconstructed panel and candidate bundle; downloads `facebook/nllb-200-distilled-600M` and `cambridgeltl/SapBERT-from-PubMedBERT-fulltext` |

Only `nllb_condition.py` calls a model, and a GPU is optional because it falls back to CPU. Every script in
`code/02_analysis/` other than the verification pair needs inputs that are not in this archive, so none of
them will run here as shipped; they are included so that the method can be inspected and repeated by anyone
who obtains the same inputs. What a reader can recompute from this archive alone is the in-house cell set for the three Spanish
benchmarks, using `code/04_ci/primary/inputs/scores.csv` with `aggregates/` and the panel. Everything else is reported as aggregates only.

## 4. What is NOT in this archive, and why

- **SNOMED CT concept maps, node tables and RF2 release files.** Distribution is governed by the SNOMED
  International affiliate licence. No concept code, map, node table or relationship table is distributed in
  this archive; only pass/fail and hierarchy scores are given, so authors who hold a licence can rebuild the
  maps from the release named in the manuscript.
- **Mention text, document text and concept codes.** Only public item identifiers, score columns and salted
  document-cluster hashes are distributed; the corpora and the terminology release are obtained from their own
  distributors.
- **Translation caches and model output logs.** The per-item scores allow the in-house cells of the three
  Spanish benchmarks to be recomputed; the remaining quantities are reported as aggregates only.
- **Participant-level annotation responses and the annotation instructions** are in the earlier archive,
  doi:10.5281/zenodo.21805578, in anonymised form.
- **Third-party participant systems.** The BIT.UA (ieeta-pt) run files carry no licence, so only our
  aggregates over them are reported; we do not redistribute their files.

## 5. Known record limitations

- The numeric seed of the original 800-row draw and its run log were not recovered. The selected panel is
  distributed instead, which is what reproduction requires.
- The weight commit and source-file SHA of the archived model runs were not recorded. Stored outputs are
  reproduced from archived per-item files, not by re-running the models.
- External submitted systems were executed by their own authors, not by us; we analysed their public
  outputs and report the resulting aggregates.
- The document-level clustering identifier is a hash, not the corpus file name. It is stable and sufficient
  to reproduce the resampling intervals, but a reader cannot map it back to a corpus file from this archive
  alone; the hashing used a private salt that is not distributed.
- One script that produced `aggregates/medmentions_bands.csv` needed access to a working archive that is not publicly available and
  is therefore not included. Only its output is given; the MedMentions per-item scores are not in this
  archive, so that table cannot be recomputed here.

## 6. How to check the numbers

`python3 code/03_verification/verify_cells.py` recomputes the per-cell statistics from the shipped scores:
for each of the 28 cells it prints the EXACT and NARROW denominators, the error counts, the two error rates,
the mean WUP, the increment G and the NARROW/EXACT error risk ratio. Those are the quantities printed in
Tables 2-5 and in supplementary tables S11-S12 of the manuscript; the printed values are for direct comparison
with the published table.

`python3 code/03_verification/recompute_aggregates.py` then recomputes the reported aggregate statistics from
their component counts. For S14 and S15 it compares the recomputed value with `expected/aggregate_expected.csv`;
for S8, S10, S11 and S13 it compares the recomputed value with the stored derived column of the same table. It
prints OK or MISMATCH for every checked row and exits non-zero on any mismatch. 111 rows are checked:

- S14 non-terminal restriction: Mantel-Haenszel odds ratio over 14 cells, computed from
  `aggregates/s14_nonterminal_cells.csv` for all rows (3.8863) and for the restricted rows (4.8312), with the
  restricted row total (7,519).
- S15 alternative-translation arm: the three per-benchmark risk ratios and the pooled Mantel-Haenszel risk
  ratio (1.7752), computed from `aggregates/nllb_by_benchmark.csv`.
- S10 external implementation: NARROW/EXACT gap ratio per run and scoring domain, computed from the two gap
  columns of `aggregates/ieeta_domains.csv`.
- S13 and S11: per-cell LCA and Jaccard increment ratios, and the fallback and non-fallback error counts and
  rates, computed from the shipped component columns.
- S8: the MedMentions depth-band increments, computed from `aggregates/medmentions_bands.csv`.

So every reported number can be recomputed from this archive alone: the per-cell statistics from the scores,
the intervals from the scores plus the document clusters, and the aggregate statistics from their component
counts. What is excluded is the licensed terminology content and the third-party run files, which are not
needed to recompute any reported number. The Mantel-Haenszel summaries pool those cells; the reported values are in
`code/04_ci/primary/expected/CI_summary.csv` and `expected/bootstrap_result.json`. Those two files are
comparison targets, not recomputation inputs: the point estimate and intervals are recomputed from the scores
and the document mapping, then compared with them.

The confidence intervals can be regenerated here. Each script compares its own output with the archived
value and exits non-zero on a mismatch:

```
sh code/04_ci/primary/run_primary.sh                # B = 10,000, seed 12345, 245 documents
sh code/04_ci/reconstructed/run_reconstructed.sh    # B = 2,000, seed 42, 246 documents
```

The primary script recomputes the point estimate from the per-item scores (it is not read from a stored
constant) and compares it with the archived value; it also recomputes all 50 interval estimates. The reconstructed script likewise recomputes its three point estimates from the matrix and then computes the
intervals. Both scripts were re-run from this archive while preparing the deposit: the primary point estimate
1.7246375019947953 with the Mantel-Haenszel 95% interval 1.6172-1.8397 and all 50 intervals, and the
reconstructed points 1.5963, 1.6735 and 1.9002 with their intervals, matched the archived values. The
protocol files inside `code/04_ci/` were path-sanitised before release, so their file hash differs from the
archived hash; the reported numbers do not change. Each script prints that note.

## 7. Sanitisation applied before release

The analysis scripts are the ones we ran, with these edits only; no reported value, threshold or filter was
altered:

- Local absolute paths were replaced with the placeholder `DATA_ROOT`.
- Names of working folders and of one working note were replaced with neutral names.
- A local identifier of one input file was replaced with a neutral file name.
- One self-check that compared a local copy of the submitted manuscript against a stored hash was removed,
  as it verifies our record keeping rather than a reported result.
- One script (`medmentions_rescore.mjs`) was withdrawn because it depended on access to a working archive that is not publicly available.
- In one script a 28-cell consistency gate that previously ran unconditionally now runs only when its gate
  file is present. This changes control flow, but not any threshold, filter or reported value.
- File names of intermediate inputs and outputs were replaced with neutral English names.
- The CI protocol and validation files had absolute paths replaced with `DATA_ROOT/...`, the provenance list
  reduced to file names plus SHA-256, and one working-process phrase replaced with a neutral description.
  The driver was re-run afterwards and still reproduces the archived intervals.
- `code/04_ci/*/run_*.sh` and `code/04_ci/primary/inputs/scores.csv` are new files written for this
  deposit; they assemble the working directory and compare the recomputed values with `expected/`.

## 8. Licence

Code files: MIT (see `LICENSE`). Aggregate tables, per-item scores, the document-cluster panel and the
reconstructed-panel matrix: CC BY 4.0 (see `LICENSE-DATA`). The SNOMED CT terminology content itself is not
redistributed.
The corpora remain under their own licences; SNOMED CT identifiers are used under the SNOMED International
affiliate licence and are not redistributed as terminology content.
