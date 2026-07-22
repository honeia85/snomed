#!/usr/bin/env python
"""Canonical pooled error-incidence odds ratio (NARROW vs EXACT top-1 error).

Reports the Mantel-Haenszel OR stratified by the 14 system x benchmark cells
(the estimator declared in Methods, *Statistical analysis*), with a
MENTION-CLUSTERED bootstrap 95% CI that resamples evaluation mentions within
each benchmark (a mention recurs across the systems, so mention-level rather
than mention x system resampling gives honest, wider intervals).

Run:  python pooled_incidence_or.py
Reads the deposited per-mention outputs (oracle candidate space) for all five
systems and prints the point estimate + CI used in the manuscript.
"""
import csv, os, random

HERE = os.path.dirname(os.path.abspath(__file__))
PM = os.path.join(HERE, "..", "per_mention")   # deposited per-mention outputs
SYS = ["lexical", "sapbert", "sapbert_ft", "llm_rerank", "llm_gen"]
BEN = ["distemist", "medprocner", "symptemist"]
B_ITER = 10000
SEED = 12345


def load(b, s):
    f = os.path.join(PM, f"{b}_oracle_{s}_per_mention.csv")
    if not os.path.exists(f):
        return None
    return [(r["semantic_rel"], int(r["exact"])) for r in csv.DictReader(open(f))]


def main():
    data = {b: {s: load(b, s) for s in SYS if load(b, s) is not None} for b in BEN}

    def counts(rows, idx):
        a = b = c = d = 0
        it = rows if idx is None else (rows[i] for i in idx)
        for strat, ex in it:
            err = ex == 0
            if strat == "NARROW":
                a, b = (a + 1, b) if err else (a, b + 1)
            else:
                c, d = (c + 1, d) if err else (c, d + 1)
        return a, b, c, d

    def estimate(idxmap):
        A = B = C = D = 0.0
        num = den = 0.0
        for bench in BEN:
            idx = None if idxmap is None else idxmap[bench]
            for s, rows in data[bench].items():
                a, b, c, d = counts(rows, idx)
                A, B, C, D = A + a, B + b, C + c, D + d
                n = a + b + c + d
                if n:
                    num += a * d / n
                    den += b * c / n
        marginal = (A * D) / (B * C) if B * C else float("nan")
        mh = num / den if den else float("nan")
        return marginal, mh

    marg0, mh0 = estimate(None)
    rng = random.Random(SEED)
    lens = {b: len(next(iter(data[b].values()))) for b in BEN}
    margs, mhs = [], []
    for _ in range(B_ITER):
        idxmap = {b: [rng.randrange(lens[b]) for _ in range(lens[b])] for b in BEN}
        m, h = estimate(idxmap)
        margs.append(m); mhs.append(h)
    margs.sort(); mhs.sort()
    lo = lambda x: x[int(0.025 * len(x))]
    hi = lambda x: x[int(0.975 * len(x))]
    print(f"n mentions: DisTEMIST 678, MedProcNER 625, SympTEMIST 800 (14 cells)")
    print(f"Mantel-Haenszel pooled incidence OR = {mh0:.3f}  "
          f"(mention-clustered 95% CI {lo(mhs):.2f}-{hi(mhs):.2f}, B={B_ITER}, seed={SEED})")
    print(f"[for reference] crude collapsed marginal OR = {marg0:.3f}  "
          f"(mention-clustered 95% CI {lo(margs):.2f}-{hi(margs):.2f}) "
          f"-- lower than MH because the OR is non-collapsible")


if __name__ == "__main__":
    main()
