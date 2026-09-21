---
title: "플랫폼 홍보 랜딩 페이지"
assignee: "조서희"
role: "app"
status: "done"
sprint: 1
priority: 15
date: 2026-08-27
paths:
  - "apps/platform"
---

`apps/platform` 신규. CallGuard 제품 소개용 마케팅 랜딩 페이지, `apps/dashboard`와
별개 배포 단위. 아직 팀 문서에 스펙이 없어 프론트가 처음 정의한다.

히어로 1차는 고객/상담원 문장 타이핑이었으나 폐기했다. 밝은 랜딩으로
다시 짰다 — 헤더 sticky+blur, 히어로 `min-height: 100vh`/`100dvh`에 세로 중앙,
우측 흰 카드(파형+키워드+추천 문서 제목), 4도메인 2.8초 순환. 아래 섹션은
전부 `padding: 88px 56px`. 데모 값은 `apps/dashboard/src/mock` 에서 옮긴다.
지어내지 않는다. 목업 파일 `reference/mockup.html` 은 저장소에 없었다.

## 완료 조건

- Vite + React 18 + TypeScript strict, 개발 서버 포트 3000
- 히어로가 키워드+카드 제목만 보여주고, FIN·SHOP·DASAN·HLT를 2.8초로 순환한다
- 섹션 순서: 헤더 · 히어로 · 문제 · 기능 3분할 · 도메인 4개 · 팀/CTA
- 히어로·헤더·푸터에 문의 CTA. 로드 시 히어로만 한 화면, 스크롤해야 다음 섹션
- 「놓치는 순간」 아래에 도입 챌린지 한 문단, 기능 카드에 기술 한 줄, 푸터는 「상담 신청」

## 아직 안 된 것

- 아키텍처·역할 문서에 `apps/platform`을 올릴지는 미결
- 공개 URL: [https://www.solidbob.cloud/](https://www.solidbob.cloud/) (2026-08-28 Vercel)

---

> **보드 최신화 (2026-09-21, 정성윤 — 사용자 지시로 전체 보드를 한 번에 맞췄다).** `in-progress` → `done`. 2026-08-27 부터 열려 있었다. 랜딩은 08-28 에 `www.solidbob.cloud` 로 나갔고, 그 뒤 작업은
[w2-platform-features-four](/backlog/w2-platform-features-four/)·[w3-platform-landing-refresh](/backlog/w3-platform-landing-refresh/)(둘 다 done)가 이어받았다.
> 「아키텍처·역할 문서에 `apps/platform` 을 올릴지」는 **그 뒤에 풀렸다** — `CLAUDE.md` §3 이 `apps/platform` 을 프론트 셋 중 하나로 적고 있다.
> 판정이 틀렸으면 조서희 님이 되돌린다.
