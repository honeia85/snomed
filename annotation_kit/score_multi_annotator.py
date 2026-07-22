#!/usr/bin/env python3
"""Aggregate + score a MULTI-annotator granularity study (EXACT vs NARROW).

Usage:
    python score_multi_annotator.py collected.csv annotation_answer_key.csv

`collected.csv` is long format (one row per rater x item), as exported from an annotation
tool or concatenated from per-rater CSVs. Required columns:
    rater_id, item_id, annotator_label   (benchmark optional; notes/timestamps ignored)
Legacy `annotator` and `row_id` column names are also accepted.

Reports agreement statistics; Cohen and consensus kappa include bootstrap 95% CIs,
whereas Fleiss' kappa is a point estimate:
  * per-annotator  human-vs-reference Cohen's kappa (overall + per benchmark)
  * human-human agreement: pairwise Cohen's kappa (each pair) + Fleiss' kappa (all raters)
  * majority-vote consensus label, and consensus-vs-reference kappa
The reference vector contains the 150 native shared-task corpus labels.
"""
import sys, itertools, numpy as np, pandas as pd
from sklearn.metrics import cohen_kappa_score

def kci(a,b,nb=5000,seed=42):
    a=np.asarray(a);b=np.asarray(b);k=cohen_kappa_score(a,b)
    rng=np.random.default_rng(seed);n=len(a);boot=[]
    for _ in range(nb):
        idx=rng.integers(0,n,n)
        if len(set(a[idx]))<2 or len(set(b[idx]))<2: continue
        boot.append(cohen_kappa_score(a[idx],b[idx]))
    if not boot: return k,float('nan'),float('nan')
    lo,hi=np.percentile(boot,[2.5,97.5]);return k,lo,hi

def fleiss(mat):
    # mat: n_items x n_categories counts
    n,k=mat.shape; N=mat.sum(axis=1)[0]
    p=mat.sum(axis=0)/(n*N)
    P=((mat**2).sum(axis=1)-N)/(N*(N-1))
    Pbar=P.mean(); Pe=(p**2).sum()
    return (Pbar-Pe)/(1-Pe) if (1-Pe)>0 else float('nan')

def norm(s): return s.astype(str).str.strip().str.upper()

def main(collected, key_csv):
    d=pd.read_csv(collected); key=pd.read_csv(key_csv)
    d.columns=[c.strip().lower() for c in d.columns]
    d=d.rename(columns={"label":"annotator_label","annotator":"rater_id","row_id":"item_id"})
    key=key.rename(columns={"row_id":"item_id","original_label":"reference_label",
                            "match_note":"reference_basis"})
    d["annotator_label"]=norm(d["annotator_label"])
    d=d[d["annotator_label"].isin(["EXACT","NARROW"])]
    key["reference_label"]=norm(key["reference_label"])
    ref=key.set_index("item_id")["reference_label"]
    benchmark=key.set_index("item_id")["benchmark"] if "benchmark" in key.columns else None
    annotators=sorted(d["rater_id"].unique())
    print(f"annotators ({len(annotators)}): {', '.join(map(str,annotators))}")

    # per-annotator vs reference
    wide={}
    for a in annotators:
        sub=d[d["rater_id"]==a].drop_duplicates("item_id").set_index("item_id")["annotator_label"]
        wide[a]=sub
        m=pd.DataFrame({"h":sub,"r":ref}).dropna()
        kk,lo,hi=kci(m["r"],m["h"]); ag=(m["r"]==m["h"]).mean()
        print(f"\n[{a}] vs reference  n={len(m)}  kappa={kk:.3f} [{lo:.3f},{hi:.3f}]  agree={ag*100:.1f}%")
        if benchmark is not None:
            for name in sorted(benchmark.dropna().unique()):
                mb=m[benchmark.reindex(m.index)==name]
                if len(mb)>=10 and mb["r"].nunique()>1 and mb["h"].nunique()>1:
                    kb,lb,hb=kci(mb["r"],mb["h"]); ab=(mb["r"]==mb["h"]).mean()
                    print(f"      {name}: n={len(mb)} kappa={kb:.3f} [{lb:.3f},{hb:.3f}] agree={ab*100:.1f}%")

    W=pd.DataFrame(wide).dropna()
    if len(annotators)>=2 and len(W)>0:
        print(f"\n=== human-human agreement (n={len(W)} rows all raters answered) ===")
        for a,b in itertools.combinations(annotators,2):
            kk,lo,hi=kci(W[a],W[b]); print(f"  pairwise Cohen  {a} vs {b}: kappa={kk:.3f} [{lo:.3f},{hi:.3f}]")
        cats=["EXACT","NARROW"]
        mat=np.array([[ (W.loc[i]==c).sum() for c in cats] for i in W.index])
        print(f"  Fleiss' kappa (all {len(annotators)} raters): {fleiss(mat):.3f}")
        # majority vote consensus
        maj=W.mode(axis=1)[0]
        mm=pd.DataFrame({"h":maj,"r":ref.reindex(W.index)}).dropna()
        kk,lo,hi=kci(mm["r"],mm["h"]); print(f"  majority-vote consensus vs reference: kappa={kk:.3f} [{lo:.3f},{hi:.3f}]  (n={len(mm)})")

if __name__=="__main__":
    main(sys.argv[1], sys.argv[2])
