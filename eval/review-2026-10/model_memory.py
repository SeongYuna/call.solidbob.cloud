# Requirement: E-1
"""심사 질문 20 — 서버 프로세스가 싣는 두 모델(KoE5 · koelectra NER)을 CPU 로 올렸을 때의 상주 메모리(RSS)를 잰다(로컬 맥, 참고값)."""
import json, resource, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "ai" / "apps"), str(ROOT / "server" / "apps")]
def rss_mb(): return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6  # macOS: bytes
out = {"python_baseline_mb": round(rss_mb())}
import torch  # noqa
out["after_torch_mb"] = round(rss_mb())
from retrieval.adapter.outbound.koe5_embedder import KoE5Embedder
e = KoE5Embedder(ROOT / "models/koe5"); e.embed_queries(["주민등록등본 발급에 필요한 서류"])
out["after_koe5_mb"] = round(rss_mb())
from pii_ner.adapter.outbound.koelectra_ner_tagger import KoElectraNerTagger
t = KoElectraNerTagger(ROOT / "models/koelectra-ner"); t.tag("홍길동 고객님 주소는 서울시 중구입니다")
out["after_koelectra_ner_mb"] = round(rss_mb())
out["files_on_disk"] = {"koe5": "2.1G", "koelectra-ner": "429M", "kanana-1.5-2.1b q4_k_m gguf": "1.5G (Ollama 별도 프로세스)", "bge-reranker-v2-m3": "2.1G (운영 미탑재)"}
print(json.dumps(out, ensure_ascii=False))
(ROOT / "eval/review-2026-10/results/model_memory.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
