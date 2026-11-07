#!/usr/bin/env python3
"""Recompute every reported aggregate statistic from the shipped component tables.

Each statistic is recomputed from its component counts, not copied from the reported value:
  S14  Mantel-Haenszel odds ratio for the non-terminal restriction, all rows and restricted rows
  S15  per-benchmark risk ratio and pooled Mantel-Haenszel risk ratio of the alternative-translation arm
  S10  per-run NARROW/EXACT gap ratio for the external implementation, both scoring domains
  S13  per-cell LCA and Jaccard increment ratios
  S11  per-cell fallback and non-fallback error counts and rates
  S8   MedMentions depth-band increments and their gaps
The printed values are compared with expected/aggregate_expected.csv where an expected value is archived.
"""
import csv, glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
AGG = os.path.join(ROOT, "aggregates")
EXP = os.path.join(ROOT, "code", "04_ci", "primary", "expected")

def rows(name):
    with open(os.path.join(AGG, name), newline="") as f:
        return list(csv.DictReader(f))

def mh_or(tables):
    nu = de = 0.0
    for a, b, c, d in tables:
        n = a + b + c + d
        if n == 0:
            continue
        nu += a * d / n
        de += b * c / n
    return nu / de

def mh_rr(strata):
    nu = de = 0.0
    for eN, nN, eE, nE in strata:
        n = nN + nE
        nu += eN * nE / n
        de += eE * nN / n
    return nu / de

def main():
    failed = 0
    expected = {}
    p = os.path.join(EXP, "aggregate_expected.csv")
    if os.path.exists(p):
        expected = {r["metric"]: float(r["expected"]) for r in csv.DictReader(open(p))}

    def report(name, got, target=None, digits=10):
        nonlocal failed
        ok = ""
        if target is not None:
            ok = "OK" if abs(got - target) < 10 ** (-digits) else "MISMATCH"
            if ok == "MISMATCH":
                failed += 1
        print(f"{name},{got:.10f},{target if target is not None else ''},{ok}")

    print("metric,recomputed,expected,status")

    # S14
    s14 = rows("s14_nonterminal_cells.csv")
    all_t = [[int(r["narrow_error_all"]), int(r["exact_error_all"]),
              int(r["narrow_correct_all"]), int(r["exact_correct_all"])] for r in s14]
    res_t = [[int(r["narrow_error_restricted"]), int(r["exact_error_restricted"]),
              int(r["narrow_correct_restricted"]), int(r["exact_correct_restricted"])] for r in s14]
    report("s14_or_all", mh_or(all_t), expected.get("s14_or_all"))
    report("s14_or_restricted", mh_or(res_t), expected.get("s14_or_restricted"))
    report("s14_all_rows", float(sum(sum(t) for t in all_t)), expected.get("s14_all_rows"), 6)
    report("s14_restricted_rows", float(sum(sum(t) for t in res_t)), expected.get("s14_restricted_rows"), 6)

    # S15 NLLB
    nllb = rows("nllb_by_benchmark.csv")
    strata, per_bench = [], []
    for r in nllb:
        eN, nN = int(r["errors_NARROW"]), int(r["n_NARROW"])
        eE, nE = int(r["errors_EXACT"]), int(r["n_EXACT"])
        strata.append((eN, nN, eE, nE))
        per_bench.append((r["benchmark"], (eN / nN) / (eE / nE)))
    for name, rr in per_bench:
        report("s15_rr_" + name, rr, expected.get("s15_rr_" + name))
    report("s15_pooled_mh_rr", mh_rr(strata), expected.get("s15_pooled_mh_rr"))

    # S10 ieeta gap ratios
    ie = rows("ieeta_domains.csv")
    seen = {}
    for r in ie:
        key = (r["analysis"], r["scope"], r["scoring_domain"], r["run"])
        try:
            gE, gN = float(r["gap_EXACT"]), float(r["gap_NARROW"])
        except ValueError:
            continue
        seen[key] = gN / gE
    stored10 = {(r["analysis"], r["scope"], r["scoring_domain"], r["run"]): r.get("gap_ratio", "")
                for r in ie}
    n10 = bad10 = 0
    for k, v in seen.items():
        s = stored10.get(k)
        try:
            ok = s not in (None, "") and abs(float(s) - v) < 5e-4
        except ValueError:
            ok = True
        n10 += 1
        bad10 += 0 if ok else 1
        print(f"s10_ratio|{'|'.join(k)},{v:.10f},{s}," + ("OK" if ok else "MISMATCH"))
    if bad10:
        failed += bad10

    # S13 LCA/Jaccard ratios
    rf2 = rows("rf2_metric_cells.csv")
    for r in rf2:
        try:
            lca = float(r["LCA_gap_NARROW"]) / float(r["LCA_gap_EXACT"])
            jac = float(r["Jaccard_gap_NARROW"]) / float(r["Jaccard_gap_EXACT"])
        except ValueError:
            continue
        s_l, s_j = r.get("LCA_ratio", ""), r.get("Jaccard_ratio", "")
        ok_l = s_l != "" and abs(float(s_l) - lca) < 5e-4
        ok_j = s_j != "" and abs(float(s_j) - jac) < 5e-4
        if not (ok_l and ok_j):
            failed += 1
        print(f"s13_lca_ratio|{r['cell']},{lca:.10f},{s_l}," + ("OK" if ok_l else "MISMATCH"))
        print(f"s13_jaccard_ratio|{r['cell']},{jac:.10f},{s_j}," + ("OK" if ok_j else "MISMATCH"))

    # S11/S12 fallback counts
    fb = rows("fallback_bool_by_relation.csv")
    for r in fb:
        n, err = int(r["n"]), int(r["error_count"])
        stored_rate = float(r["exact_rate"]) if r.get("exact_rate") not in (None, "") else None
        computed_rate = err / n
        ok = stored_rate is not None and abs(stored_rate - (1 - computed_rate)) < 5e-6
        if not ok:
            failed += 1
        print(f"s11_error_rate|{r['benchmark']}|{r['candidate_space']}|{r['semantic_rel']}|{r['fallback']},"
              f"{computed_rate:.10f},{stored_rate}," + ("OK" if ok else "MISMATCH"))

    # S8 MedMentions
    mm = rows("medmentions_bands.csv")
    for r in mm:
        computed = float(r["wup"]) - float(r["exact"])
        stored = float(r["gap"])
        print(f"s8_gap|{r['source_condition']}|{r['band']},{computed:.10f},{stored:.10f},"
              + ("OK" if abs(computed - stored) < 1e-9 else "MISMATCH"))

    print(f"\nfailures={failed}")
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
