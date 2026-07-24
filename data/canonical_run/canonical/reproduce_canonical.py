#!/usr/bin/env python
"""Regenerate the canonical headline tables/statistics from the deposited identifier-free
per-item outputs, so every core number in the paper is reproducible — not just deposited.

Run from anywhere:  python reproduce_canonical.py
Reads  ../per_mention/<benchmark>_oracle_<system>_per_mention.csv. Each row stores
release-local item metadata plus precomputed semantic_rel, exact, is_a, wup and
relation_type fields; no ontology identifiers or descriptions are required. Prints and re-derives:
  * Table 1 (exact/is-a/Wu-Palmer per system)          -> historical file table2_overall.csv
  * Table 2 (per-stratum credit gap + NARROW/EXACT ratio)
    -> historical filename table3_creditgap.csv
  * binary same-lineage sensitivity by stratum       -> is_a_sensitivity.csv
  * decomposition (per-cell incidence OR, conditional proximity) -> decomposition.csv
  * per-system Mantel-Haenszel incidence OR (extra_stats.json)
  * geometric-mean incidence x proximity
The pooled OR + mention-clustered CI is in the companion pooled_incidence_or.py.
Compare the printed values against the deposited csv/json in this directory.
"""
import csv, os, math
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
PM = os.path.join(HERE, "..", "per_mention")
SYS = ["lexical", "sapbert", "sapbert_ft", "llm_rerank", "llm_gen"]
BEN = ["distemist", "medprocner", "symptemist"]
ABBR = {"distemist": "DisTEMIST", "medprocner": "MedProcNER", "symptemist": "SympTEMIST"}

def load_pm(b, s):
    f = os.path.join(PM, f"{b}_oracle_{s}_per_mention.csv")
    if not os.path.exists(f):
        return None
    return list(csv.DictReader(open(f)))


