#!/usr/bin/env python3
"""Descriptive agreement audit for the corpus granularity labels.

Three study-author annotators, blinded to the corpus label and system outputs, re-labelled a
fixed 150-mention sample. The sample was selected within benchmark after stratifying on the
observed corpus label (25 EXACT and 25 NARROW per benchmark). It therefore supports a
descriptive reproducibility audit, but its unweighted confusion matrix cannot be transported
as a population sensitivity/specificity matrix. The study-author consensus is also not an
error-free reference standard. For those reasons this script does not correct the pooled
incidence estimates for label misclassification.

Run: python3 M3_label_noise.py
"""

import csv
import json
import os
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPOSITORY = os.path.abspath(os.path.join(HERE, "..", ".."))
RATERS = os.path.join(REPOSITORY, "annotation_kit", "results", "human_labels_deidentified.csv")
KEY = os.path.join(REPOSITORY, "annotation_kit", "reference", "annotation_answer_key.csv")
OUT = os.path.join(REPOSITORY, "data", "additional_analyses", "M3_label_noise.json")


def consensus_vs_corpus():
    by_item = defaultdict(dict)
    with open(RATERS) as fh:
        for row in csv.DictReader(fh):
            by_item[row["item_id"]][row["rater_id"]] = row["annotator_label"].strip().upper()
    native = {}
    with open(KEY) as fh:
        for row in csv.DictReader(fh):
            item = row.get("row_id") or row["item_id"]
            label = row.get("original_label") or row["reference_label"]
            native[item] = label.strip().upper()

    rows = []
    for item, labels in sorted(by_item.items()):
        if item not in native:
            continue
        votes = Counter(labels.values())
        top, n_top = votes.most_common(1)[0]
        if len(votes) > 1 and votes.most_common(2)[1][1] == n_top:
            continue
        rows.append((item, native[item], top, len(labels)))
    return rows


def cohen_kappa(nn, ne, en, ee):
    total = nn + ne + en + ee
    observed = (nn + ee) / total
    expected = (((nn + ne) * (nn + en)) + ((en + ee) * (ne + ee))) / total**2
    return (observed - expected) / (1.0 - expected)


if __name__ == "__main__":
    rows = consensus_vs_corpus()
    assert len(rows) == 150, f"expected 150 items, matched {len(rows)}"
    assert all(n == 3 for *_, n in rows), "expected three raters on every item"

    cm = Counter((native, consensus) for _, native, consensus, _ in rows)
    nn, ne = cm[("NARROW", "NARROW")], cm[("NARROW", "EXACT")]
    en, ee = cm[("EXACT", "NARROW")], cm[("EXACT", "EXACT")]
    agreement = (nn + ee) / len(rows)
    kappa = cohen_kappa(nn, ne, en, ee)
    narrow_confirmation = nn / (nn + ne)
    exact_confirmation = ee / (en + ee)

    print("corpus label (rows) vs three-rater majority consensus (columns)")
    print("                 consensus NARROW   consensus EXACT")
    print(f"  corpus NARROW  {nn:>16d}   {ne:>15d}")
    print(f"  corpus EXACT   {en:>16d}   {ee:>15d}")
    print(f"  raw agreement  {agreement:.3f}")
    print(f"  Cohen's kappa  {kappa:.3f}")
    print("  no population misclassification correction was estimated")

    output = {
        "analysis_role": "descriptive agreement audit",
        "n_items": len(rows),
        "sampling_design": "25 corpus-EXACT and 25 corpus-NARROW mentions per benchmark",
        "confusion_corpus_by_consensus": {
            "NARROW_NARROW": nn,
            "NARROW_EXACT": ne,
            "EXACT_NARROW": en,
            "EXACT_EXACT": ee,
        },
        "raw_agreement": round(agreement, 3),
        "cohen_kappa": round(kappa, 3),
        "consensus_confirmation_within_corpus_NARROW": round(narrow_confirmation, 3),
        "consensus_confirmation_within_corpus_EXACT": round(exact_confirmation, 3),
        "population_effect_correction_performed": False,
        "reason_no_correction": (
            "The sample was balanced on the observed corpus label, so the unweighted matrix "
            "does not estimate population operating characteristics; study-author consensus "
            "is also not an error-free reference standard."
        ),
    }
    with open(OUT, "w") as fh:
        json.dump(output, fh, indent=2)
        fh.write("\n")
    print(f"wrote {OUT}")
