# Requirement: C-5, E-1
"""NER 교체 후보의 비용 — 상주 메모리(RSS)와 발화당 태깅 시간(CPU). 운영 서버 파드 상한 3Gi 와 대조하려고 잰다(로컬 참고값)."""
import json, resource, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "ai" / "apps"), str(ROOT / "server" / "apps")]
from pii_ner.adapter.outbound.koelectra_ner_tagger import KoElectraNerTagger  # noqa: E402
from huggingface_hub import snapshot_download  # noqa: E402
which = sys.argv[1]
path = ROOT / "models/koelectra-ner" if which == "naver" else Path(snapshot_download("vmaca123/korean-pii-ner-v3"))
import torch  # noqa: E402
base = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6
t = KoElectraNerTagger(path)
after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6
s = "네 제 이름은 홍길동이고요 주소는 서울시 중구 세종대로 110 이에요 등본 떼려고요"
t0 = time.time()
for _ in range(20): t.tag(s)
ms = (time.time() - t0) / 20 * 1000
out = {"model": which, "rss_added_mb": round(after - base), "ms_per_utterance_cpu": round(ms, 1),
       "params_m": round(sum(p.numel() for p in t._model.parameters()) / 1e6)}
print(json.dumps(out))
p = ROOT / "eval/review-2026-10/results/ner_candidate_cost.json"
prev = json.loads(p.read_text()) if p.exists() else {}
prev[which] = out; p.write_text(json.dumps(prev, ensure_ascii=False, indent=1))
