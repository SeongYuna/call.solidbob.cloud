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

# AI Hub 음성 한 건은 수 MB 다. 넉넉하되 데이터셋을 통째로 올리는 실수는 막는 값.
_DEFAULT_UPLOAD_MAX_BYTES = 100 * 1024 * 1024


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

    # --- 테스트 음성 업로드·보관 (A-6, 2026-09-14 `_project/decisions/110`) ---
    # 자격증명은 여기 없다 — boto3 가 EC2 인스턴스 역할을 IMDSv2 로 가져온다(운영 파드에서 확인).
    s3_bucket: str | None
    aws_region: str | None
    upload_token: str | None        # 없으면 업로드 문이 **잠긴다**(fail-closed, `110` 4번)
    upload_max_bytes: int           # S3 정책 `content-length-range` 의 상한으로도 같이 나간다

    # --- 쓰기 경로 서비스 토큰 (2026-09-20, `_project/decisions/120`) ---
    # 콜 미디에이터 → 서버의 쓰기 6+1 경로(`POST /hub/calls`·`/transcripts`·`/recommendations`·`/call-guard-checks`·
    # `/compliance-checks`·`/required-docs-checks`·`/closure-checks`)를 잠근다. 09-20 운영 왕복에서 **토큰 없이 200** 이었다.
    # **없으면 닫힌다**(업로드 토큰과 같다) — 미설정이면 일곱 경로가 전부 401 이고 `/health` 의 `ingest_guard` 가 "unset" 이다.
    #    2026-09-22 까지는 「없으면 연다」 이행기였다(120 「전환 순서」 4번에서 닫음). 콜 미디에이터의 `CORE_API_TOKEN` 과 같은 값.
    ingest_service_token: str | None

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

    # --- C-5 P6·P7 NER (2026-09-15, `w5-ner-p6-p7`) — `ai/apps/pii_ner` 가 규칙 마스킹 위에 한 겹 더 얹는다 ---
    # 모델 디렉터리(`scripts/download_models.py` → `models/koelectra-ner`). **비우면 규칙 마스킹만 돈다** — 지금 운영과 같다.
    # 서버 이미지에 torch·모델이 없으면 값을 넣어도 규칙으로 내려간다. 켜졌는지는 `/health` 의 `pii_ner` 로 본다.
    pii_ner_model_dir: str | None = None

    # --- B-2·B-3 임베딩·리랭킹 검색 (2026-09-15, `decisions/206`) — 비우면 BM25 단독(지금 운영과 같다) ---
    # 임베딩 모델 디렉터리(`models/koe5`)가 있어야 켜진다. 리랭커(`models/bge-reranker-v2-m3`)는 선택.
    # ⚠ 인덱스에 벡터가 없으면(torch 없이 적재) 검색이 0건이 되는데, 그때는 BM25 로 내려간다.
    retrieval_embed_model_dir: str | None = None
    retrieval_rerank_model_dir: str | None = None

    # --- B-4 서류 목록 카드 생성 (2026-09-15, `decisions/207`) — **둘 다 있어야** 켜진다. 비우면 스니펫 카드(지금 운영) ---
    # OLLAMA_URL 은 런북 16-1 이 이미 주입한다(`http://ollama:11434`). 그것만으로 켜지면 다음 배포에서 조용히 생성이
    # 붙어 추천 지연이 늘어난다 — 그래서 모델 이름을 따로 넣어야 켠다.
    ollama_url: str | None = None
    generation_model: str | None = None

    # --- 읽기 경로 문 (2026-09-22, `decisions/322`) — 통화 목록·전사·통화 기록·수동 검색 ---
    # 토큰은 늘 받는다(틀리면 401). true 면 **토큰 없는 요청도 401**. 상담원 화면이 토큰을 싣기 시작한 뒤 켠다 —
    # 먼저 켜면 운영 상담원 화면이 깨진다. 상태는 `/health` 의 `read_guard` 가 말한다.
    read_auth_required: bool = False

    @property
    def postgres_configured(self) -> bool:
        return bool(self.database_url) or all(
            (self.postgres_host, self.postgres_db_name, self.postgres_user, self.postgres_password)
        )

    @property
    def elasticsearch_configured(self) -> bool:
        return bool(self.elasticsearch_url)

    @property
    def uploads_configured(self) -> bool:
        """저장소와 문이 **둘 다** 있어야 켜진 것이다. 하나만 있으면 반쪽이라 켜지 않는다."""
        return bool(self.s3_bucket) and bool(self.upload_token)


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
        s3_bucket=_env("S3_BUCKET"),
        aws_region=_env("AWS_REGION"),
        upload_token=_env("UPLOAD_TOKEN"),
        ingest_service_token=_env("INGEST_SERVICE_TOKEN"),
        upload_max_bytes=_env_int("UPLOAD_MAX_BYTES", _DEFAULT_UPLOAD_MAX_BYTES) or _DEFAULT_UPLOAD_MAX_BYTES,
        google_oauth_client_id=_env("GOOGLE_OAUTH_CLIENT_ID"),
        admin_jwt_secret=_env("ADMIN_JWT_SECRET"),
        admin_access_token_ttl_seconds=_env_int("ADMIN_ACCESS_TOKEN_TTL_SECONDS", 300) or 300,
        admin_refresh_token_ttl_seconds=_env_int("ADMIN_REFRESH_TOKEN_TTL_SECONDS", 600) or 600,
        redis_url=_env("REDIS_URL"),
        customer_ref_hmac_key=_env("CUSTOMER_REF_HMAC_KEY"),
        pii_ner_model_dir=_env("PII_NER_MODEL_DIR"),
        retrieval_embed_model_dir=_env("RETRIEVAL_EMBED_MODEL_DIR"),
        retrieval_rerank_model_dir=_env("RETRIEVAL_RERANK_MODEL_DIR"),
        ollama_url=_env("OLLAMA_URL"),
        generation_model=_env("GENERATION_MODEL"),
        read_auth_required=(_env("READ_AUTH_REQUIRED") or "").strip().lower() in ("1", "true", "yes"),
    )
