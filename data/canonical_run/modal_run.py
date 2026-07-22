# ============================================================================
# Full 5-system candidate-space re-run on Modal (A100-80GB), faithful recipe.
#   - Qwen2.5-32B-Instruct (rev 5ede1c97, greedy) via vLLM:
#       * translate Spanish mentions -> English (paper protocol)
#       * LLM reranker: rerank top-20 lexical candidates -> 5 best SNOMED IDs
#       * LLM generator: propose a concept name -> WRatio fuzzy-match to space
#   - SapBERT base + fine-tuned (in-batch symmetric MNRL) on English pairs
#   - lexical TF-IDF (char 2-4)
# Systems: distemist/symptemist = 5 (incl sapbert_ft); medprocner = 4 (paper).
# Spaces: oracle (train+test gold) vs train (train gold only).
# Prompts are RECONSTRUCTED from the manuscript Methods (repo ships none).
# Scoring is done locally by the caller (this file only produces predictions).
# ============================================================================
import json, os, re, modal

MODEL = "Qwen/Qwen2.5-32B-Instruct"
REVISION = "5ede1c97"                 # manuscript-pinned; falls back to main if unresolved
BENCHES = ["distemist", "medprocner", "symptemist"]
FT_BENCHES = {"distemist", "symptemist"}   # paper: medprocner reports 4 systems
TOPK = 20
SAPBERT = "cambridgeltl/SapBERT-from-PubMedBERT-fulltext"
LOCAL_INPUTS = os.path.join(os.path.dirname(__file__), "modal_inputs")

app = modal.App("snomed-5sys-rerun")
hf_cache = modal.Volume.from_name("hf-cache", create_if_missing=True)

llm_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("vllm==0.6.6.post1", "scikit-learn", "rapidfuzz", "numpy", "transformers")
    .add_local_dir(LOCAL_INPUTS, remote_path="/inputs")
)
embed_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("sentence-transformers==3.3.1", "scikit-learn", "numpy", "torch",
                 "datasets", "accelerate")
    .add_local_dir(LOCAL_INPUTS, remote_path="/inputs")
)

# --------------------------------------------------------------- shared loaders
def _load_corpus(bench):
    return json.load(open(f"/inputs/corpus_cache/{bench}_corpus.json"))

def _load_labels(bench):
    return json.load(open(f"/inputs/ontology/{bench}_labels.json"))

_EVAL_SPEC = {
    "distemist":  dict(file="distemist_5sys_preds.csv", key="span", text="span", gold="gold", rel="semantic_rel", offset=False),
    "medprocner": dict(file="mp_per_example.csv",       key="text", text="text", gold="gold", rel="sem_rel",      offset=False),
    "symptemist": dict(file="symptemist_per_example.csv", key="span", text=None, gold="gold", rel="semantic_rel", offset=True),
}

