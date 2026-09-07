---
title: "대시보드 마스킹 원문 열람"
assignee: "조서희"
role: "app"
status: "done"
sprint: 3
priority: 4
date: 2026-09-07
paths:
  - "apps/dashboard/src/components/MaskedText.tsx"
  - "apps/dashboard/src/components/TranscriptPanel.tsx"
  - "apps/dashboard/src/lib/customerRisk/maskSensitiveText.ts"
  - "apps/dashboard/src/mock/scenarios/dasan.ts"
---

랜딩 `MaskedDemoText`와 같은 권한 확인 → 스팬 클릭 원문 토글을 대시보드 `c_dasan_ko_masking`에 이식.

## 완료 조건

- 시나리오 데이터에 마스킹본/`plain_text` 쌍
- 권한 전에는 클릭 불가, 확인 후 개별·전체·⚠ 경고 토글
- 개별 열람 시 콘솔 mock 로그
---
