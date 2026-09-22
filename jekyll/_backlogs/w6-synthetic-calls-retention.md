---
title: "운영 DB 의 합성 통화 4건 — 시연용으로 남길지 지울지"
assignee: "정성윤"
role: "infra"
status: "todo"
sprint: 6
priority: 72
date: 2026-09-22
---

> **정성윤이 09-22 오늘 진행 기록·미결 항목을 보고 만든 티켓이다.** 담당은 «제안»이다 — 본인이 확인하고 맞으면 착수, 아니면 옮긴다.

## 무엇을

09-22 운영 확인으로 합성 통화 4건이 운영 DB 에 남았다 — `syn-prod-syn-010-20260922`(류준) · `syn-prod-syn-008-20260922`(류준) · `syn-prod-syn-010-seongyun-130124` · `syn-prod-syn-006-20260922-132934`(블랙리스트 요청 확인용, 콜 가드 3건).
남기면 시연·QA 때 상담기록 화면에 보이고, 지우면 자식 행부터(`closure_item` → `closure` → … → `call`) 지운다(09-21 방식).

## 완료 조건

- [ ] 팀 결정 — 남긴다(어느 것) / 지운다. [수동 QA](/backlog/w5-manual-qa-full-stack/) 3~6장의 재료로 쓸지도 같이
- [ ] 지우면 ID 를 명시해 지우고 행 수를 로그에 · 남기면 `stt_engine=synthetic-script` 로 구분됨을 화면 쪽(조서희)에 알린다
