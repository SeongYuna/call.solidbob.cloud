# 115. `gateway` 를 `call-mediator` 로 개명한다

- 날짜: 2026-09-17
- 작성: 정성윤
- 상태: 채택 (**저장소 개명 완료 · 운영 전환은 머지·배포 뒤** — 아래 「전환 순서」)
- 관련: `decisions/109`(게이트웨이는 하나) · `402`(첫 dev 경로) · `015`(브랜치 개명 — 옛 기록을 고치지 않는 선례) · `114`(룰셋 필수 검사 다섯)
- 티켓: `w5-call-mediator-rename`

---

## 맥락

`services/gateway` 는 오디오를 받아 STT 로 넘기고, 결과를 서버로 넘기고, 서버가 마스킹해 돌려준 것만 대시보드로
중계한다(A-1~A-4). **인증·속도 제한·TLS 를 맡는 경계 장비가 아니다** — 그 일은 Traefik Ingress 가 한다.
그런데 「게이트웨이」라는 이름이 「API 게이트웨이 = 보안 장치」로 읽혀 팀 안팎에서 오해가 반복됐다
(2026-09-17 세션에서도 *"원래는 보안과 관련된 것 아니냐"* 는 질문이 나왔다).

## 선택지

| 후보 | 판단 |
|---|---|
| `proxy` | 고치려는 오해를 더 정확한 말로 부르는 셈이다(리버스 프록시 = 경계 장비). 클러스터에 Traefik 이 이미 프록시다 |
| `mediator` / **`call-mediator`** | 보안 뉘앙스가 없다. 생산자·서버·대시보드 사이를 잇는 **GoF 메디에이터 패턴**을 쓴다는 설계 의도와 맞는다 |
| `relay` | 하는 일(중계)의 직역. 검토했으나 팀이 패턴 이름을 택했다 |

## 결정

**`call-mediator`.** 한국어 서술은 「콜 미디에이터」. **사람이 읽는 이름과 배선 식별자를 한 번에 전부 바꾼다.**

| 무엇 | 전 | 후 |
|---|---|---|
| 디렉터리 | `services/gateway/` | `services/call-mediator/` |
| CI job(필수 검사) · 릴리스 job | `gateway` · `gateway-image` | `call-mediator` · `call-mediator-image` |
| 이미지 | `seongyuna/callguard-gateway` | `seongyuna/callguard-call-mediator` (태그 `0.2.0` 부터) |
| k8s Deployment·Service | `callguard-gateway` | `callguard-call-mediator` |
| k8s 시크릿 · 키 | `gateway-tokens` · `GATEWAY_INGEST_TOKEN`·`GATEWAY_VIEW_TOKEN` | `call-mediator-tokens` · `CALL_MEDIATOR_INGEST_TOKEN`·`CALL_MEDIATOR_VIEW_TOKEN` |
| 공개 경로 | `https://server.solidbob.cloud/gateway/*` | `…/call-mediator/*` (`PUBLIC_PREFIX`·Ingress·프론트 허용 목록 함께) |
| 환경변수 | `GATEWAY_PORT` · `VITE_GATEWAY_WS_URL` · `VITE_GATEWAY_DEMO_BASE_URL` | `CALL_MEDIATOR_PORT` · `VITE_CALL_MEDIATOR_WS_URL` · `VITE_CALL_MEDIATOR_DEMO_BASE_URL` |
| 대시보드 런타임 오버라이드 | `?gateway=` · `callguard:gatewayUrlOverride` | `?call_mediator=` · `callguard:callMediatorUrlOverride` |
| 매니페스트 · 도커파일 | `gateway.yaml` · `gateway.Dockerfile` | `call-mediator.yaml` · `call-mediator.Dockerfile` |
| 프론트 식별자 | `GatewayClient` · `useGatewaySession` · `mockGateway` … | `CallMediatorClient` · `useCallMediatorSession` · `mockCallMediator` … |

**바꾸지 않은 것 — 의도다.**

