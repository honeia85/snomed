#!/usr/bin/env python3
"""Reproduce the binary same-lineage sensitivity and its bootstrap intervals.

Analysis: NARROW-minus-EXACT uplift in binary is-a consistency
Date: 2026-07-23
Random seed: 42
Bootstrap: 10,000 fixed-stratum item resamples, synchronized across systems
Key package: NumPy
"""
import csv
import json
import os
import sys

import numpy as np

SEED = 42
B_ITER = 10_000
HERE = os.path.dirname(os.path.abspath(__file__))
PM = os.path.join(HERE, "..", "per_mention")
ONTO = os.path.join(HERE, "..", "ontology")
FROZEN = os.path.join(HERE, "is_a_sensitivity.csv")
SYS = ["lexical", "sapbert", "sapbert_ft", "llm_rerank", "llm_gen"]
BEN = ["distemist", "medprocner", "symptemist"]
ABBR = {"distemist": "DisTEMIST", "medprocner": "MedProcNER", "symptemist": "SympTEMIST"}


def read_rows(benchmark, system):
    path = os.path.join(PM, f"{benchmark}_oracle_{system}_per_mention.csv")
    if not os.path.exists(path):
        return None
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_ancestors(benchmark):
    path = os.path.join(ONTO, f"{benchmark}_ancmap.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as handle:
        return {key: set(value) for key, value in json.load(handle).items()}


def is_a_value(row, ancestors):
    if "is_a" in row:
        return int(row["is_a"])
    pred, gold = row["pred1"], row["gold"]
    if pred == gold:
        return 1
    return int(pred in ancestors.get(gold, {gold}) or gold in ancestors.get(pred, {pred}))


def item_key(row, index):
    return row.get("item_id") or f"ROW-{index:06d}"


def reproduce():
    rng = np.random.default_rng(SEED)
    results = []

    for benchmark in BEN:
        ancestors = load_ancestors(benchmark)
        by_system = {}
        for system in SYS:
            rows = read_rows(benchmark, system)
            if rows is None:
                continue
            keyed = {item_key(row, index): row for index, row in enumerate(rows)}
            by_system[system] = keyed

        first = next(iter(by_system.values()))
        exact_ids = [key for key, row in first.items() if row["semantic_rel"] == "EXACT"]
        narrow_ids = [key for key, row in first.items() if row["semantic_rel"] == "NARROW"]
        exact_idx = rng.integers(0, len(exact_ids), size=(B_ITER, len(exact_ids)))
        narrow_idx = rng.integers(0, len(narrow_ids), size=(B_ITER, len(narrow_ids)))

        for system in SYS:
            if system not in by_system:
                continue
            rows = by_system[system]
            if set(rows) != set(first):
                raise ValueError(f"Item mismatch for {benchmark}/{system}")
            for key, reference_row in first.items():
                if rows[key]["semantic_rel"] != reference_row["semantic_rel"]:
                    raise ValueError(f"Stratum mismatch for {benchmark}/{system}/{key}")

            exact = np.array(
                [is_a_value(rows[key], ancestors) - int(rows[key]["exact"]) for key in exact_ids],
                dtype=float,
            )
            narrow = np.array(
                [is_a_value(rows[key], ancestors) - int(rows[key]["exact"]) for key in narrow_ids],
                dtype=float,
            )
            uplift_exact = exact.mean()
            uplift_narrow = narrow.mean()
            delta = uplift_narrow - uplift_exact
            boot = narrow[narrow_idx].mean(axis=1) - exact[exact_idx].mean(axis=1)
            lower, upper = np.percentile(boot, [2.5, 97.5])

            isa_exact = np.mean(
                [is_a_value(rows[key], ancestors) for key in exact_ids]
            )
            isa_narrow = np.mean(
                [is_a_value(rows[key], ancestors) for key in narrow_ids]
            )
            results.append({
                "benchmark": ABBR[benchmark],
                "system": system,
                "n_EXACT": len(exact_ids),
                "n_NARROW": len(narrow_ids),
                "isa_EXACT": isa_exact,
                "isa_NARROW": isa_narrow,
                "uplift_EXACT": uplift_exact,
                "uplift_NARROW": uplift_narrow,
                "delta_uplift": delta,
                "ci_lower": lower,
                "ci_upper": upper,
            })
    return results


def verify_frozen(results):
    with open(FROZEN, newline="", encoding="utf-8") as handle:
        frozen = {
            (row["benchmark"], row["system"]): row
            for row in csv.DictReader(handle)
        }
    numeric = [
        "isa_EXACT", "isa_NARROW", "uplift_EXACT", "uplift_NARROW",
        "delta_uplift", "ci_lower", "ci_upper",
    ]
    for row in results:
        key = (row["benchmark"], row["system"])
        if key not in frozen:
            raise ValueError(f"Missing frozen row: {key}")
        expected = frozen[key]
        if int(expected["n_EXACT"]) != row["n_EXACT"] or int(expected["n_NARROW"]) != row["n_NARROW"]:
            raise ValueError(f"Sample-size mismatch: {key}")
        for field in numeric:
            if round(row[field], 6) != round(float(expected[field]), 6):
                raise ValueError(f"Frozen mismatch: {key} {field}")


if __name__ == "__main__":
    print(f"Python: {sys.version.split()[0]}; NumPy: {np.__version__}; seed={SEED}; B={B_ITER}")
    reproduced = reproduce()
    verify_frozen(reproduced)
    for row in reproduced:
        print(
            f"{row['benchmark']:11} {row['system']:11} "
            f"uplift_E={row['uplift_EXACT']:.3f} uplift_N={row['uplift_NARROW']:.3f} "
            f"delta={row['delta_uplift']:+.3f} "
            f"[{row['ci_lower']:+.3f}, {row['ci_upper']:+.3f}]"
        )
    positive = sum(row["delta_uplift"] > 0 for row in reproduced)
    excludes_zero = sum(row["ci_lower"] > 0 or row["ci_upper"] < 0 for row in reproduced)
    print(f"Positive delta: {positive}/{len(reproduced)}; 95% CI excludes zero: {excludes_zero}/{len(reproduced)}")
    print("PASS: reproduced values match is_a_sensitivity.csv")
