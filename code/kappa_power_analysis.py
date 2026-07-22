#!/usr/bin/env python3
"""
M2 human-anchor sub-sample: precision / power analysis for Cohen's kappa
(EXACT vs NARROW granularity label validation).

Question answered: is n=150 (50 per Spanish benchmark) enough to validate the
granularity label against human annotation?

Method: Monte-Carlo. For a target true kappa and NARROW prevalence (symmetric
marginals), build the 2x2 agreement cell probabilities, draw multinomial samples
of size n, recompute kappa, and summarize the sampling distribution. "Power to
clear a threshold t" = fraction of samples whose 95% CI lower bound (k_hat -
1.96*SD_emp) exceeds t. This matches the estimand: a VALIDATION study wants the
CI lower bound above 'substantial' (0.6), not a difference test.

No external data needed. Deterministic (seed fixed).

Usage:
    python3 kappa_power_analysis.py
    python3 kappa_power_analysis.py --n 150 --prev 0.25 --true_k 0.84 --nsim 20000
"""
import argparse
import numpy as np


def kappa_from_counts(a, b, c, d):
    n = a + b + c + d
    if n == 0:
        return np.nan
    po = (a + d) / n
    p1, p2 = (a + b) / n, (a + c) / n
    pe = p1 * p2 + (1 - p1) * (1 - p2)
    return np.nan if pe >= 1 else (po - pe) / (1 - pe)


def cells_for(prev, true_k):
    """Symmetric-marginal 2x2 cell probs [both-NARROW, dis, dis, both-EXACT]."""
    pe = prev**2 + (1 - prev) ** 2
    po = pe + true_k * (1 - pe)
    b = (1 - po) / 2.0
    a, d = prev - b, (1 - prev) - b
    cells = np.array([a, b, b, d])
    return None if (cells < 0).any() else cells


def simulate(n, prev, true_k, nsim=8000, seed=42, thresholds=(0.6, 0.4)):
    cells = cells_for(prev, true_k)
    if cells is None:
        return None  # infeasible: prevalence too skewed for this kappa
    rng = np.random.default_rng(seed)
    draws = rng.multinomial(n, cells, size=nsim)
    ks = np.array([kappa_from_counts(*row) for row in draws], dtype=float)
    ks = ks[~np.isnan(ks)]
    sd = ks.std()
    lo, hi = np.quantile(ks, [0.025, 0.975])
    out = dict(n=n, prev=prev, true_k=true_k, mean=ks.mean(), sd=sd,
               ci_lo=lo, ci_hi=hi, halfwidth=1.96 * sd,
               n_narrow_expected=prev * n)
    for t in thresholds:
        out[f"power_LB>{t}"] = float(np.mean((ks - 1.96 * sd) > t))
    return out


DEFAULT_SCENARIOS = [
    ("Pooled n=150, balanced prev .50", 150, 0.50, 0.84),
    ("Pooled n=150, realistic prev .25", 150, 0.25, 0.84),
    ("Per-bench n=50, DisTEMIST .30",     50, 0.30, 0.84),
    ("Per-bench n=50, SympTEMIST .25",    50, 0.25, 0.84),
    ("Per-bench n=50, MedProcNER .17",    50, 0.17, 0.84),
    ("Pooled n=150, only-moderate .25",  150, 0.25, 0.65),
    ("Per-bench n=150 target .17",       150, 0.17, 0.84),  # to hit per-bench precision
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int)
    ap.add_argument("--prev", type=float)
    ap.add_argument("--true_k", type=float)
    ap.add_argument("--nsim", type=int, default=8000)
    a = ap.parse_args()

    hdr = f"{'scenario':36s} {'meanK':>6s} {'SD':>6s} {'95%CI':>15s} {'±hw':>6s} {'P(LB>.6)':>9s} {'P(LB>.4)':>9s} {'~NARROW':>8s}"
    print(hdr); print("-" * len(hdr))
    if a.n:
        scen = [(f"custom n={a.n} prev={a.prev} k={a.true_k}", a.n, a.prev, a.true_k)]
    else:
        scen = DEFAULT_SCENARIOS
    for label, n, prev, tk in scen:
        r = simulate(n, prev, tk, nsim=a.nsim)
        if r is None:
            print(f"{label:36s}  infeasible (prev too skewed for k)"); continue
        print(f"{label:36s} {r['mean']:6.3f} {r['sd']:6.3f} "
              f"[{r['ci_lo']:.2f},{r['ci_hi']:.2f}] {r['halfwidth']:6.3f} "
              f"{r['power_LB>0.6']:9.2f} {r['power_LB>0.4']:9.2f} {r['n_narrow_expected']:8.0f}")

    print("\nReading: 'power_LB>0.6' = P(95% CI lower bound clears 'substantial').")
    print("Validation goal is met when this is high (>=0.9) for the POOLED estimate.")


if __name__ == "__main__":
    main()
