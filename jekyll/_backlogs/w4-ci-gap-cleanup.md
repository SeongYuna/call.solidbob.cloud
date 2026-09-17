---
title: "미결로 남겨둔 CI 결함 다섯 닫기 — ES 이미지 · 부팅 롤아웃 · 중복 CI · 보호설정 · 이미지 군더더기"
assignee: "정성윤"
role: "infra"
status: "done"
sprint: 4
priority: 4
date: 2026-09-15
depends_on:
  - "w4-release-tag-gate"
paths:
  - "infra/systemd/converge.sh"
  - "infra/elasticsearch/*"
  - ".dockerignore"
---

## 무엇을

`decisions/111`(릴리스 태그 게이트)에서 **「이번에 하지 않은 것」으로 미뤄둔 다섯**을 닫는다.

## 왜

전부 「지금 터지지는 않지만 조용히 새는」 부류다. 미결 항목에만 적어두면 `111` 이 경계한 바로 그
방식으로 — 어겨도 아무 일이 안 일어나서 — 밀린다.

## 완료 조건

- [x] **① ES 이미지** — `release.yml` `paths` 에 `infra/elasticsearch/**` · `es-image` 잡 · 태그 게이트에 `es`
- [x] **② `converge.sh`** — 부팅 시 `callguard-call-mediator` 롤아웃도 확인
- [x] **③ 중복 CI** — `test.yml` push 트리거를 `[main]` 으로 (⚠ `concurrency` 통합은 머지를 막아 쓰지 않음)
- [x] **④ `branch-protection.json`** — 라이브 룰셋에 맞춤(검사 다섯 · 승인 0건)
- [x] **⑤ 이미지 군더더기** — `.dockerignore` 에 `**/tests` 계열 + `ai/apps/evaluation`
      (`call_guard`·`voice_signal` 은 남김 — C-6·D-5 자리)
- [x] ⑤ 의 사각지대 차단 — `test_image_layout.py` 가 `.dockerignore` 도 함께 본다
- [x] 태그 올림 — server `0.1.12` · call-mediator `0.1.5`
- [x] 문서 동기화 — `CLAUDE.md` §7(필수 검사 다섯 · CI 트리거) · `test.yml` 낡은 주석 둘

근거: `_project/decisions/114-미결로-남겨둔-CI-결함-다섯을-닫는다.md`
