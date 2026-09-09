#!/usr/bin/env bash
# Requirement: [Task 1], SEC-2
#
# 부팅 시 저장소(main) 상태로 클러스터를 맞춘다.
#
# **k3s 는 부팅하면 파드를 알아서 되살린다.** 이 스크립트가 필요한 이유는 그게 아니라,
# **인스턴스가 꺼져 있는 동안 나간 릴리스**를 따라잡기 위해서다 —
# `release.yml` 의 deploy 는 인스턴스가 `stopped` 면 실패가 아니라 skip 으로 넘어간다.
# 그 skip 이 유실이 되지 않게 하는 것이 여기다.
#
# git 을 쓰지 않는다. 인스턴스에 git 이 없고(2026-09-09 확인) 깔 이유도 없다 —
# 공개 저장소라 tarball 을 받아 `kubectl kustomize` 로 렌더하면 된다.
# 네트워크가 안 되면 마지막으로 적용된 캐시(`/opt/callguard/current.yaml`)로 되돌아간다.
#
# ⚠ 시크릿은 건드리지 않는다. 매니페스트에 Secret 이 없다(kustomization 의 resources 에서 제외).

set -euo pipefail

export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
REPO_TAR="https://github.com/SeongYuna/call.solidbob.cloud/archive/refs/heads/main.tar.gz"
CACHE=/opt/callguard/current.yaml
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

log() { echo "[converge] $*"; }

# ── k3s API 가 뜰 때까지 기다린다 (최대 5분) ──────────────────────────────
for _ in $(seq 1 60); do
  kubectl get --raw /readyz >/dev/null 2>&1 && break
  sleep 5
done
kubectl get --raw /readyz >/dev/null 2>&1 || { log "k3s API 가 뜨지 않았다"; exit 1; }

# ── main 의 매니페스트를 받아 렌더한다 ───────────────────────────────────
if curl -fsSL --max-time 60 "$REPO_TAR" | tar xz -C "$WORK"; then
  SRC=$(find "$WORK" -maxdepth 5 -type d -path '*/infra/k8s/base' | head -1)
  if [ -n "$SRC" ] && kubectl kustomize "$SRC" > "$WORK/manifest.yaml"; then
    # 자격증명이 섞여 들어오지 않았는지 본다 (SEC-2). release.yml 과 같은 검사다.
    if grep -qE '^kind: Secret' "$WORK/manifest.yaml"; then
      log "렌더 결과에 Secret 이 있다 — 적용하지 않는다"
      exit 1
    fi
    install -D -m 0644 "$WORK/manifest.yaml" "$CACHE"
    log "main 에서 매니페스트를 갱신했다"
  else
    log "렌더 실패 — 캐시로 진행한다"
  fi
else
  log "저장소를 받지 못했다 — 캐시로 진행한다"
fi

# ── 적용 ─────────────────────────────────────────────────────────────────
[ -s "$CACHE" ] || { log "적용할 매니페스트가 없다"; exit 1; }
kubectl apply -f "$CACHE"
kubectl -n callguard rollout status deploy/callguard-server --timeout=180s
log "완료"
