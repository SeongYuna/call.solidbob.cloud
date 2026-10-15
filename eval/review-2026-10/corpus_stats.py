# Requirement: E-1
"""심사 질문 2 — 검색 대상 코퍼스 크기·길이·KoE5 512토큰 초과 비율을 센다. 읽기만 한다."""
import json, statistics, sys, urllib.request
from transformers import AutoTokenizer

ES = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:9200/callguard-kb-single"
hits = json.load(urllib.request.urlopen(f"{ES}/_search?size=1000&_source_excludes=embedding,*vector*"))["hits"]["hits"]
tok = AutoTokenizer.from_pretrained("models/koe5")
docs = [h["_source"] for h in hits]
textkey = next(k for k in ("text", "content", "body", "chunk") if k in docs[0])
chars = [len(d[textkey]) for d in docs]
toks = [len(tok(d[textkey])["input_ids"]) for d in docs]
ids = {d.get("doc_id") for d in docs}
out = {"index": ES, "chunks": len(docs), "distinct_doc_ids": len(ids), "text_field": textkey,
       "chars": {"min": min(chars), "median": statistics.median(chars), "mean": round(statistics.mean(chars), 1), "max": max(chars)},
       "koe5_tokens": {"median": statistics.median(toks), "max": max(toks), "over_512": sum(t > 512 for t in toks)},
       "sroberta_128_over": sum(t > 128 for t in toks),
       "doc_id_prefix": {p: sum(1 for i in ids if i and i.startswith(p)) for p in ("DASAN-TERM", "DASAN-MANUAL", "DASAN-POLICY")}}
print(json.dumps(out, ensure_ascii=False, indent=1))
