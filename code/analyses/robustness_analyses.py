#!/usr/bin/env python3
"""Three analyses requested by the coauthor (Nam, 2026-07-22) that were deferred at the
Database submission, recomputed here for the JBS resubmission.

  A (Nam 3-3)  Is the NARROW effect an ontology artefact?  Split NARROW/EXACT mentions by
               whether a strictly more specific code even exists for the gold concept, and
               re-estimate the error-incidence contrast inside the "finer code exists" stratum.
  B (Nam 3-4)  Bootstrap CI for the NARROW/EXACT credit-gap ratio (currently reported as a
               bare point estimate in Table 4, Figures 2 and 5 and the abstract).
  C (Nam 3-2)  Heterogeneity of the granularity odds ratio.  Nam asked for Breslow-Day; the
               Database-stage response declined because pooling five systems scored on the
               same mentions violates independence.  Held within one system, benchmarks are
               disjoint mention sets, so the test is legitimate: run it per system across
               benchmarks, which is what the homogeneity assumption of the reported pooled
               MH OR actually rests on.

Inputs are the canonical Modal 5-system run and the frozen OLS4 ontology objects; nothing is
re-scored.  Run from anywhere:  python3 nam_reinforcement.py
"""

import csv
import json
import math
import os
import random
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))

# Inputs that cannot be redistributed (gold concepts, the frozen is-a graph, corpus annotation
# offsets) live outside this repository. Point CREDITGAP_SOURCE_ROOT at a tree holding them, or
# edit the default below. Analyses that need only the deposited identifier-free rows resolve
# against this repository and run without it.
SOURCE_ROOT = os.environ.get("CREDITGAP_SOURCE_ROOT", os.path.join(HERE, "..", "..", "source"))

SRC = os.path.join(SOURCE_ROOT, "08_rerun_colab")
PER_MENTION = os.path.join(SRC, "results_modal_5sys", "per_mention")
CANONICAL = os.path.join(SRC, "results_modal_5sys", "canonical")
ONTO_CACHE = os.path.join(SRC, "results", "ontology_cache")
OUT = HERE

BENCHMARKS = ["distemist", "medprocner", "symptemist"]
SYSTEMS = ["lexical", "sapbert", "sapbert_ft", "llm_rerank", "llm_gen"]
SPACE = "oracle"  # the manuscript's primary candidate space
B_BOOT = 2000
SEED = 20260805


# ---------------------------------------------------------------- data loading

def load_cell(bench, system):
    """Per-mention rows for one benchmark x system cell, or None if the cell does not exist."""
    path = os.path.join(PER_MENTION, f"{bench}_{SPACE}_{system}_per_mention.csv")
    if not os.path.exists(path):
        return None
    rows = []
    with open(path) as fh:
        for r in csv.DictReader(fh):
            rows.append({
                "gold": r["gold"].strip(),
                "rel": r["semantic_rel"].strip().upper(),
                "exact": float(r["exact"]),
                "wup": float(r["wup"]),
            })
    return [r for r in rows if r["rel"] in ("EXACT", "NARROW")]


def load_children(bench):
    """child -> parents is stored; invert it to parent -> children over the frozen universe."""
    with open(os.path.join(ONTO_CACHE, f"{bench}_ols_cache.json")) as fh:
        par = json.load(fh)["par"]
    kids = defaultdict(set)
    for child, parents in par.items():
        for p in parents:
            kids[p].add(child)
    return kids, set(par)


# ---------------------------------------------------------------- small stats

def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def credit_gap(rows):
    """Wu-Palmer-minus-exact credit gap, the manuscript's gap statistic."""
    return mean([r["wup"] - r["exact"] for r in rows])


def err_rate(rows):
    return mean([1.0 - (r["exact"] > 0.5) for r in rows])


def mh_or(tables):
    """Mantel-Haenszel odds ratio over 2x2 tables (a,b,c,d) = (errN, errE, okN, okE)."""
    num = den = 0.0
    for a, b, c, d in tables:
        n = a + b + c + d
        if n == 0:
            continue
        num += a * d / n
        den += b * c / n
    return num / den if den else float("nan")


