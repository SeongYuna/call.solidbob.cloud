---
title: "A-5 통번역 자막 mock"
assignee: "조서희"
role: "app"
status: "done"
sprint: 2
priority: 5
date: 2026-08-28
paths:
  - "apps/dashboard/src/components/TranscriptPanel.tsx"
  - "apps/dashboard/src/types/contract.ts"
  - "apps/dashboard/src/mock/scenarios/dasan.ts"
requirement:
  - "A-5"
---

`decisions/201` §2. 고객 베트남어 → 한글 번역을 자막에 붙이고, 상담원 발화에는 TTS 「전송됨」만 표시한다.
§7.3 이벤트는 아직 없다 — open-items에 등록하고 프론트 타입만 임시 정의.

## 완료 조건

- 원문 아래 들여쓴 번역, 원문 앞 언어 배지. 새 색 없이 기존 회색조
- 상담원 줄에 스피커 + 「VI 전송됨」. 실제 음성 재생 없음
- 등본 재발급 mock과 이어짐. `typecheck` · `build` 통과