- **진행 기록(`jekyll/_logs/`) · 결정 기록 · `STATE-archive.md` · 옛 기획서 판(`plan-rev*`·보완지시서·`docs/plan-rev4.1.md`).**
  그 시점의 사실이다(절대 원칙 8, `decisions/015` 선례). 거기의 `gateway`·「게이트웨이」는 지금의 `call-mediator` 다.
- **티켓 슬러그**(`w4-gateway-streaming-stt` 등) — 옛 기록이 그 주소로 링크한다. 본문 서술만 바꿨다.
- **AWS 의 NAT Gateway · 인터넷 게이트웨이** — 다른 물건이다.
- **사용량 장부 hostPath**(`/opt/callguard/stt-usage`) — 이름에 gateway 가 없었고, 바꾸면 월 누적이 0 으로 돌아간다.
- `server` 이미지는 주석·설명 문자열만 바뀌었지만 **이미지에 들어가는 경로라 태그를 `0.1.14` 로 올렸다**(`decisions/111` 규칙).

## 전환 순서 — 사람이 하는 일 (순서를 지킨다)

머지 **전**
1. Docker Hub 에 빈 공개 레포 `callguard-call-mediator` 를 만든다 — 없는 레포는 레지스트리가 **401** 을 돌려줘
   `tag-check` 가 「판정 불가」로 죽는다(2026-09-17 실측. 레포만 있으면 404 = 새 태그로 통과).
2. EC2 에서 시크릿을 **값 그대로** 새 이름으로 복사한다 — 안 하면 배포가 새 토큰을 만들어 Vercel 의 뷰 토큰이 무효가 된다.
3. Vercel `call-solidbob-cloud-kxu6` Production 에 새 이름 변수 둘을 **추가**한다(옛 것은 아직 지우지 않는다).

PR 을 연 직후
4. main 룰셋의 필수 검사 `gateway` → `call-mediator`. 복원본 `.github/ruleset-main.json`·`branch-protection.json` 은 이 PR 에 들어 있다.

배포 뒤
5. `curl https://server.solidbob.cloud/call-mediator/health` 확인.
6. EC2 에서 옛 `deploy/callguard-gateway`·`svc/callguard-gateway`·`secret/gateway-tokens` 삭제(적용 스크립트에 prune 이 없다).
7. Vercel 의 옛 변수 둘 삭제 · 로컬 `.env` 키 이름 변경.

명령은 런북 19-1 「개명 전환」에 있다.

## 근거

- 오해는 이름에서 나온다. 문서만 바꾸고 URL·변수에 `gateway` 를 남기면 **같은 질문이 URL 을 본 사람에게서 다시 나온다.**
- 운영 활성 통화가 0 이고 데모 단계라 **전환 창이 짧게 끊겨도 잃는 것이 없다.** 늦출수록 박힌 자리가 는다(오늘 Vercel 변수 셋이 더 생겼다).
- 검증: call-mediator 타입 검사·테스트 101/101 · `apps/call`·`apps/platform` 빌드 · server·ai pytest · 계층 계약 4종 · 사이트 빌드·링크 0건 깨짐.

## 남는 것

- **머지 전까지 문서는 `/call-mediator` 를 말하고 운영은 `/gateway` 로 돈다.** 전환이 끝나면 `STATE.md` 의 그 문장을 걷는다.
- `origin/ai` 에 `services/gateway/` 아래 미머지 작업(합성 통화 재생기 · 태그 `0.1.6`)이 있다 — main 을 받을 때 경로·이미지 이름·태그(`0.2.x`)를 맞춰야 한다.
- 홍보 페이지(`call-solidbob-cloud`, www)는 같은 이름의 변수를 **`/dev/text` 의 base** 로 읽는다 — 거기 넣을 값은 `wss://…/call-mediator` 다(`/ws?token=` 이 아니다). 지금은 비어 있다.

## 되돌리는 법

이 커밋을 되돌리고(`git revert`), 룰셋 필수 검사를 `gateway` 로, Vercel 변수·k8s 시크릿을 옛 이름으로 돌린다.
옛 이미지(`callguard-gateway:0.1.5`)와 옛 시크릿을 6·7번에서 지우기 전이라면 매니페스트만 되돌려도 돈다.
