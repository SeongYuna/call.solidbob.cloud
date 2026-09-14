#!/usr/bin/env python3
# Requirement: B-6, C-6
"""지식베이스 조항 → PostgreSQL `document` 테이블 (w4-c6-d5-persistence).

`document` 는 조항의 **참조 무결성용 메타데이터**다(본문은 Elasticsearch). 그런데 이 테이블을 채우는
경로가 **없었다** — ES 적재(`index_knowledge_base.py --to-es`)만 있고 DB 적재는 없어서,
`call_guard_flag.source_doc_id`(`DASAN-MANUAL-5.x`)·`recommendation_card.source_doc_id` 의 외래키가
설 수 없었다. 운영에서 콜 가드 기록이 FK 위반으로 실패한다.

같은 입력이면 같은 결과다 — UPSERT 라 여러 번 돌려도 된다. 지식베이스에서 **빠진 조항은 지우지
않는다**: 그 조항을 가리키는 옛 카드·콜 가드 기록이 FK 로 묶여 있고, 지우면 「어떤 근거로 떴었는지」가
사라진다(절대 원칙 8). 빠진 조항은 목록으로 알려만 준다.

    .venv/bin/python scripts/seed_documents.py --dry-run          # 넣을 행만 본다
    DATABASE_URL=postgresql://... .venv/bin/python scripts/seed_documents.py

⚠ **운영 RDS 에 돌리는 것은 인프라 절차다** — `docs/infra-runbook.md` 를 먼저 본다.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ai" / "apps"))

from retrieval.domain.services.chunking import chunk_markdown  # noqa: E402
from retrieval.domain.value_objects.chunk import DOMAINS  # noqa: E402

# `DASAN-MANUAL-5.1` → 장 "5", 조 "5.1". 점이 없는 ID(`DASAN-POLICY-1`)는 장만 있다.
_CLAUSE = re.compile(r"-(?P<num>\d+(?:\.\d+)*)$")

_UPSERT = """
INSERT INTO "document" ("document_id", "doc_type", "chapter", "clause", "title", "source_path", "updated_at")
VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT ("document_id") DO UPDATE SET
    "doc_type" = EXCLUDED."doc_type",
    "chapter" = EXCLUDED."chapter",
    "clause" = EXCLUDED."clause",
    "title" = EXCLUDED."title",
    "source_path" = EXCLUDED."source_path",
    "updated_at" = EXCLUDED."updated_at"
"""


def document_rows(kb_root: Path) -> list[tuple[str, str, str | None, str | None, str, str]]:
    """조항 하나 = 행 하나. 조항이 청크 여러 개로 쪼개져도 `doc_id` 기준으로 한 번만 낸다."""
    rows: dict[str, tuple] = {}
    for domain in DOMAINS:
        for md in sorted((kb_root / domain).rglob("*.md")):
            if md.name == "README.md":
                continue
            source_path = str(md.relative_to(kb_root.parent))
            for chunk in chunk_markdown(md.read_text(encoding="utf-8")):
                if chunk.doc_id in rows:
                    continue
                m = _CLAUSE.search(chunk.doc_id)
                num = m.group("num") if m else None
                chapter = num.split(".")[0] if num else None
                clause = num if num and "." in num else None
                if len(chunk.title) > 100:
                    raise ValueError(f"{chunk.doc_id}: 제목이 VARCHAR(100) 을 넘는다 — 자르지 않고 멈춘다")
                rows[chunk.doc_id] = (chunk.doc_id, chunk.doc_type, chapter, clause, chunk.title, source_path)
    return list(rows.values())


def main() -> int:
    ap = argparse.ArgumentParser(description="지식베이스 조항을 document 테이블에 적재한다")
    ap.add_argument("--kb", type=Path, default=ROOT / "knowledge-base")
    ap.add_argument("--dry-run", action="store_true", help="DB 에 쓰지 않고 넣을 행만 출력한다")
    args = ap.parse_args()

    rows = document_rows(args.kb)
    print(f"조항 {len(rows)}개")
    if args.dry_run:
        for row in rows:
            print("  ", " | ".join(str(v) for v in row))
        return 0

    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL 이 비어 있다 — 적재할 DB 주소를 준다(SEC-2: 값은 출력하지 않는다)")
    import psycopg  # noqa: PLC0415

    now = datetime.now(timezone.utc)
    with psycopg.connect(url) as conn, conn.cursor() as cur:
        cur.executemany(_UPSERT, [(*row, now) for row in rows])
        cur.execute('SELECT "document_id" FROM "document"')
        stale = sorted({r[0] for r in cur.fetchall()} - {row[0] for row in rows})
        conn.commit()
    print(f"적재 완료 {len(rows)}개")
    if stale:
        print(f"⚠ 지식베이스에 없는 조항 {len(stale)}개 — 지우지 않았다(참조가 남아 있을 수 있다): {stale}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
