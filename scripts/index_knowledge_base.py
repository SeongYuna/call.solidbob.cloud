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
        created = es_index.create_indices(client, args.layout, recreate=args.recreate)
        counts = es_index.index_chunks(client, chunks, args.layout)
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


if __name__ == "__main__":
    raise SystemExit(main())
