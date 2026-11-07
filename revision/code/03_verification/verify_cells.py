#!/usr/bin/env python3
"""Recompute per-cell statistics from the shipped per-item scores.

Prints, for each of the 28 cells, the counts and scores that the manuscript reports in
Tables 2-5 and in supplementary tables S11-S12. Nothing is compared with a stored copy:
the printed values are for the reader to compare with the published table.

Inputs : code/04_ci/primary/inputs/predictions/*.csv  (no mention text, no concept codes)
Output : stdout, one row per cell
"""
import csv, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SCORES = os.path.join(ROOT, "code", "04_ci", "primary", "inputs", "scores.csv")

def main():
    if not os.path.exists(SCORES):
        raise SystemExit("per-item scores not found: " + SCORES)
    by_cell = {}
    with open(SCORES, newline="") as fh:
        for row in csv.DictReader(fh):
            by_cell.setdefault(row["cell"], []).append(row)
    if not by_cell:
        raise SystemExit("no rows in " + SCORES)
    print("file,space,system,n_EXACT,err_EXACT,n_NARROW,err_NARROW,"
          "rate_EXACT,rate_NARROW,mean_wup_EXACT,mean_wup_NARROW,G_EXACT,G_NARROW,risk_ratio")
    for f in sorted(by_cell, key=lambda c: c + "_per_mention.csv"):
        rows = by_cell[f]
        space = rows[0]["candidate_space"]; system = rows[0]["system"]
        out = {}
        for rel in ("EXACT", "NARROW"):
            sub = [r for r in rows if r["semantic_rel"] == rel]
            n = len(sub)
            err = sum(1 for r in sub if float(r["exact"]) == 0)
            wup = statistics.fmean(float(r["wup"]) for r in sub) if n else float("nan")
            acc = statistics.fmean(float(r["exact"]) for r in sub) if n else float("nan")
            out[rel] = (n, err, wup, wup - acc)
        rr = (out["NARROW"][1] / out["NARROW"][0]) / (out["EXACT"][1] / out["EXACT"][0])
        print(",".join([
            f, space, system,
            str(out["EXACT"][0]), str(out["EXACT"][1]),
            str(out["NARROW"][0]), str(out["NARROW"][1]),
            f"{out['EXACT'][1]/out['EXACT'][0]:.6f}", f"{out['NARROW'][1]/out['NARROW'][0]:.6f}",
            f"{out['EXACT'][2]:.6f}", f"{out['NARROW'][2]:.6f}",
            f"{out['EXACT'][3]:.6f}", f"{out['NARROW'][3]:.6f}",
            f"{rr:.6f}"]))

if __name__ == "__main__":
    main()
