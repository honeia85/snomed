#!/usr/bin/env python3
"""
build_ontology_ols4.py — build ontology.json (labels + transitive ancestors +
longest-path depth) from EBI OLS4 for a set of SNOMED CT codes.

  ┌─────────────────────────────────────────────────────────────────────────┐
  │ RUN THIS ONLY IN A SNOMED CT–LICENSED ENVIRONMENT.                        │
  │ The output is SNOMED-derived and requires a valid SNOMED CT Affiliate     │
  │ License to use/redistribute (per the manuscript's data statement).        │
  │ NOT run in the review sandbox for that reason. This is a template.        │
  └─────────────────────────────────────────────────────────────────────────┘

Input : all_codes.txt (one SNOMED CT identifier per line; from prep_inputs.py) —
        expand with each code's ancestors so Wu–Palmer denominators are complete.
Output: ontology.json  {code: {"depth": int, "ancestors": [codes incl. self], "label": str}}
        candidates_{B}.json labels can be emitted from the same label cache.

depth = longest path root→node over reconstructed is-a parent edges
        (matches the manuscript's convention).

OLS4 API: https://www.ebi.ac.uk/ols4/api  (endpoints/params can change — verify).
Be polite: cache, rate-limit, resume. Confirm SNOMED is exposed to your account.
"""
import argparse, json, os, time
import urllib.parse, urllib.request

OLS = "https://www.ebi.ac.uk/ols4/api"
ONT = "snomed"                      # verify the ontology id served to you
SLEEP = 0.2                          # rate limit


def _get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def _iri(code):
    # SNOMED IRIs in OLS are typically http://snomed.info/id/<code> — VERIFY.
    return f"http://snomed.info/id/{code}"

def term(code):
    iri = urllib.parse.quote(urllib.parse.quote(_iri(code), safe=""), safe="")  # DOUBLE-encode (OLS4 requires; single-encoding returns HTTP 400)
    return _get(f"{OLS}/ontologies/{ONT}/terms/{iri}")

def hierarchical_ancestors(code):
    iri = urllib.parse.quote(urllib.parse.quote(_iri(code), safe=""), safe="")  # DOUBLE-encode (OLS4 requires; single-encoding returns HTTP 400)
    codes, url = set(), f"{OLS}/ontologies/{ONT}/terms/{iri}/hierarchicalAncestors?size=200"
    while url:
        j = _get(url)
        for t in j.get("_embedded", {}).get("terms", []):
            c = t.get("obo_id") or t["iri"].rsplit("/", 1)[-1]
            codes.add(c)
        url = j.get("_links", {}).get("next", {}).get("href")
        time.sleep(SLEEP)
    return codes

def parents(code):
    iri = urllib.parse.quote(urllib.parse.quote(_iri(code), safe=""), safe="")  # DOUBLE-encode (OLS4 requires; single-encoding returns HTTP 400)
    try:
        j = _get(f"{OLS}/ontologies/{ONT}/terms/{iri}/hierarchicalParents?size=200")
    except Exception:
        return set()
    return {t.get("obo_id") or t["iri"].rsplit("/", 1)[-1]
            for t in j.get("_embedded", {}).get("terms", [])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--codes", required=True)
    ap.add_argument("--out", default="ontology.json")
    ap.add_argument("--cache", default="ols_cache.json")
    a = ap.parse_args()

    seed_codes = [l.strip() for l in open(a.codes) if l.strip()]
    cache = json.load(open(a.cache)) if os.path.exists(a.cache) else {"anc": {}, "par": {}, "lab": {}}

    # 1) expand: every gold code + all its ancestors must be in the graph
    frontier, universe = set(seed_codes), set(seed_codes)
    while frontier:
        c = frontier.pop()
        if c not in cache["anc"]:
            try:
                cache["anc"][c] = sorted(hierarchical_ancestors(c))
                cache["par"][c] = sorted(parents(c))
                cache["lab"][c] = term(c).get("label", c)
            except Exception as e:
                print("  ! skip", c, e); cache["anc"][c] = []; cache["par"][c] = []; cache["lab"][c] = c
            json.dump(cache, open(a.cache, "w"))
        for anc in cache["anc"][c]:
            if anc not in universe:
                universe.add(anc); frontier.add(anc)

    # 2) longest-path depth via memoized DFS over parent edges
    depth_memo = {}
    def depth(c, stack=()):
        if c in depth_memo: return depth_memo[c]
        par = [p for p in cache["par"].get(c, []) if p in universe and p not in stack]
        d = 0 if not par else 1 + max(depth(p, stack + (c,)) for p in par)
        depth_memo[c] = d; return d

    onto = {}
    for c in universe:
        anc = set(cache["anc"].get(c, [])) | {c}
        onto[c] = {"depth": depth(c), "ancestors": sorted(anc),
                   "label": cache["lab"].get(c, c)}
    json.dump(onto, open(a.out, "w"))
    print(f"wrote {a.out}: {len(onto)} concepts "
          f"(seed {len(seed_codes)} + ancestors); depth range "
          f"[{min(v['depth'] for v in onto.values())},{max(v['depth'] for v in onto.values())}]")
    print("Reminder: SNOMED-derived output — keep within your Affiliate License.")


if __name__ == "__main__":
    main()
