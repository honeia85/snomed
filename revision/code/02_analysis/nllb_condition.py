# -*- coding: utf-8 -*-
"""m1: reproduce the NLLB-200 translation condition with the same metric pipeline as the main analysis.
NLLB translates the Spanish mentions; SapBERT retrieves in the same candidate space; exact/is-a/Wu-Palmer computed."""
import json, os, math, csv, argparse, time
import numpy as np, torch
from transformers import AutoTokenizer, AutoModel, AutoModelForSeq2SeqLM

def wup(p,g,depth,anc):
    if p==g: return 1.0
    dp,dg=depth.get(p),depth.get(g)
    if dp is None or dg is None: return 0.0
    common=(set(anc.get(p,[]))|{p})&(set(anc.get(g,[]))|{g})
    if not common: return 0.0
    lca=max(common,key=lambda c:depth.get(c,0))
    return 2.0*depth.get(lca,0)/(dp+dg) if dp+dg else 0.0

def isa(p,g,anc):
    if p==g: return 1
    return int(p in set(anc.get(g,[])) or g in set(anc.get(p,[])))

def mh(cells):
    num=den=0.0
    for a,n1,c,n0 in cells:
        N=n1+n0
        if N==0: continue
        num+=a*n0/N; den+=c*n1/N
    return num/den if den else float('nan')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--data', default='./bundle')
    ap.add_argument('--out', default='./out_nllb')
    args=ap.parse_args(); os.makedirs(args.out, exist_ok=True)
    dev='cuda' if torch.cuda.is_available() else 'cpu'
    print('device', dev, flush=True)
    t0=time.time()
    ntok=AutoTokenizer.from_pretrained('facebook/nllb-200-distilled-600M')
    nmdl=AutoModelForSeq2SeqLM.from_pretrained('facebook/nllb-200-distilled-600M').to(dev).eval()
    stok=AutoTokenizer.from_pretrained('cambridgeltl/SapBERT-from-PubMedBERT-fulltext')
    smdl=AutoModel.from_pretrained('cambridgeltl/SapBERT-from-PubMedBERT-fulltext').to(dev).eval()
    print('models loaded', round(time.time()-t0), flush=True)
    eng=ntok.convert_tokens_to_ids('eng_Latn'); ntok.src_lang='spa_Latn'
    def translate(texts, bs=32):
        out=[]
        for i in range(0,len(texts),bs):
            enc=ntok(texts[i:i+bs], return_tensors='pt', padding=True, truncation=True, max_length=64).to(dev)
            with torch.no_grad():
                gen=nmdl.generate(**enc, forced_bos_token_id=eng, max_length=64, num_beams=1)
            out+=ntok.batch_decode(gen, skip_special_tokens=True)
        return out
    def embed(texts, bs=128):
        out=[]
        for i in range(0,len(texts),bs):
            enc=stok(texts[i:i+bs], padding=True, truncation=True, max_length=32, return_tensors='pt').to(dev)
            with torch.no_grad(): rep=smdl(**enc)[0][:,0,:]
            out.append(rep.cpu().numpy())
        return np.vstack(out)
    res={}; pooled=[]
    for b in ['distemist','medprocner','symptemist']:
        ms=[json.loads(l) for l in open(os.path.join(args.data,f'mentions_{b}.jsonl'), encoding='utf-8')]
        sp=json.load(open(os.path.join(args.data,f'space_published_{b}.json'), encoding='utf-8'))
        keep=set(sp); ms=[m for m in ms if m['gold'] in keep]
        codes=[c for c in sp if sp[c].get('label_en')]
        labels=[sp[c]['label_en'] for c in codes]
        print(b, 'mentions', len(ms), 'candidates', len(codes), flush=True)
        en=translate([m['text_es'] for m in ms])
        json.dump(en, open(os.path.join(args.out, f'{b}_nllb_translations.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        C=embed(labels); M=embed(en)
        C=C/(np.linalg.norm(C,axis=1,keepdims=True)+1e-8); M=M/(np.linalg.norm(M,axis=1,keepdims=True)+1e-8)
        top=np.argsort(-(M@C.T),axis=1)[:,:5]
        depth={c:(sp[c].get('depth') or 0) for c in codes}; anc={c:sp[c].get('ancestors',[]) for c in codes}
        rows=[]
        for i,m in enumerate(ms):
            top1=codes[top[i][0]]
            rows.append(dict(mention_id=m['mention_id'], gold=m['gold'], semrel=m['semrel'], pred1=top1,
                             exact=int(top1==m['gold']), isa=isa(top1,m['gold'],anc), wup=round(wup(top1,m['gold'],depth,anc),4)))
        with open(os.path.join(args.out,f'predictions_{b}_nllb_sapbert.csv'),'w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        cells={}
        for r in rows:
            if r['semrel'] not in ('EXACT','NARROW'): continue
            d=cells.setdefault(r['semrel'],[0,0]); d[0]+=1; d[1]+=1-r['exact']
        n1,a=cells.get('NARROW',[0,0]); n0,c=cells.get('EXACT',[0,0])
        rr=(a/n1)/(c/n0) if n1 and n0 and c else float('nan')
        res[b]=dict(n_NARROW=n1, rate_NARROW=round(a/n1,4) if n1 else None, n_EXACT=n0, rate_EXACT=round(c/n0,4) if n0 else None,
                    risk_ratio=round(rr,4) if rr==rr else None, space=len(codes))
        pooled.append((a,n1,c,n0))
        print(b, res[b], flush=True)
    res['pooled_MH_RR']=round(mh(pooled),4)
    json.dump(res, open(os.path.join(args.out,'results_nllb.json'),'w'), indent=1)
    print('pooled', res['pooled_MH_RR'], 'elapsed', round(time.time()-t0), flush=True)
if __name__=='__main__':
    main()
