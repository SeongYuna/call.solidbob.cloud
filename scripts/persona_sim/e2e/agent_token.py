# Requirement: D-1, J-1, SEC-2
"""로컬 E2E 가 재생기 `--close` 에 넘길 **상담원 토큰**을 검사 DB 에 임시로 만든다 — 순수 함수 + SQL 문장만 둔다.

왜: `POST /hub/calls/{id}/close` 가 2026-09-22(`a866ff4`, `decisions/315`)부터 상담원 토큰 또는 서비스 토큰을 요구한다
(`server/apps/hub/dependencies/close_guard.py`). 로컬 E2E 서버는 서비스 토큰(`INGEST_SERVICE_TOKEN`)을 설정하지 않으니
상담원 토큰만 통한다 — 전에는 재생기가 `CORE_API_TOKEN` 만 실어 401 이었다.

가장 덜 건드리는 길을 골랐다 — **발급 API(`/admin/agent-tokens`)는 관리자 구글 로그인이 있어야 해서** 검사기가 못 부른다.
서버가 토큰을 확인하는 방법은 `agent_token.token_hash`(SHA-256 hex, 폐기 안 됨) 한 줄 조회뿐이라
(`agent_token_repository.py` `_SELECT_ACTIVE`), 같은 모양의 행을 검사 DB 에 직접 넣으면 서버 코드를 바꾸지 않고 통한다.
- 원문은 이 프로세스 메모리와 재생기 환경변수(`CALL_AGENT_TOKEN`)에만 있다. **찍지 않고 파일에 쓰지 않는다.** DB 에는 해시만 간다
- 검사가 끝나면 `revoked_at` 을 채워 폐기한다(행은 지우지 않는다 — 스키마 주석의 원칙과 같다)
- **DB 와 서버가 둘 다 루프백일 때만** 만든다 — 운영 DB 에는 절대 쓰지 않는다
토큰 모양·해시는 `server/apps/agent_auth/domain/services/agent_token.py` 와 같아야 한다 — 테스트가 둘을 대조한다.
"""

from __future__ import annotations

import hashlib
import secrets
from urllib.parse import urlparse

TOKEN_PREFIX = "cga_"
_TOKEN_BYTES = 32
E2E_AGENT_ID = "e2e-replayer"  # agent.agent_id VARCHAR(20)
E2E_AGENT_NAME = "E2E 재생기"
ENV_AGENT_TOKEN = "CALL_AGENT_TOKEN"  # 재생기 `persona_replay/close_auth.ts` 가 읽는 이름

INSERT_AGENT = (
    'INSERT INTO "agent" ("agent_id", "display_name", "team", "role") VALUES (%s, %s, %s, %s) '
    'ON CONFLICT ("agent_id") DO NOTHING'
)
INSERT_TOKEN = (
    'INSERT INTO "agent_token" ("agent_id", "token_hash", "issued_by", "issued_at") VALUES (%s, %s, NULL, now()) RETURNING "id"'
)
REVOKE_TOKEN = 'UPDATE "agent_token" SET "revoked_at" = COALESCE("revoked_at", now()) WHERE "id" = %s'


def new_token() -> str:
    return TOKEN_PREFIX + secrets.token_urlsafe(_TOKEN_BYTES)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def is_loopback_url(url: str) -> bool:
    """`postgresql://…@127.0.0.1:5432/db` · `http://localhost:8000` 처럼 이 머신을 가리키는가. 호스트가 없으면(유닉스 소켓) 아니다."""
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return False
    return host in {"localhost", "::1"} or host.startswith("127.")


def refusal_reason(database_url: str, core_url: str) -> str:
    """임시 토큰을 만들면 안 되는 이유. 빈 문자열이면 만들어도 된다."""
    if not is_loopback_url(database_url):
        return "검사 DB 가 루프백이 아니다 — 운영 DB 에는 토큰을 만들지 않는다"
    if not is_loopback_url(core_url):
        return "서버 주소가 루프백이 아니다 — 로컬 검사 DB 토큰은 그 서버에서 통하지 않는다"
    return ""
