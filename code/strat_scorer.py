"""
strat_scorer.py — canonical hierarchy-aware stratified scorer for the SNOMED-CT
normalization project. Shared across ALL benchmarks (DisTEMIST, MedProcNER,
SympTEMIST, MedMentions, Mantra) so every result table uses identical metric code.

Metrics per (pred, gold): exact, is-a, Wu-Palmer, LCA path-distance, CoPHE Jaccard.
Requires an ancestor map {code:[ancestors]} and graph depths {code:int} (longest
path from root). Codes missing from BOTH maps score 0 credit on non-exact (disclose count).
"""
import json

def load_maps(ancmap_path, depths_path):
    with open(ancmap_path) as f: ancmap = json.load(f)
    with open(depths_path) as f: depths = json.load(f)
    depths = {str(k): int(v) for k, v in depths.items()}
    ancmap = {str(k): [str(a) for a in v] for k, v in ancmap.items()}
    return ancmap, depths

class StratScorer:
    def __init__(self, ancmap, depths):
        self.ancmap = ancmap
        self.depths = depths
        self.MAXDEPTH = max(depths.values()) if depths else 1

    def aug(self, x):
        return set(self.ancmap.get(x, [])) | {x}

    def resolved(self, x):
        return (x in self.ancmap) and (x in self.depths)

    def isa(self, pred, gold):
        # pred in ancestors(gold) ∪ descendants(gold) ∪ {gold}
        if pred == gold: return 1.0
        if gold in self.ancmap.get(pred, []): return 1.0   # pred is descendant of gold
        if pred in self.ancmap.get(gold, []): return 1.0   # pred is ancestor of gold
        return 0.0

    def lca_depth(self, pred, gold):
        common = self.aug(pred) & self.aug(gold)
        ds = [self.depths[c] for c in common if c in self.depths]
        return max(ds) if ds else None

    def score_row(self, pred, gold):
        """returns dict(exact, isa, wup, lca_dist, cophe_jaccard)."""
        pred, gold = str(pred), str(gold)
        if pred == gold:
            return dict(exact=1.0, isa=1.0, wup=1.0, lca_dist=1.0, cophe_jaccard=1.0)
        isa = self.isa(pred, gold)
        if not (self.resolved(pred) and self.resolved(gold)):
            return dict(exact=0.0, isa=isa, wup=0.0, lca_dist=0.0, cophe_jaccard=0.0)
        dp, dg = self.depths[pred], self.depths[gold]
        dl = self.lca_depth(pred, gold)
        if dl is None:
            return dict(exact=0.0, isa=isa, wup=0.0, lca_dist=0.0, cophe_jaccard=0.0)
        wup = (2*dl / (dp + dg)) if (dp + dg) > 0 else 0.0
        dist = dp + dg - 2*dl
        lca_credit = max(0.0, 1.0 - dist / (2*self.MAXDEPTH))
        ap, ag = self.aug(pred), self.aug(gold)
        cophe = len(ap & ag) / len(ap | ag)
        return dict(exact=0.0, isa=isa, wup=wup, lca_dist=lca_credit, cophe_jaccard=cophe)

def bucket(gold, train_codes, ancmap):
    """seen/novel stratification vs a set of training codes."""
    gold = str(gold)
    if gold in train_codes: return "1_code_seen"
    if any(a in train_codes for a in ancmap.get(gold, [])): return "2_novel_ancestor_seen"
    return "3_isolated"

def credit_gap_by_rel(df, rel_col="semantic_rel"):
    """df must have columns: system, <rel_col>, exact, wup. Returns per (system,rel) gap."""
    import pandas as pd
    g = df.groupby(["system", rel_col]).agg(n=("exact","size"), exact=("exact","mean"),
                                            wup=("wup","mean")).reset_index()
    g["gap"] = g["wup"] - g["exact"]
    return g
