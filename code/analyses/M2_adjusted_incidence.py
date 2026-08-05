#!/usr/bin/env python3
"""M2: is the granularity label a proxy for lexical or ontological difficulty?

Fits a modified-Poisson model (Poisson regression with a log link on the binary error outcome,
so exp(beta) reads as a risk ratio) of exact-match error on the granularity label, adjusted for

  * mention length, in characters, from the annotation offsets;
  * how often the gold concept occurs in the training pairs;
  * local candidate-space density around the gold concept, defined as the number of candidate
    codes that share a direct parent with it - the codes a lateral error can land on;
  * the depth of the gold concept in the is-a graph;

with system fixed effects and a variance estimator clustered on the source document.

SCOPE - read this before quoting the number. The analysis runs on SympTEMIST only. The canonical
evaluation samples for DisTEMIST (n = 678) and MedProcNER (n = 625) were de-duplicated after
stratified sampling, and no archived artefact records which rows survived: the canonical
per-mention files carry no item key, and the historical per-example files hold a different,
larger row set. Reconstructing them would mean re-running a sampler whose behaviour depends on
the pandas version, and a silently different row set would produce a plausible wrong answer.
SympTEMIST's canonical rows align exactly, item for item, with the archived per-example file
(800/800 on gold code and granularity label, verified in the self-check below), so it is the one
benchmark where the adjustment can be run on the canonical outcomes without guessing.

Outcomes come from the canonical run. The per-example file supplies item keys only - its own
prediction columns are from a superseded run and agree with the canonical outcome on just
652-734 of 800 rows per system, which is exactly why they are not used.

Run:  python3 M2_adjusted_incidence.py
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
PEREX = os.path.join(REL, "05_reproducibility_inputs", "symptemist_per_example.csv")
CORPUS = os.path.join(REL, "08_rerun_colab", "results", "corpus_cache", "symptemist_corpus.json")
ONTO = os.path.join(REL, "08_rerun_colab", "results", "ontology_cache", "symptemist_ols_cache.json")
DEPTHS = os.path.join(REL, "08_rerun_colab", "results", "ontology", "symptemist_depths.json")

spec = importlib.util.spec_from_file_location("ra", os.path.join(HERE, "robustness_analyses.py"))
ra = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ra)

BENCH = "symptemist"
SYSTEMS = ["lexical", "sapbert", "sapbert_ft", "llm_rerank", "llm_gen"]


# ----------------------------------------------------------------- linear algebra

def solve(A, b):
    """Gaussian elimination with partial pivoting; A is square, modified in place."""
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-12:
            raise ValueError("singular design matrix")
        M[col], M[piv] = M[piv], M[col]
        p = M[col][col]
        for r in range(n):
            if r == col:
                continue
            f = M[r][col] / p
            if f:
                for c in range(col, n + 1):
                    M[r][c] -= f * M[col][c]
    return [M[i][n] / M[i][i] for i in range(n)]


def inverse(A):
    n = len(A)
    cols = []
    for j in range(n):
        e = [1.0 if i == j else 0.0 for i in range(n)]
        cols.append(solve([row[:] for row in A], e))
    return [[cols[j][i] for j in range(n)] for i in range(n)]


# ----------------------------------------------------------------- model

def poisson_irls(X, y, iters=100, tol=1e-10):
    p = len(X[0])
    beta = [0.0] * p
    beta[0] = math.log(max(sum(y) / len(y), 1e-6))
    for _ in range(iters):
        mu = []
        for row in X:
            eta = sum(b * v for b, v in zip(beta, row))
            mu.append(math.exp(max(min(eta, 30.0), -30.0)))
        XtWX = [[0.0] * p for _ in range(p)]
        XtWz = [0.0] * p
        for row, yi, mi in zip(X, y, mu):
            w = mi
            eta = sum(b * v for b, v in zip(beta, row))
            z = eta + (yi - mi) / max(mi, 1e-10)
            for a in range(p):
                XtWz[a] += w * row[a] * z
                for c in range(a, p):
                    XtWX[a][c] += w * row[a] * row[c]
        for a in range(p):
            for c in range(a):
                XtWX[a][c] = XtWX[c][a]
        new = solve([r[:] for r in XtWX], XtWz)
        if max(abs(n - o) for n, o in zip(new, beta)) < tol:
            beta = new
            break
        beta = new
    return beta


def cluster_robust(X, y, beta, clusters):
    p = len(X[0])
    mu = [math.exp(max(min(sum(b * v for b, v in zip(beta, row)), 30.0), -30.0)) for row in X]
    bread = [[0.0] * p for _ in range(p)]
    for row, mi in zip(X, mu):
        for a in range(p):
            for c in range(p):
                bread[a][c] += mi * row[a] * row[c]
    scores = defaultdict(lambda: [0.0] * p)
    for row, yi, mi, g in zip(X, y, mu, clusters):
        r = yi - mi
        s = scores[g]
        for a in range(p):
            s[a] += row[a] * r
    meat = [[0.0] * p for _ in range(p)]
    for s in scores.values():
        for a in range(p):
            for c in range(p):
                meat[a][c] += s[a] * s[c]
    B = inverse(bread)
    V = [[sum(B[a][k] * meat[k][l] * B[l][c] for k in range(p) for l in range(p))
          for c in range(p)] for a in range(p)]
    return [math.sqrt(max(V[i][i], 0.0)) for i in range(p)], len(scores)


# ----------------------------------------------------------------- data

def build():
    per = defaultdict(list)
    for r in csv.DictReader(open(PEREX)):
        per[r["system"]].append(r)

    corpus = json.load(open(CORPUS))
    train_freq = Counter(code for _, code in corpus["train_pairs"])

    par = json.load(open(ONTO))["par"]
    candidates = set(json.load(open(ONTO))["anc"])
    siblings = Counter()
    kids = defaultdict(set)
    for child, parents in par.items():
        for p in parents:
            kids[p].add(child)
    for code in candidates:
        sib = set()
        for p in par.get(code, []):
            sib |= kids.get(p, set())
        sib.discard(code)
        siblings[code] = len(sib & candidates)

    depths = json.load(open(DEPTHS))

    rows = []
    for s in SYSTEMS:
        keys = per[s]
        canon = ra.load_cell(BENCH, s)
        assert canon and len(canon) == len(keys), f"row-count mismatch for {s}"
        for k, c in zip(keys, canon):
            assert k["gold"].strip() == c["gold"], "gold mismatch: item keys are not aligned"
            assert k["semantic_rel"].strip() == c["rel"], "granularity label mismatch"
            doc, start, end = k["span"].rsplit("|", 2)
            rows.append({
                "system": s,
                "doc": doc,
                "err": 1.0 if c["exact"] < 0.5 else 0.0,
                "narrow": 1.0 if c["rel"] == "NARROW" else 0.0,
                "len": max(int(end) - int(start), 1),
                "freq": train_freq.get(c["gold"], 0),
                "dens": siblings.get(c["gold"], 0),
                "depth": depths.get(c["gold"], 0) or 0,
            })
    return rows


def design(rows, adjusted):
    X, y, cl = [], [], []
    for r in rows:
        row = [1.0, r["narrow"]]
        if adjusted:
            row += [math.log(r["len"]),
                    math.log1p(r["freq"]),
                    math.log1p(r["dens"]),
                    float(r["depth"])]
        row += [1.0 if r["system"] == s else 0.0 for s in SYSTEMS[1:]]
        X.append(row)
        y.append(r["err"])
        cl.append(r["doc"])
    return X, y, cl


def report(name, rows, adjusted):
    X, y, cl = design(rows, adjusted)
    beta = poisson_irls(X, y)
    se, ngroups = cluster_robust(X, y, beta, cl)
    rr = math.exp(beta[1])
    lo, hi = math.exp(beta[1] - 1.96 * se[1]), math.exp(beta[1] + 1.96 * se[1])
    names = ["(intercept)", "NARROW"] + (
        ["log mention length", "log(1+train frequency)", "log(1+sibling density)", "gold depth"]
        if adjusted else []) + [f"system={s}" for s in SYSTEMS[1:]]
    print(f"\n{name}  (n = {len(y)} mention x system rows, {ngroups} document clusters)")
    for nm, b, s in zip(names, beta, se):
        if nm == "(intercept)":
            continue
        print(f"    {nm:<26s} RR {math.exp(b):6.3f}   95% CI {math.exp(b-1.96*s):.3f}-{math.exp(b+1.96*s):.3f}")
    return rr, lo, hi


if __name__ == "__main__":
    rows = build()
    # self-check: the unadjusted model must reproduce the crude SympTEMIST risk ratio
    crude_n = sum(r["err"] for r in rows if r["narrow"]) / sum(1 for r in rows if r["narrow"])
    crude_e = sum(r["err"] for r in rows if not r["narrow"]) / sum(1 for r in rows if not r["narrow"])
    crude = crude_n / crude_e
    X, y, cl = design(rows, adjusted=False)
    b0 = poisson_irls([[row[0], row[1]] for row in X], y)
    assert abs(math.exp(b0[1]) - crude) < 1e-6, f"model {math.exp(b0[1]):.6f} vs crude {crude:.6f}"
    print(f"self-check OK: unadjusted model reproduces the crude SympTEMIST risk ratio {crude:.4f}")

    un = report("unadjusted (system fixed effects only)", rows, adjusted=False)
    ad = report("adjusted for length, training frequency, sibling density and depth", rows, adjusted=True)

    print(f"\nNARROW risk ratio: {un[0]:.3f} [{un[1]:.3f}, {un[2]:.3f}] unadjusted"
          f"  ->  {ad[0]:.3f} [{ad[1]:.3f}, {ad[2]:.3f}] adjusted")
    json.dump({
        "benchmark": "SympTEMIST",
        "n_rows": len(rows), "n_mentions": len(rows) // len(SYSTEMS),
        "unadjusted_RR": round(un[0], 3), "unadjusted_ci95": [round(un[1], 3), round(un[2], 3)],
        "adjusted_RR": round(ad[0], 3), "adjusted_ci95": [round(ad[1], 3), round(ad[2], 3)],
        "covariates": ["log mention length (characters)", "log(1 + gold-code training frequency)",
                       "log(1 + candidate-space sibling density)", "gold-code depth"],
        "variance": "cluster-robust on source document",
        "scope_note": ("SympTEMIST only. The canonical DisTEMIST and MedProcNER samples were "
                       "de-duplicated after stratified sampling and no archived artefact records "
                       "which rows survived, so their mentions cannot be joined to offsets "
                       "without re-running a version-dependent sampler."),
    }, open(os.path.join(HERE, "M2_adjusted_incidence.json"), "w"), indent=2)
    print("\nwrote M2_adjusted_incidence.json")
