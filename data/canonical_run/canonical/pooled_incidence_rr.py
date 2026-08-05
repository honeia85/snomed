#!/usr/bin/env python
"""Canonical pooled error-incidence RISK RATIO (NARROW vs EXACT top-1 error).

Companion to `pooled_incidence_or.py`, and reported as the PRIMARY effect
measure in the manuscript: baseline error rates vary widely across systems
(roughly 0.23-0.97), so the odds ratio is strongly non-collapsible and
overstates the ratio a reader would compute from the error rates themselves.

Interval estimation matches `pooled_incidence_or.py` exactly: a MENTION-
CLUSTERED bootstrap that resamples evaluation mentions within each benchmark.
A mention recurs across the five systems, so the 14 system x benchmark strata
are NOT independent; a closed-form stratified variance (e.g. Greenland-Robins)
assumes they are and yields an interval roughly 1.6x too narrow on the log
scale here. The clustered bootstrap is the honest estimator and is the one the
manuscript quotes.

Because the per-cell risk ratios are strongly heterogeneous, the script also
prints Cochran's Q, I-squared and a DerSimonian-Laird random-effects estimate
so that the fixed-effect pooling is not read as a homogeneity claim. Those
three use conventional inverse-variance weights and are descriptive only: the
14 cells re-score three mention samples, so part of the dispersion they
capture is between-system behaviour on identical mentions.

Run:  python pooled_incidence_rr.py
Reads the deposited per-mention outputs (oracle candidate space) for all five
systems. Needs no ontology content and no model inference.
"""
import csv, math, os, random

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

    def cells(idxmap):
        """(a, n1, c, n0) per stratum; a/c are NARROW/EXACT error counts."""
        out = []
        for bench in BEN:
            idx = None if idxmap is None else idxmap[bench]
            for rows in data[bench].values():
                it = rows if idx is None else (rows[i] for i in idx)
                a = n1 = c = n0 = 0
                for strat, ex in it:
                    err = ex == 0
                    if strat == "NARROW":
                        n1 += 1; a += err
                    elif strat == "EXACT":
                        n0 += 1; c += err
                out.append((a, n1, c, n0))
        return out

    def geomean(cs):
        ls = [math.log((a / n1) / (c / n0)) for a, n1, c, n0 in cs if a and c and n1 and n0]
        return math.exp(sum(ls) / len(ls)) if ls else float("nan")

    def mh_rr(cs):
        num = sum(a * n0 / (n1 + n0) for a, n1, c, n0 in cs if n1 and n0)
        den = sum(c * n1 / (n1 + n0) for a, n1, c, n0 in cs if n1 and n0)
        return num / den if den else float("nan")

    base = cells(None)
    rr = mh_rr(base)

    # ---- mention-clustered bootstrap (identical scheme to pooled_incidence_or.py)
    rng = random.Random(SEED)
    lens = {b: len(next(iter(data[b].values()))) for b in BEN}
    idxmaps = [{b: [rng.randrange(lens[b]) for _ in range(lens[b])] for b in BEN}
               for _ in range(B_ITER)]
    boot = [mh_rr(cells(m)) for m in idxmaps]
    boot.sort()
    lo, hi = boot[int(0.025 * B_ITER)], boot[int(0.975 * B_ITER)]

    # ---- same bootstrap draws, geometric mean of the per-cell ratios
    #      (the quantity the credit-gap decomposition factorizes through)
    gboot = sorted(g for g in (geomean(cells(m)) for m in idxmaps) if g == g)
    glo, ghi = gboot[int(0.025 * len(gboot))], gboot[int(0.975 * len(gboot))]

    # ---- heterogeneity across the 14 strata
    ws, ys = [], []
    for a, n1, c, n0 in base:
        if a and c and n1 and n0:
            y = math.log((a / n1) / (c / n0))
            v = 1.0 / a - 1.0 / n1 + 1.0 / c - 1.0 / n0
            ys.append(y); ws.append(1.0 / v)
    yfix = sum(w * y for w, y in zip(ws, ys)) / sum(ws)
    Q = sum(w * (y - yfix) ** 2 for w, y in zip(ws, ys))
    df = len(ys) - 1
    I2 = max(0.0, (Q - df) / Q) * 100 if Q > 0 else 0.0
    C = sum(ws) - sum(w * w for w in ws) / sum(ws)
    tau2 = max(0.0, (Q - df) / C) if C > 0 else 0.0
    wr = [1.0 / (1.0 / w + tau2) for w in ws]
    yre = sum(w * y for w, y in zip(wr, ys)) / sum(wr)
    sre = math.sqrt(1.0 / sum(wr))

    print(f"{'benchmark':11s} {'system':11s} {'EXACT err':>12s} {'NARROW err':>13s} {'ratio':>7s}")
    i = 0
    for bench in BEN:
        for s in data[bench]:
            a, n1, c, n0 = base[i]; i += 1
            print(f"{bench:11s} {s:11s} {c:5d}/{n0:<6d} {a:5d}/{n1:<7d} {(a/n1)/(c/n0):7.2f}")
    print()
    print(f"Mantel-Haenszel pooled RISK RATIO = {rr:.4f}  "
          f"(mention-clustered 95% CI {lo:.2f}-{hi:.2f}, B={B_ITER}, seed={SEED})")
    print(f"heterogeneity across the 14 strata: Q = {Q:.1f} on {df} df, I2 = {I2:.1f}%")
    print(f"DerSimonian-Laird random-effects RR = {math.exp(yre):.2f} "
          f"({math.exp(yre - 1.96 * sre):.2f}-{math.exp(yre + 1.96 * sre):.2f})")
    gm = geomean(base)
    print(f"geometric mean of per-cell ratios   = {gm:.4f} "
          f"(mention-clustered 95% CI {glo:.2f}-{ghi:.2f})   [decomposition input]")


if __name__ == "__main__":
    main()
