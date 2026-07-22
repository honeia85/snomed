#!/usr/bin/env python3
# Score the Modal 5-system outputs against our ontology (local, pure-python).
#
# REPRODUCTION NOTE: the fastest reproduction path is the already-scored per-mention
# CSVs in ./per_mention/ (each row carries precomputed identifier-free metrics); Tables 2-3 and
# every statistic follow from those directly. This script only RE-DERIVES those CSVs
# from the raw Modal output (modal_out.json) against user-supplied per-benchmark ontology
# maps in ./ontology/. Those inputs are not deposited and must remain in a licensed private
# environment. It needs modal_out.json (the raw retriever/LLM/embedding output);
# if that file is not shipped, use the precomputed per_mention CSVs instead.
import json, os, csv, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ONTO = os.path.join(HERE, "ontology")          # deposited per-benchmark ancmap/depths maps
OUT  = HERE                                      # write per_mention/ next to this script
os.makedirs(f"{OUT}/per_mention", exist_ok=True)
data = json.load(open(f"{HERE}/modal_out.json"))
LLM, EMB = data["llm"], data["embed"]

def load_onto(b):
    dep = json.load(open(f"{ONTO}/{b}_depths.json"))
    anc = {k: set(v) for k, v in json.load(open(f"{ONTO}/{b}_ancmap.json")).items()}
    return dep, anc

def wup(pred, gold, dep, anc):
    pred, gold = str(pred), str(gold)
    if pred == gold: return 1.0
    if pred not in anc or gold not in anc: return 0.0
    common = (anc[pred] | {pred}) & (anc[gold] | {gold})
    if not common: return 0.0
    lca = max(common, key=lambda c: dep.get(c, 0)); dd = dep.get(pred, 0) + dep.get(gold, 0)
    return 0.0 if dd == 0 else 2 * dep.get(lca, 0) / dd

def relation(pred, gold, anc):
    pred, gold = str(pred), str(gold)
    if pred == gold: return "exact"
    if pred in anc.get(gold, set()): return "ancestor"
    if gold in anc.get(pred, set()): return "descendant"
    ap = anc.get(pred, set()) | {pred}; ag = anc.get(gold, set()) | {gold}
    return "sibling" if ap & ag else "unresolved"

def strat_gap(recs, rel):
    xs = [r for r in recs if r[2] == rel]
    if not xs: return None
    e = sum(r[0] for r in xs) / len(xs); w = sum(r[1] for r in xs) / len(xs)
    return w - e

BENCH_SYS = {
    "distemist":  ["lexical", "sapbert", "sapbert_ft", "llm_rerank", "llm_gen"],
    "medprocner": ["lexical", "sapbert", "llm_rerank", "llm_gen"],
    "symptemist": ["lexical", "sapbert", "sapbert_ft", "llm_rerank", "llm_gen"],
}
BENCH_META = {
    "distemist": ("DisTEMIST", "DIS"),
    "medprocner": ("MedProcNER", "MED"),
    "symptemist": ("SympTEMIST", "SYM"),
}

summary = []
for b in ["distemist", "medprocner", "symptemist"]:
    dep, anc = load_onto(b)
    ev = LLM[b]["eval"]                       # [{gold, rel, text_en}]
    golds = [str(e["gold"]) for e in ev]
    rels  = [e["rel"] for e in ev]
    spaces = LLM[b]["spaces"]
    for space in ["oracle", "train"]:
        codes_in_space = set(spaces[space])
        def top1_of(system):
            if system == "lexical":
                return [row[0] for row in LLM[b]["lexical"][space]]
            if system == "llm_gen":
                return LLM[b]["llm_gen"][space]
            if system == "llm_rerank":
                return LLM[b]["llm_rerank"][space]["top1"]
            if system in ("sapbert", "sapbert_ft"):
                return [row[0] for row in EMB[b][system][space]]
        for system in BENCH_SYS[b]:
            preds = top1_of(system)
            recs = []
            rows_csv = []
            for i, (p, g, rel) in enumerate(zip(preds, golds, rels), 1):
                p = str(p)
                ex = int(p == g); w = wup(p, g, dep, anc)
                rel_type = relation(p, g, anc)
                is_a = int(rel_type in {"exact", "ancestor", "descendant"})
                recs.append((ex, w, rel))
                bench_name, prefix = BENCH_META[b]
                rows_csv.append(dict(benchmark=bench_name, candidate_space=space,
                                     system=system, item_id=f"{prefix}-{i:04d}",
                                     semantic_rel=rel, exact=ex, is_a=is_a,
                                     wup=round(w, 4), relation_type=rel_type))
            n = len(recs)
            e = sum(r[0] for r in recs) / n; w = sum(r[1] for r in recs) / n
            gE = strat_gap(recs, "EXACT"); gN = strat_gap(recs, "NARROW")
            ratio = (gN / gE) if (gE and gN is not None) else float("nan")
            fb = ""
            if system == "llm_rerank":
                fbl = LLM[b]["llm_rerank"][space]["fallback"]
                fb = f"{sum(fbl)}/{len(fbl)}"
            summary.append(dict(benchmark=b, space=space, system=system, n=n,
                                exact=round(e, 3), wup=round(w, 3), uplift=round(w - e, 3),
                                gap_EXACT=round(gE, 3) if gE is not None else "",
                                gap_NARROW=round(gN, 3) if gN is not None else "",
                                ratio=round(ratio, 3) if ratio == ratio else "",
                                n_codes=len(codes_in_space), rerank_fallback=fb))
            with open(f"{OUT}/per_mention/{b}_{space}_{system}_per_mention.csv", "w", newline="") as f:
                wr = csv.DictWriter(f, fieldnames=["benchmark", "candidate_space", "system",
                                                   "item_id", "semantic_rel", "exact", "is_a",
                                                   "wup", "relation_type"])
                wr.writeheader(); wr.writerows(rows_csv)

cols = ["benchmark", "space", "system", "n", "exact", "wup", "uplift",
        "gap_EXACT", "gap_NARROW", "ratio", "n_codes", "rerank_fallback"]
with open(f"{OUT}/summary_by_space_5sys.csv", "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=cols); wr.writeheader(); wr.writerows(summary)

# pretty print oracle->train per system
print(f"{'bench':10} {'system':11} {'exact O→T':>14} {'uplift O→T':>14} {'ratio O→T':>16}")
bycell = collections.defaultdict(dict)
for r in summary:
    bycell[(r["benchmark"], r["system"])][r["space"]] = r
for (b, s), d in bycell.items():
    o, t = d.get("oracle"), d.get("train")
    if not (o and t): continue
    print(f"{b:10} {s:11} {o['exact']:>6}→{t['exact']:<6} {o['uplift']:>6}→{t['uplift']:<6} "
          f"{str(o['ratio']):>7}→{str(t['ratio']):<7}")
print("\nwrote", f"{OUT}/summary_by_space_5sys.csv")
