# Requirement: 7.3절 인터페이스 계약
"""응답 스키마 전용 타입 — **모든 응답 필드는 문자열로 나간다** (2026-09-10 조서희·장민석 합의).

프론트 파서가 문자열만 받기로 정해졌고, 서버는 그 계약에 맞춘다. 라우터·DTO·DB 는 원래 타입
(bool·int·float)을 그대로 쓰고 **HTTP 표면(이 스키마 계층)에서만** 문자열로 바꾼다 — 내부까지
문자열로 바꾸면 정렬·산술·외래키가 흔들린다.

- 불리언 → `"true"` / `"false"` (JSON 리터럴과 같은 소문자)
- 정수·실수 → `str()` 그대로 (`3150`, `7.802647`)
- `None` 은 그대로 `null` — "값이 없다"는 정보는 문자열로 뭉개지 않는다

OpenAPI 에는 `string` 으로 공표된다 — 프론트가 `/openapi.json` 을 읽고 붙이므로 문서와 실제가 같아야 한다.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BeforeValidator


def _stringify(value: Any) -> Any:
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return value  # 그 밖의 타입은 pydantic 이 평소대로 검증한다


StrField = Annotated[str, BeforeValidator(_stringify)]
