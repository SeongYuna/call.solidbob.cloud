# 104 — 지킬 사이트는 `docs.solidbob.cloud`, `call` 은 프론트엔드에 준다

**작성일**: 2026-08-28
**작성**: 정성윤
**상태**: 확정 — 저장소 반영 완료, **클라우드플레어 레코드 + Pages 설정이 사람 손에 남았다**
**갱신 대상**: `jekyll/_config.yml` · `jekyll/CNAME` · `jekyll/index.markdown`(표지) · `decisions/102`(주소 부분) · [w2-custom-domain](/backlog/w2-custom-domain/) · `jekyll/open-items.markdown`
**관련**: `decisions/102`(404 원인·커스텀 도메인) · `decisions/103`(존을 클라우드플레어로)

## 맥락

`102` 는 지킬 사이트를 `call.solidbob.cloud` 에 붙이기로 했다. 저장소 이름이 그것이고
표지에도 그렇게 적혀 있었기 때문이다. 그런데 **DNS 이관 중에 프론트 담당이 같은 이름을
버셀에 잡았다**(`call CNAME cname.vercel-dns.com`). 한 이름은 한 곳만 가리킨다.

## 결정

| 이름 | 무엇 |
|---|---|
| `solidbob.cloud` · `www` | 프론트엔드 랜딩 (Vercel, 이미 동작) |
| **`call.solidbob.cloud`** | **프론트엔드** — 제품 데모 화면 |
| **`docs.solidbob.cloud`** | **지킬 기획서·진행 기록 사이트 (GitHub Pages)** |
| `api` | Railway (백엔드, 임시) |
| `ai` · `server` | 자리표시자 — apex 를 가리킨다. AWS 배포 때 실제 주소로 바꾼다 |

## 근거

- **`call` 은 "통화"다 — 제품 쪽 이름이다.** 상담 화면이 붙는 게 문서 사이트보다 자연스럽다.
- **주소만 보고 무엇인지 알아야 한다.** 발표·제출 문서에 적을 주소라, `docs` 면 설명이 필요 없다.
- **사이트 내용과 맞는다.** 기획서 16절 + 진행 로그 + 칸반 + 미결 항목 = 문서 허브다.
  `plan`·`proposal` 은 기획서만 있는 것처럼 들려 실제보다 범위가 좁게 읽힌다.
- **바꾸는 비용이 거의 없다.** 문서 본문 링크 405곳은 **전부 루트 절대경로**라 도메인과 무관하고,
  `github.com/solidbob02/call.solidbob.cloud` 같은 저장소 주소는 저장소 이름이라 그대로다.
  실제로 고친 곳은 `_config.yml` · `CNAME` · 표지 · 결정 기록·티켓·미결 항목뿐이다.

> ⚠ **저장소 이름(`call.solidbob.cloud`)과 사이트 주소(`docs.solidbob.cloud`)가 달라진다.**
> 헷갈릴 수 있지만 저장소 이름을 바꾸면 기존 링크·클론 경로가 전부 깨지므로 그대로 둔다.

## 표지도 고쳤다

`데모 사이트: call.solidbob.cloud` 한 줄이었는데, **그 주소는 지금 열리지 않는다**(레코드 없음).
열리지 않는 주소를 데모라고 적어 두는 것은 절대 원칙 2 의 취지에 어긋난다. 두 줄로 나눴다 —
**문서 사이트 `docs.solidbob.cloud`** · **데모 사이트 `solidbob.cloud`**(실제로 열리는 곳).
`call` 에 프론트가 실제로 배포되면 데모 쪽 주소를 그때 바꾼다.

## 되돌리는 법

`jekyll/_config.yml` 의 `url`, `jekyll/CNAME`, 표지 `meta` 를 `call.solidbob.cloud` 로 되돌리고
클라우드플레어에서 `call` 을 GitHub Pages 로 돌린다. 그러면 `102` 의 원안이 된다.
단 그때는 프론트가 `call` 을 비워줘야 한다.