def chi2_sf(x, df):
    """Upper tail of the chi-square distribution (regularised incomplete gamma, series/CF)."""
    if x <= 0:
        return 1.0
    a, xx = df / 2.0, x / 2.0
    if xx < a + 1.0:  # series
        term = 1.0 / a
        total = term
        n = a
        for _ in range(500):
            n += 1.0
            term *= xx / n
            total += term
            if abs(term) < abs(total) * 1e-14:
                break
        return 1.0 - total * math.exp(-xx + a * math.log(xx) - math.lgamma(a))
    b = xx + 1.0 - a  # continued fraction
    c, d = 1e300, 1.0 / b
    h = d
    for i in range(1, 500):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < 1e-300:
            d = 1e-300
        c = b + an / c
        if abs(c) < 1e-300:
            c = 1e-300
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-14:
            break
    return h * math.exp(-xx + a * math.log(xx) - math.lgamma(a))


def breslow_day(tables, or_common):
    """Breslow-Day homogeneity statistic for a common odds ratio across independent strata."""
    if or_common <= 0 or math.isnan(or_common):
        return float("nan"), float("nan"), 0
    stat = 0.0
    used = 0
    for a, b, c, d in tables:
        n1, n2 = a + c, b + d          # NARROW total, EXACT total
        m1, m2 = a + b, c + d          # error total, correct total
        n = n1 + n2
        if min(n1, n2, m1, m2) == 0:
            continue
        # fitted a under the common OR: solve the quadratic
        A = or_common - 1.0
        Bq = -(or_common * (n1 + m1) + (n2 - m1))
        C = or_common * n1 * m1
        if abs(A) < 1e-12:
            a_fit = n1 * m1 / n
        else:
            disc = Bq * Bq - 4 * A * C
            disc = max(disc, 0.0)
            a_fit = (-Bq - math.sqrt(disc)) / (2 * A)
            if not (max(0.0, m1 - n2) < a_fit < min(n1, m1)):
                a_fit = (-Bq + math.sqrt(disc)) / (2 * A)
        b_fit, c_fit, d_fit = m1 - a_fit, n1 - a_fit, n2 - m1 + a_fit
        if min(a_fit, b_fit, c_fit, d_fit) <= 0:
            continue
        var = 1.0 / (1.0 / a_fit + 1.0 / b_fit + 1.0 / c_fit + 1.0 / d_fit)
        stat += (a - a_fit) ** 2 / var
        used += 1
    df = max(used - 1, 0)
    return stat, (chi2_sf(stat, df) if df else float("nan")), df


def boot_ci(values, lo=2.5, hi=97.5):
    v = sorted(x for x in values if not math.isnan(x) and not math.isinf(x))
    if not v:
        return float("nan"), float("nan")
    def pick(p):
        k = (len(v) - 1) * p / 100.0
        f, c = math.floor(k), math.ceil(k)
        return v[int(f)] if f == c else v[int(f)] * (c - k) + v[int(c)] * (k - f)
    return pick(lo), pick(hi)


def clustered_mh_ci(restrict, B=10000, seed=12345):
    """Mention-clustered bootstrap CI for the pooled MH odds ratio.

    Resamples evaluation mentions within each benchmark and applies the same indices to every
    system, because one mention recurs across systems; mention x system resampling would
    understate the interval. This is the procedure and seed used for the published pooled
    odds ratio, so the restricted estimate is directly comparable to it.
    """
    rng = random.Random(seed)
    data, keep = {}, {}
    for bench in BENCHMARKS:
        cells = {s: load_cell(bench, s) for s in SYSTEMS}
        cells = {s: c for s, c in cells.items() if c}
        data[bench] = cells
        if restrict:
            kids, _ = load_children(bench)
            ref = next(iter(cells.values()))
            keep[bench] = [i for i, r in enumerate(ref) if len(kids.get(r["gold"], ())) > 0]
        else:
            keep[bench] = list(range(len(next(iter(cells.values())))))

    def mh_from(idxmap):
        tables = []
        for bench, cells in data.items():
            idx = idxmap[bench]
            for rows in cells.values():
                a = b = c = d = 0
                for i in idx:
                    r = rows[i]
                    err = r["exact"] < 0.5
                    if r["rel"] == "NARROW":
                        a, c = (a + 1, c) if err else (a, c + 1)
                    else:
                        b, d = (b + 1, d) if err else (b, d + 1)
                tables.append((a, b, c, d))
        return mh_or(tables)

    point = mh_from(keep)
    draws = []
    for _ in range(B):
        idxmap = {bench: [ix[rng.randrange(len(ix))] for _ in range(len(ix))]
                  for bench, ix in keep.items()}
        v = mh_from(idxmap)
        if not math.isnan(v) and not math.isinf(v):
            draws.append(v)
    lo, hi = boot_ci(draws)
    return [round(point, 3), round(lo, 3), round(hi, 3)]