def _load_eval(bench, corpus):
    import csv
    spec = _EVAL_SPEC[bench]
    seen, out = set(), []
    with open(f"/inputs/eval/{spec['file']}", newline="", encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            k, g, rel = r[spec["key"]], r[spec["gold"]], r[spec["rel"]]
            if (k, g) in seen:
                continue
            seen.add((k, g))
            if spec["offset"]:
                txt = corpus["offset2text"].get(k) or corpus["offset2text"].get(re.sub(r"^[a-z]{2}-", "", k))
                if txt is None:
                    continue
            else:
                txt = r[spec["text"]]
            out.append(dict(text_es=txt, gold=g, rel=rel))
    return out

def _spaces(bench, corpus, eval_golds):
    train = set(corpus["train_codes"])
    test = set(corpus["test_codes"]) | set(eval_golds)
    labels = _load_labels(bench)
    return {"oracle": sorted((train | test) & set(labels)),
            "train":  sorted(train & set(labels))}

# --------------------------------------------------------------- LLM stage
@app.function(image=llm_image, gpu="A100-80GB", volumes={"/root/.cache/huggingface": hf_cache},
              timeout=60 * 60, retries=0)
def llm_stage():
    import numpy as np
    from vllm import LLM, SamplingParams
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import linear_kernel
    from rapidfuzz import process, fuzz

    def log(*a): print("[llm]", *a, flush=True)
    try:
        llm = LLM(model=MODEL, revision=REVISION, dtype="bfloat16",
                  gpu_memory_utilization=0.92, max_model_len=4096, enforce_eager=False)
        log("loaded", MODEL, "rev", REVISION)
    except Exception as e:
        log("revision failed, using main:", repr(e)[:200])
        llm = LLM(model=MODEL, dtype="bfloat16", gpu_memory_utilization=0.92, max_model_len=4096)
    tok = llm.get_tokenizer()

    def chat(user_msgs, max_tokens):
        prompts = [tok.apply_chat_template([{"role": "user", "content": u}],
                                           tokenize=False, add_generation_prompt=True) for u in user_msgs]
        sp = SamplingParams(temperature=0.0, max_tokens=max_tokens)
        outs = llm.generate(prompts, sp)
        return [o.outputs[0].text.strip() for o in outs]

    T_PROMPT = ("Translate this Spanish clinical term to English. "
                "Output only the English translation, nothing else.\n\nSpanish: {es}\nEnglish:")
    G_PROMPT = ("What is the single best SNOMED CT concept name for this clinical mention? "
                "Output only the concept name, with no explanation.\n\nMention: {m}\nConcept name:")
    def R_PROMPT(m, cand):
        lines = "\n".join(f"{c}\t{lab}" for c, lab in cand)
        return ("A clinical mention must be mapped to a SNOMED CT concept. From the candidate "
                "concepts below, list the 5 best-matching SNOMED CT identifiers, best first, as a "
                "comma-separated list of the numeric IDs only.\n\n"
                f"Mention: {m}\n\nCandidates (id<TAB>name):\n{lines}\n\nBest 5 IDs:")

    result = {}
    # 1) gather all Spanish strings to translate (eval + ft train mentions), dedup
    per = {}
    to_translate = set()
    for b in BENCHES:
        corpus = _load_corpus(b)
        ev = _load_eval(b, corpus)
        per[b] = dict(corpus=corpus, eval=ev)
        for e in ev:
            to_translate.add(e["text_es"])
        if b in FT_BENCHES:
            for txt, code in corpus["train_pairs"]:
                if txt:
                    to_translate.add(txt)
    uniq = sorted(to_translate)
    log(f"translating {len(uniq)} unique Spanish strings ...")
    tr = {}
    for i in range(0, len(uniq), 1024):
        chunk = uniq[i:i + 1024]
        outs = chat([T_PROMPT.format(es=s) for s in chunk], 64)
        for s, o in zip(chunk, outs):
            tr[s] = o.split("\n")[0].strip() or s
        log(f"  translated {min(i+1024,len(uniq))}/{len(uniq)}")

    for b in BENCHES:
        corpus = per[b]["corpus"]; ev = per[b]["eval"]
        labels = _load_labels(b)
        for e in ev:
            e["text_en"] = tr.get(e["text_es"], e["text_es"])
        golds = [e["gold"] for e in ev]
        mentions_en = [e["text_en"] for e in ev]
        spaces = _spaces(b, corpus, golds)

        # lexical top-20 per space (char n-gram TF-IDF on English labels)
        lex = {}
        for sp_name, codes in spaces.items():
            vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True)
            C = vec.fit_transform([labels[c] for c in codes])
            M = vec.transform(mentions_en)
            rows = []
            for i in range(0, M.shape[0], 512):
                sim = linear_kernel(M[i:i + 512], C)
                rows.append(np.argsort(-sim, axis=1)[:, :TOPK])
            idx = np.vstack(rows)
            lex[sp_name] = [[codes[j] for j in row] for row in idx]
        log(f"{b}: lexical done")

        # LLM generator: propose a concept name (space-independent), then WRatio -> each space
        gen_names = chat([G_PROMPT.format(m=m) for m in mentions_en], 32)
        gen_names = [g.split("\n")[0].strip() for g in gen_names]
        gen = {}
        for sp_name, codes in spaces.items():
            choices = {c: labels[c] for c in codes}
            names = list(choices.values()); code_list = list(choices.keys())
            preds = []
            for gname in gen_names:
                m = process.extractOne(gname, names, scorer=fuzz.WRatio)
                preds.append(code_list[m[2]] if m else code_list[0])
            gen[sp_name] = preds
        log(f"{b}: generator done")

        # LLM reranker: rerank the top-20 lexical candidates per space
        rer = {}
        for sp_name, codes in spaces.items():
            cand_lists = lex[sp_name]
            prompts = [R_PROMPT(mentions_en[i], [(c, labels[c]) for c in cand_lists[i][:TOPK]])
                       for i in range(len(mentions_en))]
            outs = chat(prompts, 64)
            top1, top5, fb = [], [], []
            for i, o in enumerate(outs):
                ids = re.findall(r"\d+", o)
                candset = set(cand_lists[i])
                valid = [x for x in ids if x in candset]
                if valid:
                    top1.append(valid[0]); top5.append(valid[:5]); fb.append(False)
                else:
                    top1.append(cand_lists[i][0]); top5.append(cand_lists[i][:5]); fb.append(True)
            rer[sp_name] = dict(top1=top1, top5=top5, fallback=fb)
        fbrate = ", ".join(f"{k}:{sum(v['fallback'])}/{len(v['fallback'])}" for k, v in rer.items())
        log(f"{b}: reranker done (fallback {fbrate})")

        ft_pairs_en = []
        if b in FT_BENCHES:
            for txt, code in corpus["train_pairs"]:
                if txt and code in labels:
                    ft_pairs_en.append([tr.get(txt, txt), labels[code]])

        result[b] = dict(
            eval=[{"gold": e["gold"], "rel": e["rel"], "text_en": e["text_en"]} for e in ev],
            spaces=spaces, mentions_en=mentions_en,
            lexical={k: [row[:1] for row in v] for k, v in lex.items()},   # top1 for scoring
            lexical_top5={k: [row[:5] for row in v] for k, v in lex.items()},
            llm_gen=gen, gen_names=gen_names,
            llm_rerank={k: {"top1": v["top1"], "top5": v["top5"], "fallback": v["fallback"]} for k, v in rer.items()},
            ft_pairs_en=ft_pairs_en, do_ft=(b in FT_BENCHES),
        )
    return result