def main():
    t2, t3, isa_sens, decomp, per_sys_or = [], [], [], [], {}
    inc_ratios, prox_ratios = [], []
    for b in BEN:
        num_or, den_or = defaultdict(float), defaultdict(float)  # for per-system MH (single benchmark trivial)
        for s in SYS:
            rows = load_pm(b, s)
            if rows is None:
                continue
            n = len(rows)
            ex = sum(int(r["exact"]) for r in rows) / n
            wup = sum(float(r["wup"]) for r in rows) / n
            isav = sum(int(r["is_a"]) for r in rows) / n
            t2.append(dict(benchmark=ABBR[b], system=s, n=n, exact=round(ex, 3), isa=round(isav, 3), wup=round(wup, 3)))
            # per-stratum gap
            g, isa_mean, isa_uplift = {}, {}, {}
            cell = {"aN": 0, "bN": 0, "cE": 0, "dE": 0}  # a=NARROW err, b=NARROW ok, c=EXACT err, d=EXACT ok
            wsumErrN = wsumErrE = nErrN = nErrE = 0.0
            for st in ("EXACT", "NARROW"):
                sub = [r for r in rows if r["semantic_rel"] == st]
                if not sub:
                    continue
                gexact = sum(int(r["exact"]) for r in sub) / len(sub)
                gwup = sum(float(r["wup"]) for r in sub) / len(sub)
                gisa = sum(int(r["is_a"]) for r in sub) / len(sub)
                g[st] = gwup - gexact
                isa_mean[st] = gisa
                isa_uplift[st] = gisa - gexact
            for r in rows:
                err = int(r["exact"]) == 0
                if r["semantic_rel"] == "NARROW":
                    cell["aN"] += err; cell["bN"] += (not err)
                    if err: wsumErrN += float(r["wup"]); nErrN += 1
                else:
                    cell["cE"] += err; cell["dE"] += (not err)
                    if err: wsumErrE += float(r["wup"]); nErrE += 1
            ratio = g["NARROW"] / g["EXACT"] if g.get("EXACT") else float("nan")
            t3.append(dict(benchmark=ABBR[b], system=s, gap_EXACT=round(g["EXACT"], 3),
                           gap_NARROW=round(g["NARROW"], 3), ratio=round(ratio, 3)))
            isa_sens.append(dict(
                benchmark=ABBR[b], system=s,
                n_EXACT=sum(r["semantic_rel"] == "EXACT" for r in rows),
                n_NARROW=sum(r["semantic_rel"] == "NARROW" for r in rows),
                isa_EXACT=round(isa_mean["EXACT"], 6),
                isa_NARROW=round(isa_mean["NARROW"], 6),
                uplift_EXACT=round(isa_uplift["EXACT"], 6),
                uplift_NARROW=round(isa_uplift["NARROW"], 6),
                delta_uplift=round(isa_uplift["NARROW"] - isa_uplift["EXACT"], 6),
            ))
            a, bb, c, d = cell["aN"], cell["bN"], cell["cE"], cell["dE"]
            OR = (a * d) / (bb * c) if bb * c else float("nan")
            per_sys_or.setdefault(s, []).append((a, bb, c, d))
            pErrN = a / (a + bb) if (a + bb) else 0
            pErrE = c / (c + d) if (c + d) else 0
            inc = pErrN / pErrE if pErrE else float("nan")
            proxN = wsumErrN / nErrN if nErrN else 0
            proxE = wsumErrE / nErrE if nErrE else 0
            prox = proxN / proxE if proxE else float("nan")
            decomp.append(dict(benchmark=ABBR[b], system=s, incidence_OR=round(OR, 3),
                               incidence_ratio=round(inc, 3), condWuP_NARROW=round(proxN, 3),
                               condWuP_EXACT=round(proxE, 3), proximity_ratio=round(prox, 3)))
            inc_ratios.append(inc); prox_ratios.append(prox)

    # per-system Mantel-Haenszel OR across benchmarks
    mh = {}
    for s, cells in per_sys_or.items():
        numv = sum(a * d / (a + b + c + d) for a, b, c, d in cells)
        denv = sum(b * c / (a + b + c + d) for a, b, c, d in cells)
        mh[s] = round(numv / denv, 2) if denv else None
    gm = lambda xs: math.exp(sum(math.log(x) for x in xs if x == x) / len([x for x in xs if x == x]))

    print("=== Table 1 (overall exact/is-a/Wu-Palmer; historical file table2_overall.csv) ===")
    for r in t2:
        print(f"  {r['benchmark']:11} {r['system']:11} n={r['n']:3d} exact={r['exact']:.3f} is-a={r['isa']:.3f} wup={r['wup']:.3f}")
    print("\n=== Table 2 (per-system credit gap; historical file table3_creditgap.csv) ===")
    for r in t3:
        print(f"  {r['benchmark']:11} {r['system']:11} gapE={r['gap_EXACT']:.3f} gapN={r['gap_NARROW']:.3f} ratio={r['ratio']}")
    print("\n=== binary same-lineage sensitivity (is_a_sensitivity.csv) ===")
    for r in isa_sens:
        print(f"  {r['benchmark']:11} {r['system']:11} is-a_E={r['isa_EXACT']:.3f} "
              f"is-a_N={r['isa_NARROW']:.3f} uplift_E={r['uplift_EXACT']:.3f} "
              f"uplift_N={r['uplift_NARROW']:.3f} delta={r['delta_uplift']:+.3f}")
    print("\n=== per-cell incidence/proximity decomposition ===")
    for r in decomp:
        print(f"  {r['benchmark']:11} {r['system']:11} incidence_ratio={r['incidence_ratio']:.3f} "
              f"incidence_OR={r['incidence_OR']:.3f} condWuP_E={r['condWuP_EXACT']:.3f} "
              f"condWuP_N={r['condWuP_NARROW']:.3f} proximity_ratio={r['proximity_ratio']:.3f}")
    print("\n=== per-system Mantel-Haenszel incidence OR ===")
    print("  " + " ".join(f"{s}={mh[s]}" for s in SYS if s in mh))
    print(f"\n=== geometric means: incidence {gm(inc_ratios):.3f} x proximity {gm(prox_ratios):.3f} ===")
    print("Compare against deposited table2_overall.csv, table3_creditgap.csv, is_a_sensitivity.csv, decomposition.csv and extra_stats.json in this directory.")


if __name__ == "__main__":
    main()