# ---------------------------------------------------------------- A: ontology availability

def analysis_a():
    """Nam 3-3: separate 'no finer code exists' from the granularity label itself."""
    rows_out = []
    coverage = []
    pooled_tables_all, pooled_tables_avail = [], []

    for bench in BENCHMARKS:
        kids, universe = load_children(bench)
        has_finer = {}

        def finer_exists(gold):
            if gold not in has_finer:
                has_finer[gold] = len(kids.get(gold, ())) > 0
            return has_finer[gold]

        # coverage: is the NARROW label just "SNOMED has nothing finer"?
        ref = load_cell(bench, "lexical")
        by_rel = defaultdict(lambda: [0, 0])
        for r in ref:
            slot = by_rel[r["rel"]]
            slot[0] += 1
            slot[1] += 1 if finer_exists(r["gold"]) else 0
        for rel in ("EXACT", "NARROW"):
            n, k = by_rel[rel]
            coverage.append({
                "benchmark": bench, "stratum": rel, "n_mentions": n,
                "n_gold_with_finer_code": k,
                "pct_with_finer_code": round(100.0 * k / n, 1) if n else float("nan"),
                "n_gold_codes_in_universe": len(universe),
            })

        for system in SYSTEMS:
            cell = load_cell(bench, system)
            if cell is None:
                continue
            avail = [r for r in cell if finer_exists(r["gold"])]

            def table(rs):
                a = sum(1 for r in rs if r["rel"] == "NARROW" and r["exact"] < 0.5)
                c = sum(1 for r in rs if r["rel"] == "NARROW" and r["exact"] >= 0.5)
                b = sum(1 for r in rs if r["rel"] == "EXACT" and r["exact"] < 0.5)
                d = sum(1 for r in rs if r["rel"] == "EXACT" and r["exact"] >= 0.5)
                return a, b, c, d

            t_all, t_av = table(cell), table(avail)
            pooled_tables_all.append(t_all)
            pooled_tables_avail.append(t_av)

            def rr(t):
                a, b, c, d = t
                pn = a / (a + c) if a + c else float("nan")
                pe = b / (b + d) if b + d else float("nan")
                return pn, pe, (pn / pe if pe else float("nan"))

            pn_a, pe_a, rr_a = rr(t_all)
            pn_v, pe_v, rr_v = rr(t_av)
            rows_out.append({
                "benchmark": bench, "system": system,
                "n_all": len(cell), "n_finer_code_exists": len(avail),
                "pErr_NARROW_all": round(pn_a, 3), "pErr_EXACT_all": round(pe_a, 3),
                "incidence_ratio_all": round(rr_a, 3),
                "pErr_NARROW_finerexists": round(pn_v, 3),
                "pErr_EXACT_finerexists": round(pe_v, 3),
                "incidence_ratio_finerexists": round(rr_v, 3),
            })

    all_ci = clustered_mh_ci(restrict=False)
    avail_ci = clustered_mh_ci(restrict=True)
    summary = {
        "pooled_MH_OR_all_mentions": round(mh_or(pooled_tables_all), 3),
        "pooled_MH_OR_all_mentions_ci95": all_ci,
        "pooled_MH_OR_restricted_to_gold_with_finer_code": round(mh_or(pooled_tables_avail), 3),
        "pooled_MH_OR_restricted_ci95": avail_ci,
        "ci_method": ("mention-clustered bootstrap, B = 10,000, seed 12345 - the same procedure "
                      "and seed as the published pooled odds ratio, resampling evaluation "
                      "mentions within each benchmark so that a mention recurs across systems"),
        "n_cells": len(pooled_tables_all),
        "note": ("A strictly more specific code is counted as existing when the frozen OLS4 "
                 "parent map contains at least one child of the gold concept. The map covers "
                 "the candidate space and its ancestors, so this is a lower bound on what full "
                 "SNOMED CT offers, and the space a system could actually have predicted into."),
    }
    write_csv("A_narrow_vs_ontology_availability.csv", rows_out)
    write_csv("A_narrow_label_coverage.csv", coverage)
    return rows_out, coverage, summary


