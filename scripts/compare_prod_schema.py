#!/usr/bin/env python3
# Requirement: SEC-1, QUA-2
"""운영 DB 의 컬럼과 `db/schema.sql` 을 **컬럼 단위로** 대조한다.

    # ① 운영에서 컬럼 목록을 뜬다 (SSM · 읽기만 한다)
    k3s kubectl -n callguard exec deploy/callguard-server -- python -c "
    import os, psycopg
    c = psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=8)
    rows = c.execute('''select table_name, column_name, udt_name, is_nullable,
        coalesce(character_maximum_length,-1), coalesce(numeric_precision,-1), coalesce(numeric_scale,-1)
        from information_schema.columns where table_schema='public'
        order by table_name, ordinal_position''').fetchall()
    print('ROWS', len(rows))
    [print('|'.join(str(x) for x in r)) for r in rows]" > prod-columns.txt

    # ② 대조한다
    python scripts/compare_prod_schema.py prod-columns.txt

## 왜 필요한가

**「머지 = 배포」인데 스키마는 사람 손**이다(미결 「운영 스키마가 배포보다 늦게 따라간다」).
지금까지 대조는 **테이블 «이름»까지**였다 — 09-15 기록에도 *"컬럼은 이름만 봄"* 이라고 적혀 있다.
컬럼이 어긋나면 배포는 초록인데 **그 경로만 500** 이 난다. 그 상태를 눈으로 찾지 않으려고 만든다.

**이 스크립트는 DB 에 접속하지 않는다** — 운영 접속은 SSM 을 쓰는 사람이 ①로 하고,
여기서는 **텍스트 두 개만** 비교한다(자격증명을 다루지 않는다, SEC-2).

## 판정

- 🔴 **양쪽에 있는데 다르다** (타입·길이·NULL 여부) — 가장 위험하다. 코드가 기대하는 모양과 실물이 다르다
- 🟡 **`schema.sql` 에만 있다** — 마이그레이션을 안 돌렸다. 그 컬럼을 쓰는 경로가 500 난다
- 🟡 **운영에만 있다** — 지운 컬럼이 남아 있거나, 스키마 생성기(`db/generate_schema_docs.py`)에 안 적혔다
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "db" / "schema.sql"

# `schema.sql` 의 타입 표기 → PostgreSQL `information_schema.columns.udt_name`
UDT = {
    "BIGINT": "int8", "INT": "int4", "INTEGER": "int4", "SMALLINT": "int2",
    "VARCHAR": "varchar", "CHARACTER VARYING": "varchar", "CHAR": "bpchar",
    "TEXT": "text", "BOOLEAN": "bool", "BOOL": "bool",
    "TIMESTAMPTZ": "timestamptz", "TIMESTAMP WITH TIME ZONE": "timestamptz",
    "TIMESTAMP": "timestamp", "DATE": "date", "TIME": "time",
    "NUMERIC": "numeric", "DECIMAL": "numeric", "REAL": "float4",
    "DOUBLE PRECISION": "float8", "JSONB": "jsonb", "JSON": "json",
    "BYTEA": "bytea", "UUID": "uuid",
}
NOT_COLUMN = re.compile(r"^\s*(PRIMARY KEY|UNIQUE|FOREIGN KEY|CONSTRAINT|CHECK|EXCLUDE)\b", re.I)
COLUMN = re.compile(r'^\s*"(?P<name>[^"]+)"\s+(?P<type>[A-Z][A-Z \t]*?)(?:\((?P<args>[^)]*)\))?(?P<rest>\s|,|$)', re.I)


def parse_schema(path: Path) -> dict[str, dict[str, tuple[str, int, str]]]:
    """schema.sql → {테이블: {컬럼: (udt, 길이, NULL여부)}}"""
    out: dict[str, dict[str, tuple[str, int, str]]] = {}
    table = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("CREATE TABLE"):
            m = re.search(r'CREATE TABLE "([^"]+)"', line)
            table = m.group(1) if m else None
            if table:
                out[table] = {}
            continue
        if table is None:
            continue
        if line.startswith(");"):
            table = None
            continue
        if NOT_COLUMN.match(line):
            continue
        m = COLUMN.match(line)
        if not m:
            continue
        raw_type = " ".join(m.group("type").split()).upper()
        udt = UDT.get(raw_type)
        if udt is None:                       # 모르는 타입은 그대로 둔다 — 비교에서 «확인 필요» 로 드러난다
            udt = raw_type.lower()
        length = -1
        if m.group("args") and udt in ("varchar", "bpchar"):
            try:
                length = int(m.group("args").split(",")[0].strip())
            except ValueError:
                length = -1
        nullable = "NO" if re.search(r"\bNOT\s+NULL\b", line, re.I) else "YES"
        out[table][m.group("name")] = (udt, length, nullable)
    return out


def parse_dump(path: Path) -> dict[str, dict[str, tuple[str, int, str]]]:
    """①이 만든 파이프 구분 텍스트 → 같은 모양."""
    out: dict[str, dict[str, tuple[str, int, str]]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split("|")
        if len(parts) < 5:
            continue                          # 'ROWS 198' 같은 머리말·빈 줄
        table, column, udt, is_nullable, char_len = parts[0], parts[1], parts[2], parts[3], parts[4]
        out.setdefault(table, {})[column] = (udt, int(char_len), is_nullable)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dump", type=Path, help="①이 만든 운영 컬럼 목록 파일")
    ap.add_argument("--schema", type=Path, default=SCHEMA)
    args = ap.parse_args()

    want = parse_schema(args.schema)          # 저장소가 말하는 모양
    have = parse_dump(args.dump)              # 운영 실물
    if not have:
        print("운영 덤프가 비었다 — ①을 먼저 돌린다", file=sys.stderr)
        return 1

    print(f"저장소 {args.schema.name}: {len(want)} 테이블 · {sum(len(c) for c in want.values())} 컬럼")
    print(f"운영 실물          : {len(have)} 테이블 · {sum(len(c) for c in have.values())} 컬럼\n")

    only_schema = sorted(set(want) - set(have))
    only_prod = sorted(set(have) - set(want))
    if only_schema:
        print(f"🟡 schema.sql 에만 있는 테이블 {len(only_schema)}: {', '.join(only_schema)}")
    if only_prod:
        print(f"🟡 운영에만 있는 테이블 {len(only_prod)}: {', '.join(only_prod)}")

    mismatch = 0
    for table in sorted(set(want) & set(have)):
        w, h = want[table], have[table]
        for col in sorted(set(w) - set(h)):
            print(f"🟡 {table}.{col} — schema.sql 에만 있다 (마이그레이션 미적용) · {w[col]}")
            mismatch += 1
        for col in sorted(set(h) - set(w)):
            print(f"🟡 {table}.{col} — 운영에만 있다 (지운 컬럼이 남았거나 생성기에 없다) · {h[col]}")
            mismatch += 1
        for col in sorted(set(w) & set(h)):
            wt, wl, wn = w[col]
            ht, hl, hn = h[col]
            diffs = []
            if wt != ht:
                diffs.append(f"타입 {wt} ≠ {ht}")
            if wt in ("varchar", "bpchar") and wl != hl:
                diffs.append(f"길이 {wl} ≠ {hl}")
            if wn != hn:
                diffs.append(f"NULL {wn} ≠ {hn}")
            if diffs:
                print(f"🔴 {table}.{col} — {' · '.join(diffs)}")
                mismatch += 1

    total = mismatch + len(only_schema) + len(only_prod)
    print(f"\n{'어긋남 ' + str(total) + ' 건' if total else '✅ 어긋남 0 — 컬럼·타입·길이·NULL 여부까지 같다'}")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
