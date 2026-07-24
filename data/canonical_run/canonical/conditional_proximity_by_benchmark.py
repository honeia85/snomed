#!/usr/bin/env python3
"""Reproduce conditional-proximity differences overall and by benchmark.

Estimand: within each system x benchmark cell, mean Wu-Palmer among NARROW
errors minus mean Wu-Palmer among EXACT errors. Benchmark estimates give equal
weight to their available systems; the overall estimate gives equal weight to
all 14 cells.

Bootstrap: 10,000 fixed-stratum item resamples (seed 42). The same sampled item
indices are used for every system within a benchmark, preserving cross-system
dependence. This does not model within-document clustering.
"""
import csv
import os
import sys

import numpy as np


SEED = 42
B_ITER = 10_000
HERE = os.path.dirname(os.path.abspath(__file__))
PM = os.path.join(HERE, "..", "per_mention")
FROZEN = os.path.join(HERE, "conditional_proximity_by_benchmark.csv")
SYSTEMS = ["lexical", "sapbert", "sapbert_ft", "llm_rerank", "llm_gen"]
BENCHMARKS = ["distemist", "medprocner", "symptemist"]
DISPLAY = {
    "distemist": "DisTEMIST",
    "medprocner": "MedProcNER",
    "symptemist": "SympTEMIST",
}


def read_rows(benchmark, system):
    path = os.path.join(PM, f"{benchmark}_oracle_{system}_per_mention.csv")
    if not os.path.exists(path):
        return None
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def item_key(row, index):
    return row.get("item_id") or f"ROW-{index:06d}"


def cell_difference(rows, exact_ids, narrow_ids, exact_draw, narrow_draw):
    exact_flag = np.array([int(rows[key]["exact"]) for key in exact_ids])
    exact_wup = np.array([float(rows[key]["wup"]) for key in exact_ids])
    narrow_flag = np.array([int(rows[key]["exact"]) for key in narrow_ids])
    narrow_wup = np.array([float(rows[key]["wup"]) for key in narrow_ids])

    exact_error = 1 - exact_flag
    narrow_error = 1 - narrow_flag
    point = (
        (narrow_wup * narrow_error).sum() / narrow_error.sum()
        - (exact_wup * exact_error).sum() / exact_error.sum()
    )

    exact_boot_error = exact_error[exact_draw]
    narrow_boot_error = narrow_error[narrow_draw]
    exact_boot = (
        (exact_wup[exact_draw] * exact_boot_error).sum(axis=1)
        / exact_boot_error.sum(axis=1)
    )
    narrow_boot = (
        (narrow_wup[narrow_draw] * narrow_boot_error).sum(axis=1)
        / narrow_boot_error.sum(axis=1)
    )
    return point, narrow_boot - exact_boot


def reproduce():
    rng = np.random.default_rng(SEED)
    rows_out = []
    all_points = []
    all_bootstraps = []
    benchmark_bootstraps = {}

    for benchmark in BENCHMARKS:
        by_system = {}
        for system in SYSTEMS:
            source = read_rows(benchmark, system)
            if source is None:
                continue
            by_system[system] = {
                item_key(row, index): row for index, row in enumerate(source)
            }

        first = next(iter(by_system.values()))
        exact_ids = [
            key for key, row in first.items() if row["semantic_rel"] == "EXACT"
        ]
        narrow_ids = [
            key for key, row in first.items() if row["semantic_rel"] == "NARROW"
        ]
        exact_draw = rng.integers(
            0, len(exact_ids), size=(B_ITER, len(exact_ids))
        )
        narrow_draw = rng.integers(
            0, len(narrow_ids), size=(B_ITER, len(narrow_ids))
        )

        points = []
        bootstraps = []
        for system in SYSTEMS:
            if system not in by_system:
                continue
            rows = by_system[system]
            if set(rows) != set(first):
                raise ValueError(f"Item mismatch for {benchmark}/{system}")
            for key, reference_row in first.items():
                if rows[key]["semantic_rel"] != reference_row["semantic_rel"]:
                    raise ValueError(
                        f"Stratum mismatch for {benchmark}/{system}/{key}"
                    )
            point, boot = cell_difference(
                rows, exact_ids, narrow_ids, exact_draw, narrow_draw
            )
            points.append(point)
            bootstraps.append(boot)
            all_points.append(point)
            all_bootstraps.append(boot)

        benchmark_boot = np.mean(bootstraps, axis=0)
        benchmark_bootstraps[DISPLAY[benchmark]] = benchmark_boot
        lower, upper = np.percentile(benchmark_boot, [2.5, 97.5])
        rows_out.append({
            "scope": DISPLAY[benchmark],
            "n_cells": len(points),
            "estimate": np.mean(points),
            "ci_lower": lower,
            "ci_upper": upper,
        })

    overall_boot = np.mean(all_bootstraps, axis=0)
    lower, upper = np.percentile(overall_boot, [2.5, 97.5])
    rows_out.insert(0, {
        "scope": "All 14 cells",
        "n_cells": len(all_points),
        "estimate": np.mean(all_points),
        "ci_lower": lower,
        "ci_upper": upper,
    })
    return rows_out, benchmark_bootstraps


def verify_frozen(results):
    with open(FROZEN, newline="", encoding="utf-8") as handle:
        frozen = {row["scope"]: row for row in csv.DictReader(handle)}
    for row in results:
        expected = frozen[row["scope"]]
        if int(expected["n_cells"]) != row["n_cells"]:
            raise ValueError(f"Cell-count mismatch: {row['scope']}")
        for field in ("estimate", "ci_lower", "ci_upper"):
            if round(float(expected[field]), 6) != round(row[field], 6):
                raise ValueError(f"Frozen mismatch: {row['scope']} {field}")


if __name__ == "__main__":
    print(
        f"Python: {sys.version.split()[0]}; NumPy: {np.__version__}; "
        f"seed={SEED}; B={B_ITER}"
    )
    reproduced, benchmark_boot = reproduce()
    verify_frozen(reproduced)
    for row in reproduced:
        print(
            f"{row['scope']:13} cells={row['n_cells']:2d} "
            f"delta={row['estimate']:+.3f} "
            f"[{row['ci_lower']:+.3f}, {row['ci_upper']:+.3f}]"
        )
    contrasts = [
        ("MedProcNER - DisTEMIST", "MedProcNER", "DisTEMIST"),
        ("SympTEMIST - DisTEMIST", "SympTEMIST", "DisTEMIST"),
        ("SympTEMIST - MedProcNER", "SympTEMIST", "MedProcNER"),
    ]
    for label, left, right in contrasts:
        contrast = benchmark_boot[left] - benchmark_boot[right]
        lower, upper = np.percentile(contrast, [2.5, 97.5])
        print(
            f"{label:27} delta={contrast.mean():+.3f} "
            f"[{lower:+.3f}, {upper:+.3f}]"
        )
    print("PASS: reproduced values match conditional_proximity_by_benchmark.csv")