# ---------------------------------------------------------------- B: ratio CI

def analysis_b():
    """Nam 3-4: the NARROW/EXACT credit-gap ratio carries no interval anywhere in the paper."""
    rng = random.Random(SEED)
    rows_out = []
    per_cell_draws = []

    for bench in BENCHMARKS:
        for system in SYSTEMS:
            cell = load_cell(bench, system)
            if cell is None:
                continue
            ex = [r for r in cell if r["rel"] == "EXACT"]
            na = [r for r in cell if r["rel"] == "NARROW"]
            point_e, point_n = credit_gap(ex), credit_gap(na)
            point = point_n / point_e if point_e else float("nan")

            draws = []
            for _ in range(B_BOOT):
                be = [ex[rng.randrange(len(ex))] for _ in range(len(ex))]
                bn = [na[rng.randrange(len(na))] for _ in range(len(na))]
                ge, gn = credit_gap(be), credit_gap(bn)
                draws.append(gn / ge if ge > 0 else float("nan"))
            lo, hi = boot_ci(draws)
            per_cell_draws.append(draws)
            rows_out.append({
                "benchmark": bench, "system": system,
                "n_EXACT": len(ex), "n_NARROW": len(na),
                "gap_EXACT": round(point_e, 3), "gap_NARROW": round(point_n, 3),
                "ratio": round(point, 3),
                "ratio_lo95": round(lo, 3), "ratio_hi95": round(hi, 3),
                "excludes_1": bool(lo > 1.0),
            })

    # geometric mean across cells, resampling all cells jointly on each draw
    geo_draws = []
    for b in range(B_BOOT):
        vals = [d[b] for d in per_cell_draws if d[b] > 0 and not math.isnan(d[b])]
        if len(vals) == len(per_cell_draws):
            geo_draws.append(math.exp(mean([math.log(v) for v in vals])))
    geo_point = math.exp(mean([math.log(r["ratio"]) for r in rows_out]))
    glo, ghi = boot_ci(geo_draws)
    summary = {
        "geometric_mean_ratio": round(geo_point, 3),
        "geometric_mean_ratio_ci95": [round(glo, 3), round(ghi, 3)],
        "cells_with_ci_excluding_1": sum(1 for r in rows_out if r["excludes_1"]),
        "n_cells": len(rows_out),
        "B": B_BOOT, "seed": SEED,
    }
    write_csv("B_credit_gap_ratio_bootstrap_ci.csv", rows_out)
    return rows_out, summary


# ---------------------------------------------------------------- C: heterogeneity

def analysis_c():
    """Nam 3-2, done in the form the data supports: strata = benchmarks, within one system."""
    rows_out = []
    for system in SYSTEMS:
        tables, benches = [], []
        for bench in BENCHMARKS:
            cell = load_cell(bench, system)
            if cell is None:
                continue
            a = sum(1 for r in cell if r["rel"] == "NARROW" and r["exact"] < 0.5)
            c = sum(1 for r in cell if r["rel"] == "NARROW" and r["exact"] >= 0.5)
            b = sum(1 for r in cell if r["rel"] == "EXACT" and r["exact"] < 0.5)
            d = sum(1 for r in cell if r["rel"] == "EXACT" and r["exact"] >= 0.5)
            tables.append((a, b, c, d))
            benches.append(bench)
        if len(tables) < 2:
            continue
        or_c = mh_or(tables)
        stat, p, df = breslow_day(tables, or_c)
        strat = []
        for (a, b, c, d) in tables:
            strat.append(round((a * d) / (b * c), 2) if b * c else float("nan"))
        rows_out.append({
            "system": system, "benchmarks": "|".join(benches),
            "MH_OR": round(or_c, 3),
            "stratum_ORs": "|".join(str(s) for s in strat),
            "breslow_day_chi2": round(stat, 3), "df": df,
            "p_homogeneity": (f"{p:.4g}" if not math.isnan(p) else "NA"),
            "homogeneity_rejected_at_0.05": bool(not math.isnan(p) and p < 0.05),
        })
    write_csv("C_or_heterogeneity_breslow_day.csv", rows_out)
    return rows_out


