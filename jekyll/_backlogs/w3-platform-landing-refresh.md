---
title: "플랫폼 랜딩 다크 리디자인"
assignee: "조서희"
role: "app"
status: "done"
sprint: 3
priority: 4
date: 2026-09-04
depends_on:
  - "w1-platform-landing"
paths:
  - "apps/platform/src/App.tsx"
  - "apps/platform/src/components/Hero.tsx"
  - "apps/platform/src/components/ValueComparison.tsx"
  - "apps/platform/src/components/DemoScenario.tsx"
  - "apps/platform/src/components/FeatureGrid.tsx"
  - "apps/platform/src/components/PrivacySection.tsx"
  - "apps/platform/src/components/ClosingCTA.tsx"
---

Lovable 레퍼런스 톤을 `apps/platform`에 적용. 내비 링크 제거·라이트 토글·전용 AICC 문구는 claim-260904.

> **[w1-platform-landing](/backlog/w1-platform-landing/) 의 뒷단계다 (2026-09-19 표시, 정성윤).**
> 같은 화면을 두 번 만든 것이 아니라 **1주차에 세운 랜딩을 3주차에 다크로 다시 칠한 것**이라
> `depends_on` 으로 잇는다(`CLAUDE.md` §4 — 일부러 나눈 단계). 세션 종료 검사의
> 「중복 티켓」 경고는 이것으로 빠진다. ⚠ **앞 티켓이 아직 `in-progress`** 다 — 랜딩은
> `www.solidbob.cloud` 로 떠 있으니 상태가 실제와 어긋나 보이는데, `apps/` 는 조서희 님
> 전담이라 상태는 건드리지 않았다([미결](/open-items/)에 적었다).

## 완료 조건

- 6개 섹션 카피가 레퍼런스와 같고, 라이트 모드로 전환된다
---
