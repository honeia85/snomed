#!/usr/bin/env python3
"""N8: what values other than EXACT and NARROW do the three corpora carry, and how many rows
did each contribute?

The archived evaluation inputs are already filtered to the two eligible values, so the counts
have to come from the corpus distributions as released. DisTEMIST and MedProcNER are downloaded
from the Zenodo records cited in the manuscript; SympTEMIST is read from the copy retained in
the project archive.

Run:  python3 N8_semantic_rel_values.py [--download-dir DIR]

Without network access it reports whatever it can find locally and says so, rather than
guessing.
"""

import argparse
import collections
import csv
import io
import json
import os
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))

# Inputs that cannot be redistributed (gold concepts, the frozen is-a graph, corpus annotation
# offsets) live outside this repository. Point CREDITGAP_SOURCE_ROOT at a tree holding them, or
# edit the default below. Analyses that need only the deposited identifier-free rows resolve
# against this repository and run without it.
SOURCE_ROOT = os.environ.get("CREDITGAP_SOURCE_ROOT", os.path.join(HERE, "..", "..", "source"))

ARCHIVE = os.path.join(SOURCE_ROOT, "archive")

# Zenodo *version* records. Note the manuscript cites the concept DOIs (6408476 / 7929830),
# which always resolve to the newest version; the versions actually read here are recorded so
# the counts can be reproduced exactly.
SOURCES = {
    "DisTEMIST": {
        "record": "7614764",
        "concept_doi": "10.5281/zenodo.6408476",
        "file": "distemist_zenodo.zip",
        "members": {
            "train (subtrack2, part 1)": "distemist_zenodo/training/subtrack2_linking/distemist_subtrack2_training1_linking.tsv",
            "train (subtrack2, part 2)": "distemist_zenodo/training/subtrack2_linking/distemist_subtrack2_training2_linking.tsv",
            "test (subtrack2)": "distemist_zenodo/test_annotated/subtrack2_linking/distemist_subtrack2_test_linking.tsv",
        },
    },
    "MedProcNER": {
        "record": "7929830",
        "concept_doi": "10.5281/zenodo.7929830",
        "file": "medprocner_gs_train+test+gazz_230512.zip",
        "members": {
            "train (subtask 2)": "medprocner_gs_train+test+gazz_230502/medprocner_train/tsv/medprocner_tsv_train_subtask2.tsv",
        },
    },
}

LOCAL = {
    "SympTEMIST": {
        "train (subtask 2)": os.path.join(ARCHIVE, "symptemist_tsv_train_subtask2.tsv"),
    },
}


def rel_column(fieldnames):
    for k in fieldnames:
        if "sem" in k.lower() and "rel" in k.lower():
            return k
    return None


def count_tsv(handle):
    reader = csv.DictReader(handle, delimiter="\t")
    col = rel_column(reader.fieldnames or [])
    if col is None:
        return None, None
    counts = collections.Counter(r[col] for r in reader)
    return col, counts


def fetch(record, filename, dest_dir):
    dest = os.path.join(dest_dir, f"{record}_{filename}")
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    url = f"https://zenodo.org/records/{record}/files/{filename}?download=1"
    try:
        subprocess.run(["curl", "-sL", "--max-time", "600", "-o", dest, url],
                       check=True, capture_output=True)
    except Exception as exc:
        print(f"  could not download {filename}: {exc}", file=sys.stderr)
        return None
    return dest if os.path.exists(dest) and os.path.getsize(dest) > 1000 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--download-dir", default=os.environ.get("TMPDIR", "/tmp"))
    args = ap.parse_args()

    report = {}

    for corpus, spec in SOURCES.items():
        path = fetch(spec["record"], spec["file"], args.download_dir)
        if not path:
            report[corpus] = {"status": "unavailable - download failed"}
            continue
        zf = zipfile.ZipFile(path)
        splits = {}
        for split, member in spec["members"].items():
            with zf.open(member) as fh:
                col, counts = count_tsv(io.TextIOWrapper(fh, "utf-8"))
            splits[split] = {"column": col, "counts": dict(counts)} if counts else {"error": "no sem_rel column"}
        report[corpus] = {"zenodo_record": spec["record"], "concept_doi": spec["concept_doi"],
                          "splits": splits}

    for corpus, files in LOCAL.items():
        splits = {}
        for split, path in files.items():
            if not os.path.exists(path):
                splits[split] = {"error": f"not found: {path}"}
                continue
            with open(path) as fh:
                col, counts = count_tsv(fh)
            splits[split] = {"column": col, "counts": dict(counts)} if counts else {"error": "no sem_rel column"}
        report[corpus] = {"source": "project archive", "splits": splits}

    for corpus, data in report.items():
        print(f"\n=== {corpus} ===")
        if "splits" not in data:
            print(" ", data.get("status", "no data"))
            continue
        for split, s in data["splits"].items():
            if "counts" not in s:
                print(f"  {split}: {s.get('error')}")
                continue
            c = s["counts"]
            eligible = c.get("EXACT", 0) + c.get("NARROW", 0)
            other = {k: v for k, v in c.items() if k not in ("EXACT", "NARROW")}
            n_other = sum(other.values())
            print(f"  {split}: EXACT {c.get('EXACT', 0)}, NARROW {c.get('NARROW', 0)} "
                  f"(eligible {eligible}); other {n_other} across {len(other)} value(s)")
            for k, v in sorted(other.items(), key=lambda kv: -kv[1])[:8]:
                print(f"      {k}: {v}")
            if len(other) > 8:
                print(f"      ... and {len(other) - 8} further composite value(s)")

    json.dump(report, open(os.path.join(HERE, "N8_semantic_rel_values.json"), "w"), indent=2)
    print("\nwrote N8_semantic_rel_values.json")


if __name__ == "__main__":
    main()
