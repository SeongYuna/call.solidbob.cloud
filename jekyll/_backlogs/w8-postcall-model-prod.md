---
title: "통화 후 요약을 운영에서 모델로 켠다 — 요약만 · CPU Ollama · 서버 등급 상향"
assignee: "정성윤"
role: "infra"
status: "in-progress"
sprint: 8
priority: 90
date: 2026-10-02
requirement:
  - "D-1"
paths:
  - "infra/k8s/base/ollama.yaml"
  - "ai/apps/postcall_summary/*"
depends_on:
  - "w7-postcall-spoke"
---

## 무엇을

통화 후 처리의 요약 초안을 규칙 발췌에서 **모델 요약**으로 바꾼다 — 운영에서, 요약만(`_project/decisions/146`).

## 왜

10-02 사용자 지적: 요약 초안이 요약이 아니라 발화 모음으로 보인다. 모델 요약 코드는 09-15 에 있었지만([w7-postcall-spoke](/backlog/w7-postcall-spoke/)) 운영에 GPU·Ollama 가 없어 꺼져 있었다.

## 완료 조건

- [x] 요약만 켜는 스위치(`POSTCALL_MODEL`) — 카드 생성은 꺼진 채다(테스트)
- [x] 위반이 잡힌 상담원 발화는 모델 프롬프트에서 뺀다(테스트)
- [x] Ollama 배포 파일(`infra/k8s/base/ollama.yaml`, ClusterIP 전용)
- [x] 루트 볼륨 60GB · 고정 IP · 인스턴스 등급 상향 (10-02 — `c7i.2xlarge`)
- [ ] 운영에 모델 등록 · `server-env` 에 `OLLAMA_URL`·`POSTCALL_MODEL` · `/health` `spokes` 에 `postcall_model`
- [ ] 운영에서 시연 1막을 넣고 통화 종료 → 요약 시간과 글을 **잰다**(등급별)
- [ ] `.env.example` 에 `POSTCALL_MODEL=` 키 이름(보호 훅이라 사람이 넣는다)

## 2026-10-02 — 운영 노드 임시 시험 · 코드 (정성윤)

- **시험**: `t3.large` 에 임시 파드(llama.cpp server · kanana Q4_K_M)를 띄워 서버가 보내는 것과 같은 요약 요청 셋을 쟀다 — 1막 17줄 38.1초 · 폭언·위기 5줄 17.8초 · 외국인 고객 19줄 53.4초(출력 4토큰/초 안팎). 셋 다 규칙 검사 통과. 하네스 값이 아니라 임시 실측이다. 파드·이미지는 지웠다(디스크 62% · ES green 확인).
- **그 전에 Ollama 이미지로 시도했다가 디스크가 62% → 91% 로 뛰어 바로 지웠다** — 압축 3.75GB 이미지다. 30GB 디스크에는 Ollama 를 못 올린다.
- **코드**: `server/core/config.py`·`server/main.py`(스위치 분리) · `ai/apps/postcall_summary/…/model_postcall_adapter.py`(`summarize_with_flags` — 위반 발화 제외) · 테스트 +4 · `infra/k8s/base/ollama.yaml` · 서버 태그 `0.1.45`. server pytest 통과 · ai `postcall_summary` 14 통과 · 구조 계약 5종·3종 KEPT. (ai 전체에서 `test_harness_postcall` 2건은 이 Windows 머신의 심볼릭 링크 권한 문제로 실패 — 수정 전에도 같다, CI 는 통과)

## 2026-10-02 오후 — 등급 상향 · 올린 뒤 실측 (정성윤)

- **운영 변경**: 루트 볼륨 60GB(켠 채로) · 고정 IP `3.38.62.188` + Cloudflare A 레코드(사용자) · `t3.large` → `c7i.2xlarge`(약 1분 중단). 올라온 뒤 파드 넷 `1/1` · ES green · `/health` ok 확인.
- **실측**(임시 Ollama 파드, 각 1회, 하네스 값 아님): 1막 17줄 8.0초(첫 요청, 모델 올리기 2.6초 포함) · 1막 위반 줄 제외 14줄 5.2초 → 다시 3.7초 · 폭언·위기 5줄 2.5초 · 외국인 고객 19줄 7.5초. 출력 18토큰/초 안팎(전 4.4). 다섯 다 규칙 검사 통과, 30초 타임아웃 안. 표는 `decisions/146` 갱신 절.
- **알게 된 것**: 같은 입력을 두 번 넣으니 글이 달랐다(142자 / 114자, temperature 0 · seed 고정) · 파드 메모리 2,690Mi 라 상한을 3Gi → 4Gi 로 올렸다(`ollama.yaml`).
- 임시 파드는 지웠다. 모델 파일(1.5GB)과 이미지는 노드에 남겨 정식 배포가 다시 받지 않는다. 디스크 48%.
- **세 번째 완료 조건의 「등급별」 은 한 등급만 쟀다** — `c7i.xlarge` 는 재지 않았다.
- 남은 것: 커밋·머지(승인 대기) → Ollama 배포 → `server-env` 두 키 → `/health` 에 `postcall_model` → 운영에서 1막 통화 종료로 다시 잰다.
