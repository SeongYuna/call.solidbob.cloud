---
title: "욕설 별표 마스킹"
assignee: "조서희"
role: "app"
status: "done"
sprint: 3
priority: 4
date: 2026-09-07
paths:
  - "apps/dashboard/src/lib/customerRisk/maskSensitiveText.ts"
  - "apps/dashboard/src/components/TranscriptPanel.tsx"
---

C-6 욕설을 자막에서 * 로 가린다. 글자 수 1:1, 조사·문장부호는 남긴다. 배너는 유지.

## 완료 조건

- abuse 구간이 글자 수만큼 *
- 배너·관리자 배지 유지
- 실시간·상담기록 동일
---
