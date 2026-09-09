---
title: "대기화면 복귀 · 최초 비밀번호 강제 설정"
assignee: "조서희"
role: "app"
status: "done"
sprint: 3
priority: 4
date: 2026-09-01
paths:
  - "apps/dashboard/src/components/ForcePasswordSetup.tsx"
  - "apps/dashboard/src/components/StandbyBackButton.tsx"
  - "apps/dashboard/src/components/ConfirmDialog.tsx"
  - "apps/dashboard/src/App.tsx"
---

어시스트·요약에서 대기화면으로 돌아오는 길과, 임시 비밀번호 최초 1회 강제 설정(mock).

## 완료 조건

- 실시간 헤더에 「대기화면」. 통화 중이면 확인 모달, 종료·기록 열람이면 바로 이동
- `mustChangePassword` 이면 `ForcePasswordSetup`만 보이고 건너뛰기 없음
---
