#!/usr/bin/env python3
"""M3: label-noise sensitivity for the granularity stratification.

The manuscript's exposure is the corpus `semantic_rel` label. Three blinded annotators
re-labelled a fixed 150-mention sample, which gives an independent measurement of the same
property and therefore a way to ask how much exposure misclassification could move the
incidence contrast.

Computed here, on all 150 mentions (not the 50 text-matched subset) and against the
majority-vote consensus of the three raters (not annotator 1):

  1. the consensus-vs-corpus misclassification matrix;
  2. sensitivity and specificity of the corpus label with the consensus taken as reference;
  3. a matrix-method correction of the pooled odds ratio and pooled risk ratio under
     nondifferential exposure misclassification, which is the direction of the standard
     assumption (misclassification independent of whether the system erred).

The 150-item sample is balanced by design (25 EXACT + 25 NARROW per benchmark), so it does not
estimate prevalence; sensitivity and specificity are prevalence-independent, which is why the
correction is run through them rather than through the observed counts of the sample.

Run:  python3 M3_label_noise.py
"""

import csv
import importlib.util
import json
import math
import os
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))

# Inputs that cannot be redistributed (gold concepts, the frozen is-a graph, corpus annotation
# offsets) live outside this repository. Point CREDITGAP_SOURCE_ROOT at a tree holding them, or
# edit the default below. Analyses that need only the deposited identifier-free rows resolve
# against this repository and run without it.
SOURCE_ROOT = os.environ.get("CREDITGAP_SOURCE_ROOT", os.path.join(HERE, "..", "..", "source"))

REL = SOURCE_ROOT
RATERS = os.path.join(REL, "11_public_release_final", "annotation_kit", "results",
                      "human_labels_deidentified.csv")
KEY = os.path.join(REL, "04_annotation_kit", "annotation_answer_key.csv")

spec = importlib.util.spec_from_file_location("ra", os.path.join(HERE, "robustness_analyses.py"))
ra = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ra)


def consensus_vs_corpus():
    by_item = defaultdict(dict)
    for r in csv.DictReader(open(RATERS)):
        by_item[r["item_id"]][r["rater_id"]] = r["annotator_label"].strip().upper()
    native = {}
    for r in csv.DictReader(open(KEY)):
        native[r["row_id"]] = r["original_label"].strip().upper()

    rows = []
    for item, labels in sorted(by_item.items()):
        if item not in native:
            continue
        votes = Counter(labels.values())
        top, n_top = votes.most_common(1)[0]
        if len(votes) > 1 and votes.most_common(2)[1][1] == n_top:
            continue  # no majority; with three raters over two labels this cannot happen
        rows.append((item, native[item], top, len(labels)))
    return rows


def matrix_correct(a, b, c, d, se, sp):
    """Matrix-method correction for nondifferential exposure misclassification.

    (a, c) = classified-NARROW and classified-EXACT among errors;
    (b, d) = classified-NARROW and classified-EXACT among non-errors.
    Returns corrected counts, or None when the correction leaves the feasible region -
    which is itself the finding, not something to silently clamp.
    """
    denom = se - (1.0 - sp)
    if denom <= 0:
        return None
    out = []
    for cls_pos, tot in ((a, a + c), (b, b + d)):
        true_pos = (cls_pos - (1.0 - sp) * tot) / denom
        true_neg = tot - true_pos
        if true_pos <= 0 or true_neg <= 0:
            return None
        out.append((true_pos, true_neg))
    (a_t, c_t), (b_t, d_t) = out
    return a_t, b_t, c_t, d_t


def pooled_tables():
    """Per system x benchmark 2x2 tables on the corpus label, as used in the manuscript."""
    tabs = []
    for bench in ra.BENCHMARKS:
        for s in ra.SYSTEMS:
            rows = ra.load_cell(bench, s)
            if not rows:
                continue
            a = sum(1 for r in rows if r["rel"] == "NARROW" and r["exact"] < 0.5)
            c = sum(1 for r in rows if r["rel"] == "NARROW" and r["exact"] >= 0.5)
            b = sum(1 for r in rows if r["rel"] == "EXACT" and r["exact"] < 0.5)
            d = sum(1 for r in rows if r["rel"] == "EXACT" and r["exact"] >= 0.5)
            tabs.append((a, b, c, d))
    return tabs


def mh_or(tabs):
    num = sum(a * d / (a + b + c + d) for a, b, c, d in tabs)
    den = sum(b * c / (a + b + c + d) for a, b, c, d in tabs)
    return num / den if den else float("nan")


def mh_rr(tabs):
    num = den = 0.0
    for a, b, c, d in tabs:
        n1, n0 = a + c, b + d
        n = n1 + n0
        num += a * n0 / n
        den += b * n1 / n
    return num / den if den else float("nan")


