#!/usr/bin/env python3
"""
prep_inputs.py — convert the real TEMIST gold files into harness inputs.

IMPORTANT: TEMIST column names must be VERIFIED against your downloaded files.
Run `--inspect` first; it prints the columns and a few rows for every table it
finds, then set COLUMN_MAP accordingly. Defaults below are a best guess for the
TEMIST normalization TSVs and are marked TODO-VERIFY — do not trust blindly.

Outputs (per benchmark B): corpus_{B}.csv with columns
  mention_id, benchmark, mention_text, gold_code, semantic_rel(EXACT|NARROW), doc_id
plus all_codes.txt (union of gold codes, for build_ontology_ols4.py).

Note on language: TEMIST mentions are Spanish. The neural/LLM systems in the
paper translate mentions to English before matching English SNOMED labels. This
script keeps `mention_text` as-is; insert your translation step (released prompt/
Qwen, or NLLB for the ablation) before scoring with SapBERT.
"""
import argparse, glob, os, sys
import pandas as pd

# TODO-VERIFY against your files (run --inspect). Keys are logical fields.
COLUMN_MAP = {
    "mention_text": "text",        # span surface form
    "gold_code":    "code",        # SNOMED CT identifier
    "semantic_rel": "semantic_rel",# EXACT / NARROW (may be 'sem_rel' or 'relation')
    "doc_id":       "filename",    # source document id
}
SEP = "\t"   # TEMIST gold is usually TSV


def inspect(raw):
    files = glob.glob(os.path.join(raw, "**", "*.tsv"), recursive=True) + \
            glob.glob(os.path.join(raw, "**", "*.csv"), recursive=True)
    if not files:
        print("No .tsv/.csv found under", raw); return
    for f in files:
        try:
            df = pd.read_csv(f, sep=None, engine="python", nrows=5)
        except Exception as e:
            print(f"  ! could not read {f}: {e}"); continue
        print(f"\n=== {f}  ({df.shape[1]} cols) ===")
        print("  columns:", list(df.columns))
        print(df.head(3).to_string(index=False)[:800])


def build(raw, out, bench_files, n_sample, seed):
    os.makedirs(out, exist_ok=True)
    all_codes = set()
    for bench, path in bench_files.items():
        df = pd.read_csv(path, sep=SEP)
        need = {v for v in COLUMN_MAP.values()}
        missing = need - set(df.columns)
        if missing:
            sys.exit(f"[{bench}] missing columns {missing} in {path}; run --inspect and fix COLUMN_MAP")
        g = pd.DataFrame({
            "benchmark": bench,
            "mention_text": df[COLUMN_MAP["mention_text"]].astype(str),
            "gold_code": df[COLUMN_MAP["gold_code"]].astype(str),
            "semantic_rel": df[COLUMN_MAP["semantic_rel"]].astype(str).str.upper().str.strip(),
            "doc_id": df[COLUMN_MAP["doc_id"]].astype(str),
        })
        g = g[g["semantic_rel"].isin(["EXACT", "NARROW"])].reset_index(drop=True)
        g["mention_id"] = [f"{bench}_{i}" for i in range(len(g))]
        # fixed stratified-by-semantic_rel sample of n_sample, preserving prevalence
        if n_sample and len(g) > n_sample:
            frac = n_sample / len(g)
            g = (g.groupby("semantic_rel", group_keys=False)
                   .apply(lambda s: s.sample(max(1, round(len(s) * frac)), random_state=seed)))
            g = g.sort_values("mention_id").reset_index(drop=True)
        g.to_csv(os.path.join(out, f"corpus_{bench}.csv"), index=False)
        all_codes |= set(g["gold_code"])
        print(f"[{bench}] wrote corpus_{bench}.csv  n={len(g)} "
              f"(EXACT {int((g.semantic_rel=='EXACT').sum())}/NARROW {int((g.semantic_rel=='NARROW').sum())})")
    with open(os.path.join(out, "all_codes.txt"), "w") as f:
        f.write("\n".join(sorted(all_codes)))
    print(f"wrote all_codes.txt  ({len(all_codes)} unique gold codes)  -> feed to build_ontology_ols4.py")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--out", default="real_data")
    ap.add_argument("--inspect", action="store_true")
    ap.add_argument("--n_sample", type=int, default=800)
    ap.add_argument("--seed", type=int, default=20240101)
    a = ap.parse_args()
    if a.inspect:
        inspect(a.raw); sys.exit(0)
    # TODO-VERIFY: point each benchmark at its gold normalization file
    bench_files = {
        "DisTEMIST":  os.path.join(a.raw, "distemist_gold.tsv"),
        "MedProcNER": os.path.join(a.raw, "medprocner_gold.tsv"),
        "SympTEMIST": os.path.join(a.raw, "symptemist_gold.tsv"),
    }
    build(a.raw, a.out, bench_files, a.n_sample, a.seed)
