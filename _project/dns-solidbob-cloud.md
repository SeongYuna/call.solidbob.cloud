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

## 클라우드플레어 이관 후 목표 상태

위 4건 + 아래 1건. **프록시는 전부 회색 구름(DNS only)** — 근거: `_project/decisions/103`.

| Type | Name | Content | Proxy |
|---|---|---|---|
| `CNAME` | `call` | `solidbob02.github.io` | **DNS only** |

## 확인 방법 (권위 서버에 직접 묻는다)

캐시에 속지 않으려면 재귀 리졸버(1.1.1.1 등) 말고 권위 서버에 직접 물어야 한다.
이관 전에는 `ns.gabia.co.kr`, 이관 후에는 클라우드플레어가 배정한 네임서버가 권위 서버다.