# ---------------------------------------------------------------- output

def write_csv(name, rows):
    if not rows:
        return
    with open(os.path.join(OUT, name), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def self_check():
    """The pipeline must reproduce the published Table 4 gaps from the same per-mention rows."""
    published = {}
    with open(os.path.join(CANONICAL, "table3_creditgap.csv")) as fh:
        for r in csv.DictReader(fh):
            published[(r["benchmark"].lower(), r["system"])] = (
                float(r["gap_EXACT"]), float(r["gap_NARROW"]), float(r["ratio"]))
    checked = 0
    for (bench, system), (ge, gn, ratio) in published.items():
        cell = load_cell(bench, system)
        assert cell, f"missing per-mention rows for {bench}/{system}"
        mine_e = credit_gap([r for r in cell if r["rel"] == "EXACT"])
        mine_n = credit_gap([r for r in cell if r["rel"] == "NARROW"])
        assert abs(mine_e - ge) < 1e-3, f"{bench}/{system} gap_EXACT {mine_e:.4f} vs {ge}"
        assert abs(mine_n - gn) < 1e-3, f"{bench}/{system} gap_NARROW {mine_n:.4f} vs {gn}"
        assert abs(mine_n / mine_e - ratio) < 5e-3, f"{bench}/{system} ratio"
        checked += 1
    assert checked == 14, f"expected 14 published cells, reproduced {checked}"
    print(f"self-check OK: reproduced all {checked} published credit-gap cells")


if __name__ == "__main__":
    self_check()
    a_rows, a_cov, a_sum = analysis_a()
    b_rows, b_sum = analysis_b()
    c_rows = analysis_c()
    with open(os.path.join(OUT, "nam_reinforcement_summary.json"), "w") as fh:
        json.dump({"A_ontology_availability": a_sum,
                   "A_label_coverage": a_cov,
                   "B_ratio_ci": b_sum,
                   "C_heterogeneity": c_rows}, fh, indent=2)
    print("\n--- A: does a finer code even exist? ---")
    for r in a_cov:
        print(f"  {r['benchmark']:11s} {r['stratum']:6s} n={r['n_mentions']:4d} "
              f"finer code exists for {r['pct_with_finer_code']}%")
    print(f"  pooled MH OR, all mentions          : {a_sum['pooled_MH_OR_all_mentions']}")
    print(f"  pooled MH OR, finer code exists only: "
          f"{a_sum['pooled_MH_OR_restricted_to_gold_with_finer_code']}")
    print("\n--- B: credit-gap ratio with CI ---")
    for r in b_rows:
        print(f"  {r['benchmark']:11s} {r['system']:11s} {r['ratio']:5.2f} "
              f"[{r['ratio_lo95']:.2f}, {r['ratio_hi95']:.2f}]"
              f"{'' if r['excludes_1'] else '   <- includes 1'}")
    print(f"  geometric mean {b_sum['geometric_mean_ratio']} "
          f"{b_sum['geometric_mean_ratio_ci95']}; "
          f"{b_sum['cells_with_ci_excluding_1']}/{b_sum['n_cells']} cells exclude 1")
    print("\n--- C: is the pooled OR poolable? ---")
    for r in c_rows:
        print(f"  {r['system']:11s} MH OR {r['MH_OR']:5.2f}  strata {r['stratum_ORs']:22s} "
              f"BD chi2={r['breslow_day_chi2']:7.2f} df={r['df']} p={r['p_homogeneity']}")
