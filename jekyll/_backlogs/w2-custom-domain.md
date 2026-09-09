---
title: "커스텀 도메인 docs.solidbob.cloud 연결 (배포 사이트 404 수정)"
assignee: "정성윤"
role: "infra"
status: "done"
sprint: 2
priority: 3
date: 2026-08-28
paths:
  - "jekyll/_config.yml"
  - "jekyll/index.markdown"
  - "jekyll/CNAME"
  - ".github/workflows/pages.yml"
depends_on:
  - "w1-pages-deploy"
---

**무엇을** — 배포된 사이트에서 본문 링크(`/docs/09/`·`/toc/` …)가 전부 404 다.
프로젝트 페이지라 사이트가 `/call.solidbob.cloud/` 아래 놓이는데 링크 **405곳이 루트 절대경로**라
한 겹이 어긋난다. 상단 내비만 `relative_url` 을 써서 **내비는 되고 본문은 안 되는** 상태다.
커스텀 도메인을 붙여 사이트를 루트에 올리면 `baseurl` 이 `""` 가 되어 405곳이 그대로 맞는다.

**왜 이 방법인가** — 링크 405곳을 고치는 쪽은 네 브랜치 전부와 충돌하고, 새로 쓰는 링크마다
같은 실수가 재발한다. 클라우드플레어 경유는 네임서버를 통째로 옮겨야 하고 프록시가 GitHub 인증서
발급을 막아, 이 목적에는 얻는 게 없다. → `_project/decisions/102`

**한 것 (2026-08-28)**
- `jekyll/_config.yml` — `url` 설정 (baseurl 은 `""` 유지). ⚠ 오전엔 `call`, 오후에 **`https://docs.solidbob.cloud`** 로 확정(`decisions/104`)
- `jekyll/CNAME` 신규(`docs.solidbob.cloud`) — ⚠ Actions 배포는 이 파일을 읽지 않는다(표식·이관용)
- `jekyll/index.markdown` — 표지 「데모 사이트」를 「문서 사이트 `docs.solidbob.cloud`」 + 「데모 사이트 `solidbob.cloud`」 두 줄로
- `.github/workflows/pages.yml` — `--baseurl` 이 왜 자동으로 비워지는지 주석

**완료 (2026-08-28)** — `https://docs.solidbob.cloud/` 정상. **404 가 사라졌다.**

```
docs.solidbob.cloud → solidbob02.github.io → 185.199.109.153 (GitHub Pages)
/  ·  /docs/09/  ·  /toc/  ·  /progress/  ·  /kanban/  ·  /open-items/   전부 200
http:// → 301 https://          Enforce HTTPS ✅
인증서  Let's Encrypt, CN=docs.solidbob.cloud, 2026-08-28 ~ 11-26
```

**표지·목차·개발 로그·칸반·미결에서 내부 링크 86개를 수집해 전부 열어봤다 — 200 아닌 것 0건.**

밟은 경로: 클라우드플레어 존 이관(`decisions/103`) → `CNAME docs → solidbob02.github.io`(회색 구름)
→ Settings → Pages 커스텀 도메인 → Enforce HTTPS. 이름은 `call` → `docs` 로 바뀌었다(`decisions/104`).

**비용은 0원이다** — Pages(공개 저장소)·Let's Encrypt·Cloudflare Free 전부 무료다.
Settings → Pages 아래쪽 `Visibility` 의 「Start free for 30 days」는 **GitHub Enterprise 광고**이고
Pages 사이트를 **비공개로** 만드는 기능이라 이 프로젝트와 방향이 반대다(`CLAUDE.md §8` — 공개가 목적). 누르지 않는다.

**완료 조건** — ✅ `https://docs.solidbob.cloud/docs/09/` 200 · ✅ HTTPS 강제 ·
✅ 표지의 「문서 사이트」 주소와 실제 주소가 일치.

**남은 것(이 티켓 밖)**: `call.solidbob.cloud` 는 프론트 몫이라 클라우드플레어에 레코드가 필요하고,
`ai`·`server` 자리표시자는 AWS 배포 때 실제 주소로 바꾼다.
