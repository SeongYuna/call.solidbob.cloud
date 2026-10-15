# Requirement: B-2, E-1
"""조항 검색 학습 데이터 생성(doc2query) — 지식베이스 조항마다 시민이 다산콜센터에 할 법한 질문을 로컬 LLM(kanana, Ollama)으로 만든다.
**골든셋은 쓰지 않는다**(평가 전용). 생성된 질문 중 골든셋 질의와 같은 문장은 버린다(누수 차단). 결과: data/processed/train/retrieval-queries.jsonl
"""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "ai" / "apps"), str(ROOT / "server" / "apps")]
from evaluation.golden_set import load_golden_set  # noqa: E402
from evaluation.harness import retrieval_query  # noqa: E402
from generation.adapter.outbound.ollama_chat import OllamaChat  # noqa: E402
from retrieval.adapter.outbound.knowledge_base_loader import load_chunks  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 8
chat = OllamaChat("http://localhost:11434", model="kanana-1.5-2.1b-instruct:q4_k_m", num_predict=400, timeout_s=60, seed=20261015)
SCHEMA = {"type": "object", "properties": {"questions": {"type": "array", "items": {"type": "string"}, "minItems": N, "maxItems": N}}, "required": ["questions"]}
norm = lambda s: re.sub(r"[\s\W]+", "", s)
gold = {norm(retrieval_query(it)) for it in load_golden_set() if it.module in ("B", "B-6")}
out = ROOT / "data/processed/train/retrieval-queries.jsonl"; out.parent.mkdir(parents=True, exist_ok=True)
kept = dropped = 0
with out.open("w", encoding="utf-8") as f:
    for c in load_chunks(ROOT / "knowledge-base"):
        msgs = [{"role": "system", "content": f"너는 서울 120 다산콜센터에 전화한 시민이다. 아래 안내 조항이 답이 되는 질문을 서로 다른 말투로 {N}개 만든다. 구어체·짧은 말·앞뒤 맥락 없는 말·오타 섞인 말을 고루 섞는다. 조항 제목을 그대로 베끼지 않는다."},
                {"role": "user", "content": f"조항 제목: {c.title}\n조항 내용: {c.text}"}]
        try:
            qs = json.loads(chat.chat(msgs, schema=SCHEMA).content)["questions"]
        except Exception as e:  # noqa: BLE001
            print("실패", c.chunk_id, type(e).__name__); continue
        for q in qs:
            q = q.strip()
            if not q or norm(q) in gold:
                dropped += 1; continue
            f.write(json.dumps({"query": q, "doc_id": c.doc_id, "chunk_id": c.chunk_id}, ensure_ascii=False) + "\n"); kept += 1
        print(c.chunk_id, len(qs), flush=True)
print(json.dumps({"kept": kept, "dropped_same_as_golden_or_empty": dropped, "out": str(out)}, ensure_ascii=False))