# --------------------------------------------------------------- SapBERT stage
@app.function(image=embed_image, gpu="A10G", volumes={"/root/.cache/huggingface": hf_cache}, timeout=60 * 60)
def embed_stage(payload):
    import numpy as np, torch
    from sentence_transformers import SentenceTransformer, losses
    def log(*a): print("[embed]", *a, flush=True)

    def embed(model, texts, bs=128):
        return model.encode(texts, batch_size=bs, convert_to_numpy=True,
                            normalize_embeddings=True, show_progress_bar=False)

    def topk_codes(M, C, codes, k=5):
        out = []
        for i in range(0, len(M), 512):
            sim = M[i:i + 512] @ C.T
            out.append(np.argsort(-sim, axis=1)[:, :k])
        idx = np.vstack(out)
        return [[codes[j] for j in row] for row in idx]

    def finetune(pairs):
        from datasets import Dataset
        from sentence_transformers import SentenceTransformerTrainer, SentenceTransformerTrainingArguments
        m = SentenceTransformer(SAPBERT)
        loss = losses.MultipleNegativesSymmetricRankingLoss(m, scale=20.0)
        ds = Dataset.from_dict({"anchor": [a for a, _ in pairs], "positive": [b for _, b in pairs]})
        args = SentenceTransformerTrainingArguments(
            output_dir="/tmp/ft", num_train_epochs=3, per_device_train_batch_size=32,
            learning_rate=2e-5, fp16=True, save_strategy="no", report_to=[], logging_steps=1000,
            seed=20260718, dataloader_drop_last=True)
        SentenceTransformerTrainer(model=m, args=args, train_dataset=ds, loss=loss).train()
        return m

    base = SentenceTransformer(SAPBERT)
    out = {}
    for b, d in payload.items():
        labels = json.load(open(f"/inputs/ontology/{b}_labels.json"))
        mentions = d["mentions_en"]; spaces = d["spaces"]
        Mb = embed(base, mentions)
        res = {"sapbert": {}}
        for sp_name, codes in spaces.items():
            C = embed(base, [labels[c] for c in codes])
            res["sapbert"][sp_name] = topk_codes(Mb, C, codes)
        if d["do_ft"] and d["ft_pairs_en"]:
            log(f"{b}: fine-tuning on {len(d['ft_pairs_en'])} pairs")
            ft = finetune([tuple(p) for p in d["ft_pairs_en"]])
            Mf = embed(ft, mentions)
            res["sapbert_ft"] = {}
            for sp_name, codes in spaces.items():
                C = embed(ft, [labels[c] for c in codes])
                res["sapbert_ft"][sp_name] = topk_codes(Mf, C, codes)
        out[b] = res
        log(f"{b}: embed done")
    return out

# --------------------------------------------------------------- orchestrate
@app.local_entrypoint()
def main():
    import json as _json
    print("launching llm_stage (A100-80GB) ...", flush=True)
    llm = llm_stage.remote()
    payload = {b: {"mentions_en": llm[b]["mentions_en"], "spaces": llm[b]["spaces"],
                   "ft_pairs_en": llm[b]["ft_pairs_en"], "do_ft": llm[b]["do_ft"]}
               for b in llm}
    print("launching embed_stage (A10G) ...", flush=True)
    emb = embed_stage.remote(payload)
    out = {"llm": llm, "embed": emb}
    dst = os.path.join(os.path.dirname(__file__), "modal_out.json")
    _json.dump(out, open(dst, "w"))
    print("wrote", dst, flush=True)
