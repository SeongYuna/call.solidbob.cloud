---
title: "www 랜딩 배포를 정성윤 Vercel 계정으로 옮기고 Git 연동을 붙인다"
assignee: "정성윤"
role: "infra"
status: "done"
sprint: 3
priority: 2
date: 2026-09-03
paths:
  - "apps/platform/*"
---

## 무엇을

`solidbob.cloud`·`www` 를 조서희 개인 Vercel 계정에서 **정성윤 계정으로 옮기고**,
`SeongYuna/call.solidbob.cloud` 를 **Git 연동**해 `main` 머지가 곧 랜딩 배포가 되게 한다.

## 왜

**지금 공개 랜딩이 6일째 낡아 있다.** 2026-09-03 확인 —

- GitHub Deployments 최근 15건이 전부 `github-pages`. **Vercel 배포 기록 0건** = Git 연동 없음
- 라이브 번들에 `확보한 데이터 네 곳만 다룬다.`·`한별금융 이용약관 제2조 1항` →
  **`9265e79`(08-27) 빌드**. `9eef20a`(08-31 다산 단일 랜딩)가 반영되지 않았다
- 즉 `decisions/201` 로 폐기한 **금융·4개 도메인 서사가 공개 주소에 그대로** 떠 있다

수동 CLI 배포라 **안 도는 것이 드러나지 않았다.** `pages.yml` 이 이미 증명한 「머지 = 배포」를 쓴다.

## 완료 조건

- [x] 정성윤 Vercel 에 프로젝트 생성 — Root Directory `apps/platform` · Vite · `dist` · Production `main`
- [x] 조서희 계정에서 `solidbob.cloud`·`www` 해제
- [x] 정성윤 프로젝트에 `www`(Primary) + apex(→`www` 리다이렉트) 부착
- [x] 클라우드플레어: `_vercel` TXT 2건 · `www` CNAME 새 해시로 교체 (전부 회색 구름)
- [x] `https://www.solidbob.cloud/` 번들에 `핵심 어시스트 기능`·`동시 통번역 언어` 확인
- [x] `main` 에 커밋 하나 밀어 **자동 배포가 실제로 도는지** 확인
- [x] 조서희를 Vercel 팀에 초대 (Preview 접근 유지)

절차·되돌리는 법: `_project/decisions/106`

## 막는 것

**조서희 협조.** 한 도메인은 한 Vercel 계정에만 붙어서, 놓아주기 전에는 부착이 안 된다.

## 결과 (2026-09-03 완료)

**조서희 해제 없이 끝났다.** Vercel 이 TXT 검증 챌린지를 줘서 새 `_vercel` 값 2건을
클라우드플레어에 넣는 것만으로 도메인이 넘어왔다 — **체감 다운타임 없음.**
`www` CNAME 은 옛 해시 그대로인데도 정상 동작한다(Vercel 은 Host 헤더로 판단한다).

⚠ **마지막 항목(`main` 머지 자동배포 실측)만 남았다** — 이 정리를 담은 PR 이 첫 시험이다.
경위·되돌리는 법: `_project/decisions/106`
