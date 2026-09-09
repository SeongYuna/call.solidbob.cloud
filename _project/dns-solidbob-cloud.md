# `solidbob.cloud` DNS 레코드 원본 (비공개 · 복구용)

> ⚠ **왜 이 파일이 있나 (2026-08-28)** — 클라우드플레어 이관 작업 중 **가비아 존에서
> apex `A` 와 `www` `CNAME` 이 사라졌다.** 오전에 조회했을 때는 있었고, 오후에 권위 서버
> (`ns.gabia.co.kr` = 43.201.170.100)에 직접 물으니 `_vercel` TXT 2건과 NS/SOA 만 남아 있었다.
> **사라지기 전에 읽어 둔 값이 아래에 있다.** 다시는 사람 기억에 의존하지 않도록 여기에 남긴다.
>
> 공개 DNS 에 이미 노출된 값이지만 운영 정보이므로 `_project/`(비게시)에 둔다.

## 2026-08-28 오전 시점의 존 전체

| Type | Name | Content | 용도 |
|---|---|---|---|
| `A` | `solidbob.cloud` (`@`) | `216.198.79.1` | Vercel (apex). 응답은 `307 → https://www.solidbob.cloud/` |
| `CNAME` | `www` | ~~`8511982eb7ecc120.vercel-dns-017.com.`~~ → **`ea6aaafa6f786127.vercel-dns-017.com.`** | Vercel. ⚠ **같은 날 오후에 바뀌었다** — 아래 참조 |
| `TXT` | `_vercel` | ⚠ `vc-domain-verify=solidbob.cloud,e0cf45c2f12745718ea` — **이 값은 틀렸다(아래)** | Vercel 도메인 소유 확인 |
| `TXT` | `_vercel` | `vc-domain-verify=www.solidbob.cloud,66d9dffd08201b066afb` | Vercel 도메인 소유 확인 |

`MX`·`TXT(SPF)`·`AAAA`·`CAA` 는 **없다**(메일을 쓰지 않는다). 위 4건이 존의 전부다.

**apex 는 www 로 넘긴다** — 즉 `www` CNAME 이 없으면 apex 도 같이 죽는다. 실제로 그렇게 됐다.

## ⚠ apex 쪽 `_vercel` TXT 토큰은 한 글자가 빠져 있다 (2026-08-28 오후)

```
vc-domain-verify=www.solidbob.cloud,66d9dffd08201b066afb    토큰 20자
vc-domain-verify=solidbob.cloud,e0cf45c2f12745718ea         토큰 19자  ⚠
```

버셀 토큰은 같은 방식으로 생성돼 **길이가 같다.** 둘 다 16진수만 쓰는데 apex 쪽만
한 글자가 짧다 — **처음 가비아에 손으로 입력할 때 빠진 것으로 보인다.** 클라우드플레어에도
이 틀린 값이 그대로 복사돼 있었다(이관 과정의 실수가 아니라 원본이 틀렸다).

**어느 글자가 빠졌는지는 DNS 로 알 수 없다.** 정본은 **버셀 대시보드 → Settings → Domains →
Show DNS configuration** 이고, **복사 버튼으로** 가져와야 한다. 위 표의 apex TXT 값을
복구용으로 쓰면 안 된다.

## ⚠ `www` 대상값은 고정이 아니다 (2026-08-28 오후)

버셀 프로젝트가 바뀌면 **`…vercel-dns-017.com` 앞의 해시가 바뀐다.** 오전에 읽은
`8511982eb7ecc120` 은 오후에 `ea6aaafa6f786127` 이 됐고, 버셀 대시보드가
`Invalid Configuration` 으로 그 사실을 알렸다. **이 표의 값도 언제든 낡을 수 있다** —
정본은 항상 **버셀 대시보드의 Domains 화면**이다. 여기 값은 "잃어버렸을 때의 출발점"이지
"영원한 정답"이 아니다.

두 해시 모두 같은 IP(`216.198.79.1`·`64.29.17.1`)로 풀린다. **IP 가 아니라 호스트명 문자열
자체가 프로젝트 식별자**라 한 글자도 틀리면 안 된다.

## 현재 존 (2026-09-03 실측, 권위 서버 = 클라우드플레어)

**프록시는 전부 회색 구름(DNS only)** — 근거: `_project/decisions/103`.

