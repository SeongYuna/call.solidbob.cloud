#!/usr/bin/env python3
# Requirement: B-2
"""지식베이스 → 청크 목록 덤프 (w2-kb-index).

골든셋 라벨링이 이 목록을 보고 정답 문서 ID 를 고른다. 같은 입력이면 항상 같은 결과가
나오므로(정렬된 순회) diff 로 변경분을 확인할 수 있다.

    .venv/bin/python scripts/index_knowledge_base.py                 # 요약만
    .venv/bin/python scripts/index_knowledge_base.py --out data/processed/kb-chunks.json

ES 적재(2026-08-27 추가). 기본은 `single` — 인덱스 하나 + `domain` 필터다
(`_project/decisions/017`). `per-domain` 은 도메인이 늘었을 때를 대비해 남겨 둔 경로다.

    # ES 9.5.1 + nori — 컴포즈는 걷어냈다(decisions/107). 자세한 것은 infra/README.md
    docker run -d --name callguard-elasticsearch -p 127.0.0.1:9200:9200 \
      -e discovery.type=single-node -e xpack.security.enabled=false \
      -e ES_JAVA_OPTS="-Xms512m -Xmx512m" seongyuna/callguard-es:9.5.1
    export ELASTICSEARCH_URL=http://localhost:9200
    .venv/bin/python scripts/index_knowledge_base.py --to-es --recreate
    .venv/bin/python scripts/index_knowledge_base.py --to-es            # 재적재 재현 확인
    .venv/bin/python scripts/index_knowledge_base.py --to-es --layout per-domain --recreate

`--to-es` 없이 돌리면 예전과 똑같이 요약(과 `--out` 덤프)만 낸다.

**임베딩(2026-09-15, `w4-dense-vector-index`)** — `--to-es` 가 본문과 KoE5 임베딩을 **한 번에** 넣는다.
모델(`models/koe5`)이나 torch 가 없으면 **BM25 만 적재하고 그 사실을 찍는다** — 운영 서버 파드(런북 15-1)는
torch 가 없어 이 경로로 간다. 벡터 없는 인덱스에서 dense·하이브리드 검색은 결과가 0건이다.

    .venv/bin/python scripts/index_knowledge_base.py --to-es --recreate               # 본문 + 임베딩
    .venv/bin/python scripts/index_knowledge_base.py --to-es --recreate --no-embed    # BM25 만
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ai" / "apps"))  # 2026-08-26 fastapi/ → server/·ai/ 분리 반영

from retrieval.adapter.outbound import es_index  # noqa: E402
from retrieval.adapter.outbound.knowledge_base_loader import load_chunks  # noqa: E402
from retrieval.domain.services.chunking import MAX_CHARS  # noqa: E402


def _es_client():
    """ES 클라이언트를 만든다. 설정을 읽는 곳은 여기 한 곳뿐이다.

    `ai/` 에는 config 모듈이 없고 `server/core/config.py` 는 import 경로 밖이다
    (`ai/pytest.ini` 의 pythonpath 는 `../server/apps` 까지만 올린다). 어댑터가 환경변수를
    직접 읽으면 테스트에서 갈아끼울 수 없으므로, 스크립트가 읽어 주입한다.
    """
    url = os.environ.get("ELASTICSEARCH_URL")
    if not url:
        raise SystemExit(
            "ELASTICSEARCH_URL 이 비어 있다. .env 를 읽었는지 확인하거나 직접 지정한다:\n"
            "  export ELASTICSEARCH_URL=http://localhost:9200"
        )
    try:
        from elasticsearch import Elasticsearch
    except ModuleNotFoundError:
        raise SystemExit(
            "elasticsearch 패키지가 없다:  pip install -r ai/requirements.txt"
        ) from None

    api_key = os.environ.get("ELASTICSEARCH_API_KEY") or None
    return Elasticsearch(url, api_key=api_key) if api_key else Elasticsearch(url)


def main() -> int:
    ap = argparse.ArgumentParser(description="지식베이스를 조항 단위 청크로 자른다")
    ap.add_argument("--kb", type=Path, default=ROOT / "knowledge-base")
    ap.add_argument("--out", type=Path, help="청크 목록을 JSON 으로 저장할 경로")
    ap.add_argument("--max-chars", type=int, default=MAX_CHARS)
    ap.add_argument("--to-es", action="store_true", help="Elasticsearch 에 적재한다")
    ap.add_argument(
        "--layout",
        choices=es_index.LAYOUTS,
        default="single",
        help="single(기본): 한 인덱스 + domain 필터 / per-domain: 도메인별 인덱스 4개 (전환 대비)",
    )
    ap.add_argument("--recreate", action="store_true", help="인덱스를 지우고 다시 만든다")
    ap.add_argument("--embed-model", type=Path, default=ROOT / "models" / "koe5",
                    help="KoE5 모델 디렉터리 (decisions/010). 없으면 BM25 만 적재한다")
    ap.add_argument("--no-embed", action="store_true", help="임베딩 없이 BM25 필드만 적재한다")
    ap.add_argument("--device", default=None, help="임베딩 장치 (기본 cpu — mps·cuda 는 명시)")
    args = ap.parse_args()

    if (args.recreate or args.layout != "single") and not args.to_es:
        ap.error("--layout / --recreate 는 --to-es 와 함께 쓴다")

    chunks = load_chunks(args.kb, max_chars=args.max_chars)

    by_domain = Counter(c.domain for c in chunks)
    by_type = Counter(c.doc_type for c in chunks)
    split = [c for c in chunks if c.chunk_id != c.doc_id]
    lengths = sorted(len(c.text) for c in chunks)

    print(f"청크 {len(chunks)}개 (조항 {len({c.doc_id for c in chunks})}개, 상한 {args.max_chars}자)")
    print("  도메인별:", dict(by_domain))
    print("  문서종류별:", dict(by_type))
    print(f"  길이: 최소 {lengths[0]} / 중앙 {lengths[len(lengths) // 2]} / 최대 {lengths[-1]}자")
    print(f"  분할된 조항: {len(split)}개" + (f" — {[c.chunk_id for c in split]}" if split else ""))

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps([c.__dict__ for c in chunks], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\n저장: {args.out}")

    if args.to_es:
        client = _es_client()
        embeddings = None if args.no_embed else _embed(chunks, args.embed_model, args.device)
        dims = es_index.EMBEDDING_DIMS if embeddings is not None else None
        if embeddings is not None and not args.recreate:
            _check_existing_mapping(client, args.layout)
        created = es_index.create_indices(client, args.layout, recreate=args.recreate, embedding_dims=dims)
        counts = es_index.index_chunks(client, chunks, args.layout, embeddings=embeddings)
        print(f"\nES 적재 — 레이아웃 {args.layout}")
        if created:
            print(f"  생성된 인덱스: {', '.join(created)}")
        for name, n in counts.items():
            print(f"  {name}: {n}건")
        total = sum(counts.values())
        if total != len(chunks):
            print(f"  ⚠ 청크 {len(chunks)}개인데 색인 문서는 {total}건이다")
            return 1
    return 0


def _embed(chunks, model_dir: Path, device: str | None) -> dict[str, list[float]] | None:
    """청크 전부를 임베딩한다. 모델·torch 가 없으면 None — 호출부가 BM25 만 적재한다."""
    if not (model_dir / "config.json").exists():
        print(f"\n⚠ 임베딩 모델이 없다({model_dir}) — BM25 필드만 적재한다. dense·하이브리드 검색은 0건이 된다")
        return None
    try:
        from retrieval.adapter.outbound.koe5_embedder import KoE5Embedder
        embedder = KoE5Embedder(model_dir, device=device)
    except ModuleNotFoundError as e:
        print(f"\n⚠ 임베딩 의존성이 없다({e.name}) — BM25 필드만 적재한다")
        return None

    texts = [es_index.embedding_input(c) for c in chunks]
    lengths = embedder.token_lengths(texts)
    # ⚠ 128 은 KoE5 의 상한이 아니다 — decisions/010 이 옛 후보(ko-sroberta, max_seq_length 128)에 적은 값이다.
    #   티켓이 그 숫자로 적어 둬서 둘 다 센다. KoE5 에서 실제로 잘리는 것은 512 초과분뿐이다.
    over128 = sum(1 for n in lengths if n > 128)
    over512 = sum(1 for n in lengths if n > 512)
    vectors = embedder.embed_passages(texts)
    print(f"\n임베딩 {embedder.model_name} · {len(vectors)}건 · {len(vectors[0])}차원 · 장치 {embedder.device}")
    print(f"  토큰 수(접두어 포함): 최대 {max(lengths)} · 128 초과 {over128}건 · 512 초과(실제 잘림) {over512}건")
    return {c.chunk_id: v for c, v in zip(chunks, vectors)}


def _check_existing_mapping(client, layout) -> None:
    """이미 있는 인덱스에 벡터를 넣으려면 매핑에 `dense_vector` 가 있어야 한다.

    없는 채로 넣으면 ES 가 `embedding` 을 **float 배열로 동적 매핑**해 적재는 성공하고 kNN 만 조용히 실패한다.
    """
    for name in es_index.index_names(layout):
        if not client.indices.exists(index=name):
            continue
        props = client.indices.get_mapping(index=name)[name]["mappings"].get("properties", {})
        if props.get(es_index.EMBEDDING_FIELD, {}).get("type") != "dense_vector":
            raise SystemExit(f"{name} 에 dense_vector 매핑이 없다 — --recreate 로 다시 만든다")


if __name__ == "__main__":
    raise SystemExit(main())
