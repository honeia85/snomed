#!/usr/bin/env python3
"""Score the human NARROW/EXACT reproducibility study.

Usage:
    python score_human_iaa.py annotation_sheet_FILLED.csv annotation_answer_key.csv

Expects the filled sheet to have an `annotator_label` column containing
EXACT / NARROW for each item_id, and the answer key to map item_id -> reference_label.
Legacy `row_id` and `original_label` column names are also accepted.
Computes human-vs-reference Cohen's kappa with a bootstrap 95% CI, overall and per benchmark.
"""
import sys, numpy as np, pandas as pd
from sklearn.metrics import cohen_kappa_score

def kappa_ci(a, b, n_boot=5000, seed=42):
    a = np.asarray(a); b = np.asarray(b)
    k = cohen_kappa_score(a, b)
    rng = np.random.default_rng(seed); n = len(a); boots = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        if len(set(a[idx])) < 2 or len(set(b[idx])) < 2:
            continue
        boots.append(cohen_kappa_score(a[idx], b[idx]))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return k, lo, hi

def main(filled_csv, key_csv):
    s = pd.read_csv(filled_csv); k = pd.read_csv(key_csv)
    s = s.rename(columns={"row_id": "item_id", "label": "annotator_label"})
    k = k.rename(columns={"row_id": "item_id", "original_label": "reference_label"})
    m = s.merge(k[["item_id", "benchmark", "reference_label"]], on="item_id", how="left",
                suffixes=("", "_reference"))
    if "benchmark" not in m and "benchmark_reference" in m:
        m["benchmark"] = m["benchmark_reference"]
    m = m.dropna(subset=["annotator_label","reference_label"])
    m["annotator_label"] = m["annotator_label"].str.strip().str.upper()
    m["reference_label"] = m["reference_label"].str.strip().str.upper()
    print(f"scored rows: {len(m)}")
    kk, lo, hi = kappa_ci(m["reference_label"], m["annotator_label"])
    agree = (m["reference_label"] == m["annotator_label"]).mean()
    print(f"OVERALL  human-vs-reference  kappa={kk:.3f}  95% CI [{lo:.3f}, {hi:.3f}]  raw agreement={agree*100:.1f}%")
    for b, sub in m.groupby("benchmark"):
        if len(sub) >= 10 and sub["reference_label"].nunique() > 1:
            kb, lob, hib = kappa_ci(sub["reference_label"], sub["annotator_label"])
            print(f"  {b:11} n={len(sub):3d}  kappa={kb:.3f}  95% CI [{lob:.3f}, {hib:.3f}]")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
