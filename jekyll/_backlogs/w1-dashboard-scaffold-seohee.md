---
title: "React 대시보드 스캐폴딩"
assignee: "조서희"
role: "app"
status: "done"
sprint: 1
priority: 12
date: 2026-08-26
requirement:
  - "B-5"
  - "C-5"
---

`apps/dashboard` 를 Vite + React 18 + TypeScript strict 로 스캐폴딩한다.
**이 티켓은 `w1-dashboard-scaffold`(장민석, 팀개편 전)를 대체한다.**
그 티켓은 이후 중복 정리로 보드에서 빠졌다. 기존 `assignee`는 작성 당시 기록이므로 소급 수정하지 않는다.

규칙은 `.claude/rules/dashboard.md` 를 따르되, 그 안의 `RecommendationCard` 예시(`source.doc`/`score`)는 구버전이다.
정본은 [7.3절 인터페이스 계약 v2](/docs/07/) (`source.doc_id`+`title`, `similarity_score`).

## 범위

- 3분할: 실시간 자막 / 추천 카드 / 개인정보 마스킹 로그. F-2 종결 모달
- 콜 미디에이터 클라이언트 real/mock 동일 인터페이스. `VITE_CALL_MEDIATOR_WS_URL` 이 없으면 mock.
  mock 데이터는 7.3절 예시값만 사용 (프로모션 할인 카드, 해지 종결 `blocked`)
- **상태관리 zustand — 팀 컨펌 필요.** 칸반·규칙에 합의된 방식이 없어 이번에 도입했다.
  PR 올릴 때 이 선택을 팀에 확인한다.

## 완료 조건

- `npm run typecheck` · `npm run build` 통과
- mock 시나리오가 자막 → 카드 → 마스킹 로그 → 종결(F-2) 순으로 그려진다
- 출처 없는 카드 미표시, 위험도/"안전합니다" 류 문구 없음

## 완료한 것 (2026-08-26)

`apps/dashboard` mock 스캐폴딩을 이 범위로 끝냈다. `typecheck` · `build` 통과.

- **화면**: 상단 2분할(자막 2fr · 경고 1fr) + 하단 전체폭 책갈피. 카드는 사이드바 목록이 아니라 수신 시 아래에서 펼쳐지고, 접기는 X. 탭에는 약관명이 아니라 카드 `title`.
- **mock 4도메인**: 금융보험 · 다산콜센터 · 쇼핑 · 질병관리본부. 헤더에서 도메인 선택. 7.3절 통신(요금제약관) 카드는 쓰지 않음.
- **F-2**: `ClosureType`은 상품해지 / 사고·보상 / 반품 / 교환. evidence는 `중도해지수수료_안내` · `약정혜택소멸_안내` · `고객확인_기록`. 금융은 blocked(1/3→2/3) 후 approved(3/3). blocked는 모달 없이 경고 패널에서 「근거 N건 중 M건 충족」. approved만 종결 모달. 다산·헬스는 종결 이벤트 없음.
- **마스킹**: 카드번호 4자리 전부, 유형 한글(P2 카드번호, P4 연락처). 위험도/"안전합니다" 없음.
- **재생**: `utterance_end_ms` 기준, 발화 간격에서 2초 단축(최소 1.5초).

상태관리는 zustand. 팀에서 다른 방식으로 정하면 바꾼다.

고객 화면(`apps/customer`)은 이 티켓 범위가 아니다. 009로 철회, 티켓 `w1-customer-screen` cancelled.