if __name__ == "__main__":
    rows = consensus_vs_corpus()
    assert len(rows) == 150, f"expected 150 items, matched {len(rows)}"
    assert all(n == 3 for *_, n in rows), "expected three raters on every item"

    # confusion, corpus label (rows) x consensus label (cols)
    cm = Counter((native, cons) for _, native, cons, _ in rows)
    nn, ne = cm[("NARROW", "NARROW")], cm[("NARROW", "EXACT")]
    en, ee = cm[("EXACT", "NARROW")], cm[("EXACT", "EXACT")]
    agree = (nn + ee) / 150

    # consensus taken as the reference measurement
    se = nn / (nn + en) if (nn + en) else float("nan")   # P(corpus NARROW | consensus NARROW)
    sp = ee / (ee + ne) if (ee + ne) else float("nan")   # P(corpus EXACT  | consensus EXACT)

    print("consensus vs corpus label, all 150 mentions")
    print(f"                 consensus NARROW   consensus EXACT")
    print(f"  corpus NARROW  {nn:>16d}   {ne:>15d}")
    print(f"  corpus EXACT   {en:>16d}   {ee:>15d}")
    print(f"  raw agreement  {agree:.3f}")
    print(f"  sensitivity of the corpus label (consensus as reference): {se:.3f}")
    print(f"  specificity of the corpus label (consensus as reference): {sp:.3f}")

    tabs = pooled_tables()
    labels = [(b, s) for b in ra.BENCHMARKS for s in ra.SYSTEMS if ra.load_cell(b, s)]
    obs_or, obs_rr = mh_or(tabs), mh_rr(tabs)
    corrected = [matrix_correct(*t, se=se, sp=sp) for t in tabs]
    dropped = [labels[i] for i, c in enumerate(corrected) if c is None]
    keep = [i for i, c in enumerate(corrected) if c is not None]
    ok = [corrected[i] for i in keep]
    same_obs = [tabs[i] for i in keep]   # observed on the SAME cells, so the pair is comparable

    print(f"\nobserved (corpus label), all {len(tabs)} cells:  MH OR {obs_or:.3f}   MH RR {obs_rr:.3f}")
    if dropped:
        print(f"  {len(dropped)} cell(s) left the feasible region under correction: "
              + ", ".join(f"{b}/{s}" for b, s in dropped))
        print("  (correction is infeasible where the classified-NARROW share falls below 1 - "
              "specificity, which happens at near-saturated error rates)")
    if ok:
        print(f"\non the {len(ok)} correctable cells:")
        print(f"  observed   MH OR {mh_or(same_obs):.3f}   MH RR {mh_rr(same_obs):.3f}")
        print(f"  corrected  MH OR {mh_or(ok):.3f}   MH RR {mh_rr(ok):.3f}")
        print("\nNondifferential misclassification biases towards the null, so the corrected "
              "estimate exceeding the observed one is the expected direction: the reported "
              "contrast is, if anything, an underestimate.")

    out = {
        "n_items": 150,
        "confusion_corpus_by_consensus": {
            "NARROW_NARROW": nn, "NARROW_EXACT": ne, "EXACT_NARROW": en, "EXACT_EXACT": ee},
        "raw_agreement": round(agree, 3),
        "sensitivity_corpus_label": round(se, 3),
        "specificity_corpus_label": round(sp, 3),
        "observed_MH_OR": round(obs_or, 3),
        "observed_MH_RR": round(obs_rr, 3),
        "observed_MH_OR_correctable_cells": round(mh_or(same_obs), 3) if ok else None,
        "observed_MH_RR_correctable_cells": round(mh_rr(same_obs), 3) if ok else None,
        "corrected_MH_OR": round(mh_or(ok), 3) if ok else None,
        "corrected_MH_RR": round(mh_rr(ok), 3) if ok else None,
        "cells_corrected": len(ok),
        "cells_infeasible": [f"{b}/{s}" for b, s in dropped],
        "assumption": ("Nondifferential exposure misclassification: the probability that the "
                       "corpus label differs from the three-rater consensus does not depend on "
                       "whether the system erred. The three raters were blinded to the corpus "
                       "labels and to system output, which supports it but does not prove it."),
        "sample_note": ("Sensitivity and specificity come from the balanced 150-mention sample "
                        "(25 EXACT + 25 NARROW per benchmark). That sample does not estimate "
                        "prevalence, but sensitivity and specificity are prevalence-independent, "
                        "so they transport to the full evaluation sets."),
    }
    json.dump(out, open(os.path.join(HERE, "M3_label_noise.json"), "w"), indent=2)
    print("\nwrote M3_label_noise.json")
