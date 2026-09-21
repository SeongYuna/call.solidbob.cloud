---
title: "ai/ 모델 HTTP 표면 — GPU 인스턴스에서 도는 추론 서비스"
assignee: "류준"
role: "ai"
status: "todo"
sprint: 6
priority: 68
date: 2026-09-21
requirement:
  - "B-2"
  - "B-3"
  - "C-5"
depends_on:
  - "w6-gpu-model-instance"
paths:
  - "ai/apps/*"
---

## 무엇을

`decisions/121` 로 모델이 서버와 **다른 머신**에 간다. `ai/` 의 NER · 임베딩 · 리랭커 · 생성을
원격에서 부를 수 있게 **HTTP 표면**을 만든다.

## 왜 — 그리고 무엇이 바뀌는가

`decisions/024`·`105` 는 `ai/` 를 서버와 **같은 프로세스에 실리는 라이브러리**로 정했고
`ai/requirements.txt` 에 웹 프레임워크가 없다는 것이 그 전제였다. **그 전제가 깨진다** —
결정 기록(`2xx`)으로 남긴다. 포트(`RetrievalPort`·`MaskingPort` …)는 그대로 두고 어댑터만 바꾸는 구조다.

## 지켜야 할 것

- **의존 방향은 그대로 `ai → server` 한쪽이다.** 표면이 생겨도 `server` 가 `ai` 를 import 하지 않는다 — HTTP 로만 닿는다
- **판정은 규칙이, 설명만 LLM 이**(절대 원칙 9). 표면이 마스킹 «판정»을 모델 단독으로 돌려주지 않는다 — 규칙 + NER 두 겹 그대로
- 원문이 로그에 남지 않는다(SEC-1) — 요청 본문을 찍는 접근 로그를 켜지 않는다

## 완료 조건

- [ ] 표면 위치·프레임워크·인증을 결정 기록으로 남긴다
- [ ] 엔드포인트별 단위 테스트 + `.importlinter` 계약 3종 KEPT
- [ ] 로컬에서 서버 원격 어댑터([w6-server-remote-model-adapter](/backlog/w6-server-remote-model-adapter/))와 왕복 1건
