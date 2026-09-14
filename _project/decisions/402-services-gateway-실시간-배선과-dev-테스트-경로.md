# 402 — services/gateway 실시간 배선 신설 + 전화 사업자·STT 키 없는 /dev 테스트 경로

**날짜**: 2026-09-11
**상태**: 확정 — **게이트웨이 신설 부분(결정 1·2)은 `decisions/109` 로 일부 대체됨** (2026-09-11). `services/gateway` 는 main 의
정식 게이트웨이 하나로 두고, 여기 `/dev` 경로는 그쪽 `GET /dev`·`WS /dev/text` 로 옮겼다. **결정 4(대시보드 `?gateway=` 덮어쓰기)는 그대로 유효하다.**
아래 본문은 작성 시점 기록이라 고치지 않는다.

## 맥락

`services/gateway`는 `_project/decisions/012`(디렉터리 경계 = 담당 경계)상 정성윤 담당이고,
`STATE.md`(2026-09-09 기준)에 "A(STT)는 `services/` 디렉터리 자체가 없다 — 코드 0줄"로
기록돼 있었다. 사용자가 포트폴리오 드래프트 단계에서 실제 폰으로 통화 테스트를 하며
개발을 진행하고 싶다고 요청했고, 정성윤(서버 운영자)·장민석(백엔드)의 협조를 바로 받기
어려운 상황이라 조서희가 직접 만들었다(`decisions/023`에 따라 협의를 절차로 요구하지
않음 — 경계를 넘은 사실만 기록).

시도한 순서와 각각 막힌 지점:

