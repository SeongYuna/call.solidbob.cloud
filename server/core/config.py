# Requirement: SEC-2
"""환경변수 → 상수. 이 저장소에서 `os.environ` 을 읽는 곳은 이 파일 하나뿐이다.

- 키 이름은 저장소 루트 `.env.example` 과 1:1 이다. 새 키를 추가하면 그쪽에도 등록한다 (이름만, 값 없음).
- 값은 `.env`(gitignore) 에서 온다. 이 모듈은 `.env` 를 직접 파싱하지 않는다 — 프로세스 환경에 이미
  실려 있다고 가정한다 (uvicorn `--env-file .env`, Docker `env_file:`, CI 시크릿). python-dotenv 를
  들이지 않는 이유: 로드 지점이 두 곳이 되면 어느 값이 이겼는지 추적이 안 된다.
- 비밀값은 로그·예외 메시지·`/health` 응답에 싣지 않는다 (docs/architecture.md §5, CLAUDE.md §8).
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def _env_int(name: str, default: int | None = None) -> int | None:
    raw = _env(name)
    return int(raw) if raw is not None else default


def _env_csv(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = _env(name)
    if raw is None:
        return default
    return tuple(item.strip() for item in raw.split(",") if item.strip())


_LOCAL_VITE_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")


@dataclass(frozen=True)
class Settings:
    # --- PostgreSQL (call · transcript_segment · recommendation · closure · eval_result …) ---
    postgres_host: str | None
    postgres_port: int
    postgres_db_name: str | None
    postgres_user: str | None
    postgres_password: str | None
    database_url: str | None

    # --- Elasticsearch (B-2 하이브리드 검색) ---
    elasticsearch_url: str | None
    elasticsearch_api_key: str | None

    # --- HuggingFace (임베딩·분류기·카드 요약 모델; 공개 모델이면 비워도 됨) ---
    huggingface_token: str | None

    # --- CORS (apps/call 가 브라우저에서 코어 API 를 부른다) ---
    # 기본값은 로컬 Vite 뿐이다. 운영 origin 은 배포 env 가 넣는다 — 운영 주소를 개발 기본값으로 굳히지 않는다
    # (`.claude/rules/dashboard.md` §5). 대시보드를 `server.solidbob.cloud` 와 같은 origin 에서 내주면 이 값은 쓰이지 않는다.
    cors_allowed_origins: tuple[str, ...]

    # --- 관리자 로그인(구글, 2026-09-14) — apps/admin. 회원가입 없음, 허용 목록은 admin_account ---
    google_oauth_client_id: str | None
    admin_jwt_secret: str | None
    # 테스트 스코프로 짧게 잡은 값(사용자 지시) — access는 Redis 세션, refresh는 admin_refresh_token(RDS)
    admin_access_token_ttl_seconds: int
    admin_refresh_token_ttl_seconds: int

    # --- Redis (관리자 access token 세션 전용, 테스트 스코프) ---
    # ElastiCache 를 쓰지 않는다(infra/CLAUDE.md §1-2) — 로컬 `docker run redis` 하나면 된다.
    redis_url: str | None

    # --- 고객 식별(2026-09-14, `decisions/304`) — 발신 번호를 HMAC-SHA256 으로 바꾸는 서버 비밀키 ---
    # 없으면 통화는 그대로 열리고 고객 연결만 하지 않는다(평문 번호를 대신 저장하지 않는다).
    # ⚠ 키를 바꾸거나 잃으면 기존 customer_id·블랙리스트 등록을 다시 찾을 수 없다(`decisions/205` ③)
    customer_ref_hmac_key: str | None

    @property
    def postgres_configured(self) -> bool:
        return bool(self.database_url) or all(
            (self.postgres_host, self.postgres_db_name, self.postgres_user, self.postgres_password)
        )

    @property
    def elasticsearch_configured(self) -> bool:
        return bool(self.elasticsearch_url)


def load_settings() -> Settings:
    """호출 시점의 환경을 읽는다. 앱 기동 시 한 번 부르고 DI 로 넘긴다 — 모듈 전역에 캐시하지 않는다
    (테스트에서 환경을 바꿔가며 부를 수 있어야 한다)."""
    return Settings(
        postgres_host=_env("POSTGRES_HOST"),
        postgres_port=_env_int("POSTGRES_PORT", 5432) or 5432,
        postgres_db_name=_env("POSTGRES_DB_NAME"),
        postgres_user=_env("POSTGRES_USER"),
        postgres_password=_env("POSTGRES_PASSWORD"),
        database_url=_env("DATABASE_URL"),
        elasticsearch_url=_env("ELASTICSEARCH_URL"),
        elasticsearch_api_key=_env("ELASTICSEARCH_API_KEY"),
        huggingface_token=_env("HUGGINGFACE_TOKEN"),
        cors_allowed_origins=_env_csv("CORS_ALLOWED_ORIGINS", _LOCAL_VITE_ORIGINS),
        google_oauth_client_id=_env("GOOGLE_OAUTH_CLIENT_ID"),
        admin_jwt_secret=_env("ADMIN_JWT_SECRET"),
        admin_access_token_ttl_seconds=_env_int("ADMIN_ACCESS_TOKEN_TTL_SECONDS", 300) or 300,
        admin_refresh_token_ttl_seconds=_env_int("ADMIN_REFRESH_TOKEN_TTL_SECONDS", 600) or 600,
        redis_url=_env("REDIS_URL"),
        customer_ref_hmac_key=_env("CUSTOMER_REF_HMAC_KEY"),
    )
