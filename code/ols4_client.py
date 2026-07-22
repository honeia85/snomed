#!/usr/bin/env python3
"""
ols4_client.py — build ontology.json (label + transitive ancestors + longest-path
depth) from EBI OLS4 live SNOMED CT. Verified against the real OLS4 API schema
(ontologyId 'snomed', baseUri http://snomed.info/id/, obo_id 'SNOMED:<code>',
double-URL-encoded term IRIs, hierarchicalParents with _links.next pagination).

Wave-parallel BFS (ThreadPoolExecutor) for a locally supplied identifier list.
Run this only in an environment covered by the user's applicable SNOMED CT licence;
generated identifiers, descriptions and maps are not part of the public release.

Usage:
  python3 ols4_client.py --codes all_codes.txt --out ontology.json
"""
import argparse, json, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

OLS = "https://www.ebi.ac.uk/ols4/api"
WORKERS = 8

def _get(url, tries=3):
    import time
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.load(r)
        except Exception:
            if k == tries - 1: raise
            time.sleep(0.4 * (k + 1))

def _term_url(code, suffix=""):
    iri = "http://snomed.info/id/" + str(code)
    enc = urllib.parse.quote(urllib.parse.quote(iri, safe=""), safe="")  # DOUBLE-encode
    return f"{OLS}/ontologies/snomed/terms/{enc}{suffix}"

def _code(obo, iri):
    return obo.split(":")[-1] if (obo and ":" in obo) else iri.rsplit("/", 1)[-1]

def get_label(code):
    try: return _get(_term_url(code)).get("label", str(code))
    except Exception: return str(code)

def get_parents(code):
    out, url = [], _term_url(code, "/hierarchicalParents?size=100")
    while url:
        j = _get(url)
        for t in j.get("_embedded", {}).get("terms", []):
            out.append((_code(t.get("obo_id"), t["iri"]), t.get("label", "")))
        url = j.get("_links", {}).get("next", {}).get("href")
    return out

def build(seed_codes, workers=WORKERS, verbose=True):
    parents, label = {}, {}
    frontier = set(str(c) for c in seed_codes)
    universe = set(frontier)
    with ThreadPoolExecutor(workers) as ex:
        wave = 0
        while frontier:
            res = list(ex.map(lambda c: (c, get_parents(c)), sorted(frontier)))
            newf = set()
            for c, pars in res:
                parents[c] = [p for p, _ in pars]
                for p, plab in pars:
                    if plab: label[p] = plab
                    if p not in universe:
                        universe.add(p); newf.add(p)
            wave += 1
            if verbose:
                print(f"  wave {wave}: +{len(newf)} new, universe={len(universe)}", file=sys.stderr)
            frontier = newf
        missing = [c for c in universe if c not in label]
        for c, lab in ex.map(lambda c: (c, get_label(c)), missing):
            label[c] = lab

    def ancestors(c, memo={}):
        if c in memo: return memo[c]
        acc = set()
        for p in parents.get(c, []):
            acc.add(p); acc |= ancestors(p, memo)
        memo[c] = acc; return acc
    def depth(c, memo={}, stack=()):
        if c in memo: return memo[c]
        par = [p for p in parents.get(c, []) if p not in stack]
        d = 0 if not par else 1 + max(depth(p, memo, stack + (c,)) for p in par)
        memo[c] = d; return d
    return {c: {"depth": depth(c), "ancestors": sorted(ancestors(c) | {c}),
                "label": label.get(c, c)} for c in universe}

def wu_palmer(pred, gold, onto):
    if pred == gold: return 1.0, pred
    if pred not in onto or gold not in onto: return 0.0, None
    common = set(onto[pred]["ancestors"]) & set(onto[gold]["ancestors"])
    if not common: return 0.0, None
    lca = max(common, key=lambda c: onto[c]["depth"])
    denom = onto[pred]["depth"] + onto[gold]["depth"]
    return ((2.0 * onto[lca]["depth"] / denom, lca) if denom else (0.0, None))

def relation(pred, gold, onto):
    if pred == gold: return "exact"
    if pred not in onto or gold not in onto: return "unresolved"
    ap, ag = set(onto[pred]["ancestors"]), set(onto[gold]["ancestors"])
    if pred in ag: return "ancestor"
    if gold in ap: return "descendant"
    return "sibling" if ap & ag else "unresolved"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--codes"); ap.add_argument("--out", default="ontology.json")
    ap.add_argument("--workers", type=int, default=WORKERS)
    a = ap.parse_args()
    if not a.codes: sys.exit("--codes is required")
    seeds = [l.strip() for l in open(a.codes) if l.strip()]
    if not seeds: sys.exit("--codes file contains no identifiers")
    onto = build(seeds, a.workers)
    json.dump(onto, open(a.out, "w"), ensure_ascii=False)
    ds = [v["depth"] for v in onto.values()]
    print(f"\nontology.json: {len(onto)} concepts (seeds {len(seeds)} + ancestors); "
          f"depth range [{min(ds)},{max(ds)}] -> {a.out}")

if __name__ == "__main__":
    main()