1. **Twilio 연동을 먼저 만들었다** — 실제 전화번호로 걸려오는 통화를 받으려는 요구였으나,
   개인 프로젝트 단계에서 전화 사업자 계정을 만들 수 없다는 게 확인됐다("포트폴리오
   드래프트 상태에서 테스트만 할 것"). Twilio는 그 자체로 통신사(SKT/KT/LGU+)가 개인에게
   열어주지 않는 실시간 미디어 스트림 웹훅을 대신 열어주는 유료 서비스라, 가입 없이는
   대체 수단이 없다.
2. **Google STT 서비스 계정 키도 없었다.** 정성윤이 `w1-stt-billing-quota`(2026-08-25,
   상태 `done`)로 이미 만들어 둔 GCP 프로젝트(`callguard-506606`)와 키가 있었지만, 키
   파일이 정성윤 로컬 머신(`~/.gcp/callguard-stt.json`)에만 있고 저장소엔 없다(SEC-2,
   의도된 설계). "이건 내 파트가 아닌데" — 라는 사용자 지적이 타당했다: A-1/A-2 본체는
   원래 류준·장민석 몫이다.
3. **배포된 백엔드(`server.solidbob.cloud`)에 `POST /hub/calls`가 없어** 새 통화 ID로
   `/hub/transcripts`를 호출하면 500이 났다 — `STATE.md`에 이미 기록된 장민석 담당
   블로커("call 행 생성 경로 없음")와 일치했다. 정성윤에게 맡기고 기다렸고, 세션 중
   실제로 고쳐졌다(`decisions/301` 참고 — `POST /hub/calls`를 전사보다 먼저 보내라는
   409 검증이 추가됨). 고쳐진 뒤 로컬 게이트웨이 → 실제 배포 백엔드 → 대시보드까지
   엔드투엔드로 실측 확인했다(아래 "확인" 참고).

## 결정

1. **`services/gateway`(Node.js/Express/ws)를 신설한다.** `hubClient.js`가
   `POST /hub/calls`·`POST /hub/transcripts`를 호출하고, 마스킹 호출이 실패하면 그
   구간을 대시보드로 보내지 않는다(C-5 절대 원칙 — 마스킹 없는 원문을 내보내지 않음).
   `dashboardHub.js`가 `apps/dashboard`용 WebSocket(`/dashboard`)을 중계한다.
2. **전화 사업자(Twilio 등) 연동은 만들지 않는다.** 대신 `GET /dev` 페이지가 개발자 본인
   폰(또는 컴퓨터) 브라우저의 **내장 Web Speech API**로 그 자리에서 텍스트로 바꿔
   `/dev/media` WebSocket으로 보낸다 — 오디오 자체가 서버로 오지 않으므로 Google STT
   호출도, GCP 자격증명도 필요 없다. 이 경로는 COST-1 사용량 가드와도 무관하다.
3. **STT 품질 측정 용도가 아니다.** `/dev`는 "게이트웨이 → hub → 대시보드" 배선이 실제로
   도는지 개인적으로 확인하는 용도로 한정한다. 정식 파이프라인 품질(Recall@5 등)은
   여전히 `ai/apps/evaluation/` 골든셋 하네스가 낸 값만 쓴다(루트 CLAUDE.md §5) — `/dev`
   테스트 결과를 성능 수치로 인용하지 않는다.
4. **대시보드(`apps/dashboard`)에 런타임 게이트웨이 주소 오버라이드를 추가한다**
   (`lib/ws/types.ts`의 `gatewayUrl()`). `?gateway=<wss URL>` 쿼리로 방문하면
   `localStorage`에 저장돼 다음 방문부터도 유지된다. 빌드타임 환경변수
   (`VITE_GATEWAY_WS_URL`)는 Vercel 프로젝트 설정 접근 권한이 있어야 바꿀 수 있는데,
   배포 담당자(정성윤)의 협조를 바로 받기 어려운 상황이라 이 경로가 필요했다.
5. **팀 도메인(`call.solidbob.cloud`)이 아니라 개인 Vercel 계정
   (`whtjgml2002-6071s-projects/call-solidbob-cloud`,
   `https://call-solidbob-cloud.vercel.app`)에 배포해 확인한다.** `git push`가 아니라
   `vercel --prod` CLI로 직접 배포했다 — main 브랜치·팀 도메인은 건드리지 않았다.

## 근거

- **결정 기록이 기능 추가의 공식 경로다**(루트 CLAUDE.md §1). `services/gateway`는
  새 코드이자 담당 경계를 넘는 변경이라, 마무리 세션 기록(`_logs/`)만으로는 부족하고
  나중에 정성윤·장민석이 "이게 왜 여기 있는지" 추적할 수 있어야 한다.
- **재현율 우선(C-5)은 `/dev` 경로에서도 그대로 지켰다** — hub 호출 실패 시 그 구간을
  버리지, 마스킹 없는 원문을 대시보드로 보내지 않는다. 오디오 경로가 브라우저로
  바뀌었다고 해서 이 원칙을 예외로 두지 않았다.
- **측정하지 않은 것을 측정한 것처럼 쓰지 않는다**(절대 원칙 2·10) — 그래서 `/dev`가
  "배선 확인용"이지 "품질 측정용"이 아니라는 것을 명시했다. 브라우저 STT 엔진과
  실제 서버 Google STT는 품질이 다르다.

## 확인 (2026-09-11 실측)

로컬 게이트웨이(8080) → ngrok 터널 → 배포된 `https://server.solidbob.cloud` → 대시보드
WebSocket 리스너까지 엔드투엔드로 연결해, 실제 폰 발화("여보세요")가

1. 브라우저 Web Speech API로 텍스트 변환
2. `POST /hub/calls` → `POST /hub/transcripts` (마스킹 통과)
3. `GET /hub/calls/{call_id}/transcript`로 조회 시 DB에 영구 저장된 것 확인
4. 대시보드 쪽 WebSocket 리스너가 해당 이벤트를 실제로 수신

하는 것을 직접 확인했다. `POST /hub/calls` 미존재로 인한 500 블로커(위 맥락 3번)는
세션 도중 백엔드 쪽에서 해결됐다(`decisions/301`).

## 되돌리는 법

- `services/gateway/` 디렉터리를 통째로 지운다(다른 어떤 코드도 이 디렉터리를
  import하지 않는다 — 독립 프로세스).
- `apps/dashboard/src/lib/ws/types.ts`에서 `syncGatewayOverrideFromQuery`·
  `readGatewayOverride` 관련 코드를 빼고 `gatewayUrl()`을 원래대로(빌드타임 환경변수만)
  되돌린다.
- 개인 Vercel 배포(`whtjgml2002-6071s-projects/call-solidbob-cloud`)는 팀 도메인과
  무관하므로 되돌릴 필요 없이 그냥 방치하거나 삭제하면 된다.

## 승인

사용자 직접 지시로 진행 (2026-09-11).
