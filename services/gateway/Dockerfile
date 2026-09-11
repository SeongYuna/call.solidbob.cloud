# Requirement: A-1, A-2, A-3, COST-1
#
# 실제 전화 → Twilio Media Streams → Google STT → server/apps/hub(마스킹) →
# apps/dashboard 로 이어지는 게이트웨이. server.Dockerfile과 같은 관례를
# 따른다(플랫폼 고정·루트 미사용·버전 태그).
#
# ⚠ 지금은 배포용이 아니라 **내일 이후를 위한 준비물**이다 — 오늘은 로컬 +
# ngrok 으로만 확인한다. 실제로 k3s 에 올릴 때는 infra/docker/server.Dockerfile
# 관례대로 infra/docker/gateway.Dockerfile 로 옮기고 정성윤과 먼저 맞춘다
# (`infra/CLAUDE.md` — "다른 사람이 여기를 고칠 일이 생기면 먼저 말로 맞춘다").
#
# 빌드 컨텍스트는 이 디렉터리(services/gateway) 하나면 된다 — server 이미지처럼
# 저장소 루트를 볼 필요가 없다(ai/apps 를 끌어오지 않는다).
#
#   docker buildx build --platform linux/amd64 \
#     -t <도커허브계정>/callguard-gateway:0.1.0 --push services/gateway
#
# ⚠ `--platform linux/amd64` 를 빼지 않는다 — EC2 가 g4dn(x86_64)이라 arm64 로
#   구우면 `exec format error` 로 죽는다(server.Dockerfile과 같은 함정).
# ⚠ `latest` 태그를 쓰지 않는다 — k3s 가 캐시된 이미지를 계속 쓴다.

FROM node:20-slim

ENV NODE_ENV=production

WORKDIR /app

# 의존성을 먼저 넣는다 — 코드만 고쳤을 때 이 레이어가 캐시돼 빌드가 빨라진다.
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

COPY src/ ./src/

# 루트로 돌리지 않는다.
RUN groupadd --system callguard \
 && useradd --system --create-home --gid callguard --uid 10001 callguard \
 && chown -R callguard:callguard /app
USER callguard

EXPOSE 8080

CMD ["node", "src/server.js"]