| Type | Name | Content | 용도 |
|---|---|---|---|
| `A` | `@` | `216.198.79.1` | Vercel apex (→ `www` 307). **계정이 바뀌어도 같은 값** — 공용 IP |
| `CNAME` | `www` | `ea6aaafa6f786127.vercel-dns-017.com.` | 소개 페이지 `apps/platform`. **정성윤 계정** ⚠ 값은 옛 해시 — 아래 참조 |
| `CNAME` | `call` | `2ff10b62284009c0.vercel-dns-017.com.` | 데모 `apps/dashboard`. **정성윤 계정**(09-03 신설) |
| `TXT` | `_vercel` ×2 | `solidbob.cloud,d6ed4bb765cc19600009` · `www.solidbob.cloud,8b6c87dca5bf2a244207` | **09-03 교체** — 정성윤 계정 값 |
| `CNAME` | `docs` | ~~`solidbob02.github.io`~~ → **`seongyuna.github.io`** | GitHub Pages. ⚠ **아래 참조** |
| `CNAME` | `api` | Railway (`uivwfh8v.up.railway.app`) | 백엔드 임시. **TLS 미발급 — 안 열린다** |
| `CNAME` | `server` | `solidbob.cloud` | 자리표시자. AWS 배포 때 실주소로 |

**TTL 은 전부 Auto(300초), 프록시는 전부 회색 구름(DNS only).**

> ⚠ **`www` CNAME 이 아직 옛 프로젝트 해시다.** `ea6aaafa…` 는 조서희 프로젝트 식별자인데,
> 도메인 소유가 정성윤 계정으로 넘어온 뒤에도 **정상 서빙된다** — Vercel 엣지는 CNAME 의 해시가
> 아니라 **Host 헤더로 프로젝트를 판단**하기 때문이다. 해시는 Vercel 이 설정 검증에 쓰는 표식이라
> 대시보드에 경고가 남을 수 있다. 바꾸려면 `www` 행을 **`Edit`** 한다(`Add record` 는 거부된다 —
> 한 이름에 CNAME 은 하나뿐이다). **이 문서의 옛 판이 「호스트명 문자열 자체가 프로젝트 식별자라
> 한 글자도 틀리면 안 된다」고 적어 뒀는데, 실측으로 그렇지 않았다.**

> ⚠ **`call` 은 GitHub Pages 가 아니다.** 이 표의 옛 판은 `call CNAME solidbob02.github.io` 를
> 목표로 적어 뒀는데, 그건 `decisions/102` 안(지킬을 `call` 에 붙인다)이고 **`104` 가 철회했다** —
> 지킬은 `docs`, `call` 은 프론트엔드다.

## ⚠ `docs` CNAME 대상이 낡았다 (2026-09-03)

저장소 소유권이 `solidbob02` → `SeongYuna` 로 넘어갔다(`decisions/106`). 그런데 `docs` 는
아직 `solidbob02.github.io` 를 가리킨다. **지금은 동작한다** — 두 이름이 같은 GitHub Pages
애니캐스트 IP(`185.199.108~111.153`)로 풀리고 GitHub 이 리다이렉트도 유지한다. 다만 정본은
소유 계정 호스트이므로 **`seongyuna.github.io` 로 바꾼다.** `solidbob02` 계정이 사라지거나
이름이 바뀌면 그때 죽는다.

## ⚠ apex `_vercel` TXT 토큰은 그 뒤 고쳐졌다 (2026-09-03 확인)

이 문서가 「한 글자가 빠졌다(19자)」고 적어 둔 값은 **지금 20자로 맞다.**

```
문서에 적힌 값   e0cf45c2f12745718ea    19자  ← 낡음
현재 DNS        e0cf45c2f127745718ea   20자  ✅
www            66d9dffd08201b066afb   20자
```

누가 언제 고쳤는지는 기록이 없다. **위 「토큰이 틀렸다」 절은 당시 기록으로 남긴다**(절대 원칙 8).

## 확인 방법 (권위 서버에 직접 묻는다)

캐시에 속지 않으려면 재귀 리졸버(1.1.1.1 등) 말고 권위 서버에 직접 물어야 한다.
이관 전에는 `ns.gabia.co.kr`, 이관 후에는 클라우드플레어가 배정한 네임서버가 권위 서버다.
