---
title: "A-5 5개 언어 배지 일반화"
assignee: "조서희"
role: "app"
status: "done"
sprint: 2
priority: 5
date: 2026-08-31
paths:
  - "apps/dashboard/src/lib/language/languageMeta.ts"
  - "apps/dashboard/src/components/LanguageBadge.tsx"
  - "apps/dashboard/src/components/TranscriptPanel.tsx"
  - "apps/dashboard/src/mock/scenarios/"
requirement:
  - "A-5"
---

VI 하드코딩을 `targetLanguage` + `LANGUAGE_META`로 바꿨다. EN/JA/ZH/TH 시나리오는 이미 있었고 통화 필드와 배지만 맞췄다.

## 완료 조건

- 헤더(통화 ID 옆)와 자막·상담기록에 같은 국기 톤
- 상담기록 클릭 시 해당 통화 자막·언어로 전환
- 번역 텍스트는 `lib/translation/mockSource` — API 자리
---
