# Requirement: [Task 1] FastAPI 앱 골격, SEC-2, B-2
#
# server(FastAPI) + ai/apps 를 한 이미지로 굽는다. **컨테이너는 하나다** —
# `ai/` 는 서비스가 아니라 라이브러리라 `main.py` 가 같은 프로세스에서 꽂는다
# (`_project/decisions/024`·`105`).
#
# 빌드는 **저장소 루트를 컨텍스트로** 한다. `main.py` 가 `../ai/apps` 를 경로에 올리므로
# `server/` 만 넣으면 검색 스포크가 꽂히지 않는다(= /health 의 spokes 에 retrieval 이 빠진다).
#
#   docker buildx build --platform linux/amd64 \
#     -f infra/docker/server.Dockerfile \
#     -t <도커허브계정>/callguard-server:0.1.0 --push .
#
# ⚠ `--platform linux/amd64` 를 빼지 않는다. EC2 가 g4dn(x86_64)인데 arm64 로 구우면
#   컨테이너가 `exec format error` 로 죽는다. 로컬에서는 멀쩡해서 원인을 찾기 어렵다.
# ⚠ `latest` 태그를 쓰지 않는다. k3s 가 캐시된 이미지를 계속 쓴다 — 버전을 올린다.

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 의존성을 먼저 넣는다 — 코드만 고쳤을 때 이 레이어가 캐시돼 빌드가 빨라진다.
COPY server/requirements.txt /tmp/server-requirements.txt
COPY ai/requirements.txt /tmp/ai-requirements.txt

# `ai/requirements.txt` 전체를 설치하지 않는다 — 필요한 것만 골라 넣는다.
#
# 버전을 여기 손으로 적지 않고 ai/requirements.txt 에서 뽑는다. 두 곳에 적으면 어긋나고,
# 어긋나면 ES 서버에 아예 붙지 않는다 (`decisions/020` 실측 —
# 'Accept version must be either version 8 or 7, but found 9').
RUN pip install -r /tmp/server-requirements.txt \
 && pip install "$(grep -E '^elasticsearch==' /tmp/ai-requirements.txt)"

# 모델 실행 환경 (2026-09-22, `_project/decisions/124` — NER·임베딩을 운영 노드 CPU 에 싣는다).
# **CPU 판 torch 만** 넣는다 — PyPI 기본 torch 는 CUDA 라이브러리가 딸려 수 GB 인데 t3.large 에는 GPU 가 없다.
# 인덱스 순서가 중요하다: cpu 인덱스를 첫째로 두고 PyPI 는 나머지 의존성용이다.
# 모델 파일은 이미지에 넣지 않는다 — 노드의 /opt/callguard/models 를 파드 /models 로 붙인다(server.yaml).
# `PII_NER_MODEL_DIR`·`RETRIEVAL_EMBED_MODEL_DIR` 가 비어 있으면 이 층은 그냥 잠들어 있고 규칙·BM25 로 돈다.
RUN pip install --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple \
      "$(grep -E '^torch==' /tmp/ai-requirements.txt)" \
 && pip install $(grep -E '^(transformers|huggingface_hub|sentencepiece|numpy)==' /tmp/ai-requirements.txt)

# main.py 가 기대하는 배치 그대로 둔다: /app/server/main.py 와 /app/ai/apps/ · /app/ai/provider.py
COPY server/ /app/server/
COPY ai/apps/ /app/ai/apps/
# 트리거(B-1) 팩토리. main.py `_wire_trigger` 가 `from provider import …` 로 부른다 — 없으면 **오류 없이**
# trigger 스포크만 빠진다(decisions/024 설계). 0.1.2 가 이 줄 없이 나가 운영 spokes 가 3종이었다(2026-09-11).
COPY ai/provider.py /app/ai/provider.py

# 루트로 돌리지 않는다.
RUN useradd --create-home --uid 10001 callguard \
 && chown -R callguard:callguard /app
USER callguard

WORKDIR /app/server
EXPOSE 8000

# 배포 태그를 이미지에 굽는다 — `/health` 의 `version`(`w6-server-loose-ends` ①). `release.yml` 이 `newTag` 를 넘긴다.
# 캐시를 깨지 않게 맨 끝에 둔다(태그가 바뀌어도 이 한 층만 다시 굽는다). 로컬 빌드는 "unknown".
ARG APP_VERSION=unknown
ENV APP_VERSION=${APP_VERSION}

# `--host 0.0.0.0` 이 아니면 컨테이너 밖에서 붙지 못한다 — 쿠버네티스 프로브부터 실패한다.
# `--reload` 는 개발 전용이라 넣지 않는다.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
