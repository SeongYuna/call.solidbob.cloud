# Requirement: A-1, A-3, COST-1
#
# services/gateway(Node.js) 이미지. server 와 **따로** 굽고 따로 뜬다 — 오디오 중계라 파이썬 서버와
# 수명·자원이 다르다. 같은 노드에 올린다(런북 0장 사양표가 이미 «FastAPI server · Node 게이트웨이 ≈ 1.0GB» 로 계산).
#
#   docker buildx build --platform linux/amd64 \
#     -f infra/docker/gateway.Dockerfile \
#     -t seongyuna/callguard-gateway:0.1.0 --push .
#
# 컨텍스트는 저장소 루트다(server 이미지와 같은 규칙 — `.dockerignore` 하나를 같이 쓴다).
# ⚠ `--platform linux/amd64` · `latest` 금지 — server.Dockerfile 머리말과 같은 이유다.

# 로컬에서 테스트한 버전과 같게 고정한다. .ts 를 빌드 없이 그대로 돌리는 타입 제거 실행이 22.18+ 부터다.
FROM node:24.18.0-slim

ENV NODE_ENV=production \
    NPM_CONFIG_UPDATE_NOTIFIER=false

# 코드 위치를 저장소와 같게 둔다 — `src/config.ts` 가 사용량 장부를 저장소 루트 기준
# (`../../../data/processed/stt-usage.json` → `/app/data/processed/`)으로 찾는다. 운영은 거기에 볼륨을 붙인다.
WORKDIR /app/services/gateway

# 의존성 먼저 — 코드만 고쳤을 때 이 레이어가 캐시된다.
# `--omit=dev`: typescript·@types 는 실행에 필요 없다(타입 검사는 CI 가 한다).
# `--ignore-scripts`: 설치 스크립트를 돌리지 않는다. 지금 걸리는 것은 protobufjs 의 버전 경고 스크립트 하나다.
COPY services/gateway/package.json services/gateway/package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts --no-audit --no-fund \
 && npm cache clean --force

COPY services/gateway/src ./src

# 장부 디렉터리를 미리 만들어 node 사용자에게 준다. 운영은 이 자리에 hostPath 를 덮어 쓴다(gateway.yaml).
RUN mkdir -p /app/data/processed && chown -R node:node /app/data

# 루트로 돌리지 않는다 — 이미지에 있는 node 사용자(uid 1000).
USER node
EXPOSE 8080

# exec 형태 — node 가 PID 1 이 되어 SIGTERM 을 직접 받는다(사용량을 장부에 쓰고 내려간다, main.ts).
CMD ["node", "src/main.ts"]
