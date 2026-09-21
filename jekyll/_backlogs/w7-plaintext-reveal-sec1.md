---
title: "원문 열람(plain_text)이 SEC-1 과 모순이다 — 기능을 정리한다"
assignee: "조서희"
role: "app"
status: "todo"
sprint: 7
priority: 81
date: 2026-09-21
requirement:
  - "C-5"
  - "SEC-1"
paths:
  - "apps/call/src/*"
---

## 무엇을

상담원 화면의 **마스킹 스팬 클릭 → 원문 토글**([w3-dashboard-mask-reveal](/backlog/w3-dashboard-mask-reveal/)·[w3-demo-mask-span-toggle](/backlog/w3-demo-mask-span-toggle/))을 정리한다.

## 왜

SEC-1 은 **「마스킹 전 원문이 DB·로그 어디에도 남지 않는다」**다. 원문을 보여 주려면 원문이 어딘가에 있어야 한다 —
**둘은 동시에 성립하지 않는다**([미결 항목](/open-items/)). mock 에서는 시나리오 파일에 원문이 있어 토글이 되지만, 실서버는 원문을 주지 않는다(줄 수 없다).
시연에서 mock 화면의 토글을 보이면 **「운영에서도 원문을 볼 수 있다」로 읽힌다.**

## 선택지 — 권고는 앞쪽

- **기능을 걷는다** — 라이브 모드에서는 이미 동작할 재료가 없다. mock 에서도 걷어 화면이 말하는 것과 시스템이 하는 것을 맞춘다
- mock 전용으로 남기고 화면에 「데모 데이터」를 적는다

## 완료 조건

- [ ] 고른 쪽을 `4xx` 결정 기록으로 남긴다
- [ ] 서버 응답에 `plain_text` 류 필드가 **없음을 단언하는 테스트**는 장민석 님 몫 — 필요하면 티켓을 따로 연다(한 티켓에 두 사람 작업을 담지 않는다)
