# STATE — 지금 어디까지 왔는가

> 세션 인수인계용 비공개 메모. **지금 상태만 적는다.**
>
> - 세션에 무엇을 했는지 → `jekyll/_logs/` (`/progress/` 가 렌더링). **여기 적지 않는다.**
> - 아직 정하지 못한 것 → `jekyll/open-items.markdown`
> - 지난 세션 기록 → `_project/STATE-archive.md` (2026-08-24 ~ 08-27, 보관용)
>
> **⚠ 이 파일에 세션 기록을 쌓지 않는다.** 자기 영역에 해당하는 줄을 **덮어쓴다.**
> 맨 위에 블록을 끼워 넣으면 네 사람이 같은 자리에서 충돌한다 — 그게 2026-08-27까지
> 실제로 일어난 일이다(`_project/decisions/101`). 「최종 갱신」 줄도 그래서 없앴다.
> 마지막 갱신 시각은 `git log -1 --format=%ai -- _project/STATE.md` 가 갖고 있다.

---

## 현재

**3주차** / 8스프린트 (2026-08-20 ~ 2026-10-27). 1주차 목표 6개 전부 달성.

성공 조건은 F-2가 아니라 **STT 오류 내성 실험(4.2절) + 검색 품질 개선 수치**다.
F·G·H·I 동결 판정은 **6주차 종료 시점**이다(그 전까지는 적용되지 않는다).

---

## 영역별 상태

**자기 줄만 고친다.** 남의 줄은 건드리지 않는다 — 여기서 «자기»는 **그 영역을 실제로 고친 사람**이다.
담당 디렉터리 잠금이 풀려(`decisions/302`, 2026-09-10) `server/`·`ai/`·`infra/` 는 누구나 고치므로,
**남의 주 담당 영역을 실제로 고쳤으면 그 줄도 갱신한다.** 아래 «담당» 열은 **주 담당**이다.

| 영역 | 주 담당 | 상태 |
|---|---|---|
| `server/` | 장민석 | 스포크 5종 규칙·`ai/` 합산(`masking`·`closure_gate`·**`postcall`**·`retrieval`·`trigger`·`call_guard` + S3 있으면 `uploads`). 테스트 server 696 + integration 12 · ai 225 · 계약 4·3종 KEPT (09-15 실측). **09-15**: 통화 후 초안 501 걷음 — **규칙 발췌**(`decisions/306`, 유형은 null, 품질 측정 불가) · **초안 저장**(`call.summary_text`·`follow_up_action` draft, 확정본은 409 로 보호 — 읽는 API·확정 API 는 아직 없다) · **상담원 전용 토큰**(`decisions/307`) — `agent_token`(해시만) · `/admin/agent-tokens` · `POST /hub/blacklist-requests` 는 토큰 필수·`requested_by` 본문에서 제거. 스키마 26 테이블 — 운영 DB **26 테이블 — 이름이 `schema.sql` 과 완전 일치**(09-15 서버 파드 출력 대조, `agent_token`·`admin_account`·`closure_item` 있음. 컬럼은 이름만 봄) · **서버 `0.1.8` 운영 배포 완료**(PR #86 머지 `8223579` → release 성공, 09-15) — `/health` spokes 에 `postcall` · `/admin/agent-tokens` 노출 · 블랙리스트 요청 토큰 없음·가짜 토큰 401(운영 `agent_token` 조회가 돈다). ⚠ **관리자 API 는 운영에서 전부 500**(Redis·시크릿 없음, `w4-admin-auth-runtime`) — 운영에서 토큰 발급 불가. **09-15 뒤이어**: 관리자·상담원 가드가 헤더 없으면 인프라 전에 401(운영 반영 전) · **추천 저장 + 카드 `card_id`**(`decisions/308`, 통화 없으면 404, 운영 반영 전) · `frontend` 를 `server` 에 병합(조서희 요청 5건은 미결로 전달). **통화 기록 조회 `GET /hub/calls/{id}/record`** · **블랙리스트 만료 연장·단축 + 이력**(`decisions/309`, 205 철회 — 스키마 27 테이블, 운영 마이그레이션 필요) · 만료된 등록이 같은 고객 재승인을 막던 버그 수정. **09-15 서버 `0.1.9` 운영 배포 완료**(PR #88 머지 `76423e8` → release 성공, 운영 DB 27 테이블 이름 일치 확인) — `/openapi.json` 34경로 · 헤더 없는 관리자 요청 401(전엔 500) · `…/record` 없는 통화 404. 테스트 server 739 + integration 16. 고객 연결(발신 번호 → HMAC → `GET /hub/calls?customer_id=`)은 로컬 실DB 로 끝까지 확인. `POST /hub/calls`(통화 시작) 가 전사 저장의 외래키 선행 조건. CORS 는 `CORS_ALLOWED_ORIGINS`. 응답 전 필드 문자열화(`StrField`, §7.3 정본과 어긋남 — 미결). 콜 미디에이터 알림 3종(검색 중·콜 가드·필요서류) **09-15 켰다**(프론트 파서 main 반영, 콜 미디에이터 `0.1.4` — 운영 반영 전). **요약 확정 API**(`decisions/310`, 상담원 토큰) · **연장 누적 상한 승인일+365일**(`decisions/309` 추가) · **확정 요약 재수정 + 이력**(`decisions/311`) · **블랙리스트 문장 보존 정리 180일**(`decisions/312`, 관리자 API) · **J-5 인입 전 배정 판정 API + 베테랑 기준 설정**(`decisions/313`, `app_setting`) — **09-15 서버 `0.1.10` · 콜 미디에이터 `0.1.4` 운영 배포 완료**(PR #90 머지 `c25d225`, 운영 DB 29 테이블 이름 일치 확인 · `/openapi.json` 40경로 · 새 관리자·상담원 경로 헤더 없음 401). 테스트 server 780 + integration 20 · call-mediator 101. ⚠ **운영·Neon 스키마 적용 여부 미확인** — 이 머신에 Neon 유효 자격증명·AWS 키가 없다. ngrok 터널 인계는 닫았다 |
| `ai/` | 류준 | **09-15 4~7주차 AI 티켓 대부분 착수·완료(로컬 측정, 운영 미반영)**. 검색: KoE5 dense + bge 리랭커(후보 5) **0.979 / MRR 0.919**(BM25 0.833/0.659) · RRF 하이브리드는 dense 보다 낮아 **비채택**(`decisions/206`) · 청킹 「1조항=1청크」 유지 · 결과 LRU 캐시. **C-5**: `ai/apps/pii_ner`(사전학습 NER + 규칙 두 겹) 골든셋 누락 **0**(규칙만 4) · 하네스 부분 마스킹 가짜 통과 수정. 오류 내성 곡선: 검색 10% 에서 0.979(낙관적 — 흉내 못 내는 몫 46.9%) · C-5 규칙+NER 누락 0/0/1/1/1. **B-4** `ai/apps/generation` 서류 목록 — 모델 **kanana 로 교체**(`decisions/207`, 원출력 환각 카드 96→27/96, 화면 0) · **C-1~C-4** `ai/apps/compliance` 규칙 v1(골든셋 1.0 은 상한, 실제 상담원 보류 절반 과탐지 2/4,952) · **D-1/D-2** `ai/apps/postcall_summary`(유형 제안 0.872, AI Hub 1,009 대화). 서버 배선은 전부 **설정이 있을 때만**(`PII_NER_MODEL_DIR` · `RETRIEVAL_*` · `GENERATION_MODEL`) — 이미지에 torch 가 없어 **운영은 여전히 규칙·BM25·스니펫**. 막힘: A-5 2건(AI Hub 505/71479 미신청) · D-5 음성 골든셋 없음 · 분류기 대조(학습 데이터 없음). J-5 는 장민석 님 `decisions/313` 에서 풀렸다. 테스트 ai 392 · server 787(main 머지 후) · 계약 3+4종 |
| 인프라 · CI | 정성윤 | CI 워크플로 4종(`test.yml` 4잡 · `pages.yml` · `release.yml` · **`tag-check.yml` 신규 09-14**) · main 보호. **09-14 릴리스 태그 게이트 정비**(`decisions/111`) — 레지스트리 조회 fail-closed · PR 시점 검사 분리 · `fetch-depth: 0` · `deploy`→`k3s-deploy`. 판정은 `scripts/check_release_tags.py` 한 벌. `sha-<커밋>` 전환은 **기각**(`converge.sh` 가 저장소 `newTag` 를 직접 읽어 매일 되돌린다). **룰셋 필수 검사 다섯** — `jekyll`·`ai`·`server`·`call-mediator`·`tag-check`(09-15 뒤의 둘 등록, `decisions/114`). 이제 태그를 안 올리면 머지 버튼이 잠긴다. **라이브 룰셋의 복원본은 `.github/ruleset-main.json`**(이미 있었으나 `contexts` 셋인 옛 판이라 09-15 에 라이브와 일치시켰다) — 룰셋을 고치면 이 파일과 `.github/branch-protection.json`(클래식 대비본)을 함께 갱신한다. **OIDC 신뢰 정책 확인 완료**(09-15) — `callguard-deploy-role` 은 `ref:refs/heads/main` 한정이고 GitHub OIDC 를 신뢰하는 역할은 그것 하나뿐이다. **사이트 배포 ✅ `https://docs.solidbob.cloud`**(DNS 는 클라우드플레어 — `decisions/102~104`). **저장소 소유권 `SeongYuna` 로 이전 완료**(09-03, `decisions/106` — 룰셋·Pages·협업자 전부 보존). **프론트 3종 배포 ✅ 정성윤 Vercel + Git 연동** — 소개 `www.solidbob.cloud`(`apps/platform`) · 데모 `call.solidbob.cloud`(`apps/call`, 옛 `apps/dashboard` — 2026-09-14 이름 변경, mock 모드) · **관리자 `admin.solidbob.cloud`(`apps/admin`, 09-15 신설 — 구글 로그인 실동작, 화면 데이터는 아직 mock 시드)**. 조서희 계정에서 무중단 이관(TXT 검증). **09-15 셋 다 Ignored Build Step**(`git diff --quiet HEAD^ HEAD -- ./`) — 그날 계정 하루 배포 한도에 걸렸다(PR #94 에서 둘 빨간 X, 필수 검사는 아니다). 프로젝트 이름↔도메인↔Root Directory 대조표는 **런북 18-4**. ⚠ **`main` 머지로 자동배포가 실제로 도는지는 아직 안 봤다.** **운영 AWS 는 떠 있다**(09-08~09-11) — EC2 k3s(server **`0.1.7`** · call-mediator `0.1.3` · ES nori, 지식베이스 98조항 적재 완료). **⚠ 위의 「main 머지로 자동배포가 실제로 도는지 안 봤다」는 서버 쪽에 한해 09-15 에 풀렸다** — PR #83 머지 → 이미지 0.1.7 → SSM 적용 → `/openapi.json` 변화까지 완주했다(`w4-swagger-deploy-probe`). **프론트(Vercel) Git 자동배포는 여전히 미확인이다. **09-17 실측 둘**: ① `apps/call` 이 안 바뀐 커밋의 대시보드 Redeploy 는 Ignored Build Step 에 걸려 1초 만에 Canceled — CLI `vercel deploy --prod --force` 로 우회했다(저장소 루트에 `.vercel/` 링크 남김, gitignore) ② 환경변수만 바꾼 재배포는 취소되지 않는다. 상담원 화면(`kxu6`) 프로덕션에 `VITE_CORE_API_URL`·`VITE_CALL_MEDIATOR_DEMO_BASE_URL`·`VITE_CALL_MEDIATOR_WS_URL`(뷰 토큰 포함) 반영 완료 — 번들에 구워진 구독 주소로 운영 콜 미디에이터 `/ws` 열림 확인** + RDS `callguard-pg`(`decisions/108`). **콘솔로 세웠고 `infra/terraform/` 은 설계서로만 남는다** — `destroy`→`apply` 재현 경로가 없다. ⚠ 자리표시자 `ai` DNS 레코드는 아직 살아 있다(09-14 실측 `216.198.79.1`). **관리자 로그인 ✅ 운영에서 실제 로그인 성공**(09-15, `decisions/112` · 런북 18-3) — 세션 Redis 파드(클러스터 안·휘발) · `server-env` 키 4종 · CORS 에 admin 오리진 · `admin_account` 행 1건. ⚠ 그 행의 `agent_id` 가 NULL 이라 **블랙리스트 승인·해제는 409** 다(`decisions/304`). **A(STT) 는 `services/call-mediator` 로 존재하고 배포돼 있다**(`decisions/109`·`402`) — **09-17 `gateway` → `call-mediator` 개명**(`decisions/115`, 저장소 전부 · 이미지 `callguard-call-mediator:0.2.0` · server `0.1.14`). ⚠ **머지·배포 전이라 문서는 `/call-mediator` 를 말하고 운영은 아직 `/gateway/*`·`callguard-gateway:0.1.5` 로 돈다** — 전환 순서는 런북 19-1 「개명 전환」·티켓 `w5-call-mediator-rename` — 옛 「코드 0줄」 서술을 09-14 에 걷었다. 배치 전사 `scripts/transcribe_batch.py` 는 결함 3건 수정했으나 **실제 API 경로 여전히 미검증** — 이 머신에 오디오도 `.venv` 도 없다 |
| `apps/` | 조서희 | 대시보드: `/` = 대기화면 ⇄ 어시스트/요약. `ko-masking`은 권한 확인 후 스팬 클릭으로 원문 토글. `ko-grant-delay` 욕설은 별표 마스킹+배너. 랜딩: 다크 레퍼런스 + 해/달 토글. **09-09**: 프론트 계약에 `fired` 반영(`decisions/401`) — 검색 안 함/결과 없음/결과 있음 3상태 구분 + 카드 대기 중 로딩 UI. 실서버엔 로딩 신호가 없어(§7.3 미정) 라이브 모드는 아직 스피너가 안 뜬다. **09-10**: 통화 후 처리 화면에 블랙컨슈머 수동 분류 카드(C-6 확장) 추가 — 자동 탐지 아님, 관리자 알림은 mock. `main`(J 블록) 병합 후 프론트 타입을 09-09 스키마 QA에 맞춤(`BlacklistEntryItem.display_hint` 제거·`evidence_snapshot_at` 추가). ⚠ 블랙컨슈머 카드와 J 블록 전환 요청이 의미상 겹침 — [미결](/open-items/), 결정 기록 미작성. **09-11**: `services/call-mediator`(Node.js) 신설(정성윤 담당 경계 넘음, `decisions/402`·`w3-gateway-dev-testcall`) — 전화 사업자·Google STT 자격증명 없이 브라우저 Web Speech API로 `/dev` 개발용 테스트 콜 구현. 대시보드 `callMediatorUrl()`에 `?call_mediator=` 런타임 오버라이드 추가(Vercel 빌드타임 env 권한 없이 라이브 모드 전환). 개인 Vercel(`call-solidbob-cloud.vercel.app`)에 배포 확인. **로컬 콜 미디에이터(ngrok)→배포 백엔드→대시보드 엔드투엔드 실측 성공** — 실제 폰 발화가 DB에 영구 저장되는 것까지 확인. 그 과정에서 장민석 블로커("call 행 생성 경로 없음")가 팀 쪽에서 해결된 것도 확인함(`decisions/301`). **09-14**: `apps/dashboard`→`apps/call` 이름 변경(파생 경로 전부 수정, Vercel Root Directory 설정만 정성윤이 수동으로 남음). **관리자 로그인 신설** — 구글 OAuth만(회원가입 없음), access token JWT+Redis 5분·refresh token RDS 10분 회전(`server/apps/admin_auth/`, `decisions/403`). `admin_account`·`admin_refresh_token` 테이블 추가. ⚠ 실제 브라우저 로그인은 Google Client ID·로컬 Redis 발급 전이라 미확인 — [w4-admin-google-login](/backlog/w4-admin-google-login/). `main`을 받아 `frontend`에 머지·푸시(`d6efaaa`) — `services/call-mediator`는 정성윤 님의 09-11 정식 콜 미디에이터로 교체됨(`decisions/109`). 머지로 드러난 **`?call_mediator=` 허용 목록 없음** 보안 구멍도 같은 세션에 고침 — `isAllowedCallMediatorUrl()` + `CallMediatorOverrideBanner.tsx` ([w4-gateway-override-allowlist](/backlog/w4-gateway-override-allowlist/)). **09-15**: Flutter 개인 실험(`decisions/405`)에 `requests_tab` 패턴을 재사용한 "상담원 계정 생성" 탭 추가. F-2·C-6 프론트 계약을 서버 실측에 맞춤 — `ClosureEvent.closure_type`→`procedure`+`verdict complete/incomplete`(`decisions/305`), `CallGuardFlag.category`를 `insult/threat/sexual/distress` 4종으로 통일하고 distress는 폭언과 다른 배너·문구로 분리(`call_guard_dto.py` 그대로). [w4-dashboard-live-contract](/backlog/w4-dashboard-live-contract/) 착수 — `apps/call`·`apps/admin`을 실제 `/hub/*` REST에 연결(통화 목록·자막 조회, 수동 검색, 블랙리스트 생성/승인/해제, 콜가드 집계). ⚠ **다 붙이진 못했다** — 카드 피드백은 추천 카드 응답에 `card_id`가 없어 보류, 상담기록 재생 화면은 mock 시나리오(카드·종결·감정분석 재생)와 실제 API(목록+자막뿐) 모양이 달라 재설계 필요, 관리자 지식베이스 갭 화면도 실제 계약(`module/description/status`)과 mock 집계(`query/found`) 모양이 달라 아직 연결 안 함. `apps/admin` 현황판을 좌(통계 카드 4개)+우(recharts 도넛) 2단 레이아웃으로 재설계. **09-15 뒤이어**: `server` 병합분(장민석 `frontend` 병합 대조 5건)을 반영 — 블랙리스트 요청에 상담원 토큰(`?agent_token=` → sessionStorage, `apps/call/src/lib/agentToken.ts`) 인증 추가·`requested_by` 제거, `submitCardFeedback`/`card_id`를 문자열로 정정, 관리자 만료 상한 24→12개월(`RequestsTab`·`EntriesTab`·`SettingsTab`), 블랙리스트 연장(`adminStore.extendEntry`)을 로컬 mock에서 `POST .../expiry` 실호출로 교체, 해제·연장 사유를 하드코딩 대신 실제 입력으로 받도록 `EntriesTab`·`AdminPanel` 수정, `SettingsTab`에 상담원 토큰 발급·목록·폐기 화면 신설. ⚠ 남은 것: `GET /hub/calls/{id}/record`(상담기록 재생) 화면 연결과 `GET .../expiry-changes`(연장 이력) 화면은 스코프 밖으로 남겨 뒀다. **09-15 재차**: `origin/server`를 `frontend`에 머지(요약 확정·재수정·J-5 설정·판정·보존 정리, `decisions/310~313`) — `apps/`는 영향 없어 빌드 클린. `SettingsTab.tsx`의 근속 연차 입력을 `GET/PUT /hub/routing-settings`에 연결(`adminStore.ts`에 `fetchRoutingSetting`/`saveRoutingSetting`, 저장 성공 응답으로만 상태 갱신, 상한 0.5~40년으로 정정). ⚠ 남은 것: 상담기록 재생·요약 확정 UI(재설계 필요), 블랙리스트 보존 정리 트리거(관리자 버튼 vs 인프라 CronJob 미정), J-5 배정 판정(`POST /hub/routing-decisions`) 호출 주체(콜 미디에이터 쪽, 정성윤 결정 대기). **09-15 세 번째**: 보존 정리 버튼(`SettingsTab`, 관리자 수동 트리거로 결정) 추가. 통화 후 요약 확정 연결 — 그 과정에서 `RealCallMediatorClient.wrapUp()`이 "계약 없음"으로 늘 실패하도록 박혀 있던 걸 발견(`decisions/306`으로 `POST /hub/calls/{id}/close`가 이미 생겼는데 프론트가 안 따라간 상태) — `closeCall`·`confirmSummary`(`coreClient.ts`) 추가, `CallMediatorClient.wrapUp`에 `segments` 인자 추가, `CallSummaryPanel`에 요약·유형·후속조치 편집+확정 폼 신설. **09-15 네 번째**: 요약 재수정(`decisions/311`) 연결 — 확정 카드에 "재수정" 버튼 추가, 사유 필수로
`POST .../summary-revision` 호출(`reviseSummary`, `coreClient.ts`). 남은 것: 상담기록 재생 화면 재설계, J-5 배정 판정 호출 주체. **09-15 다섯 번째(상담기록 재생 재설계)**: 착수 전 `historySegments`·`historyCards`(인라인 자막 재생용 상태)가 `TranscriptPanel`·`TermsPanel`에 이미 있는데 `App.tsx`의 `showSummary`(history면 무조건 요약 화면)에 가려 **실제로는 절대 렌더링 안 되는 죽은 코드**였던 걸 발견(`.claude/rules/call.md` 원래 설계와 실제 동작이 어긋나 있었다). 사용자 지시("둘 다 살리는 방향")로 `historyView: "record" | "transcript"` 토글을 신설해 요약 화면·인라인 자막 재생 둘 다 살렸다 — `openHistory`가 실 API 설정 시 `fetchCallTranscript` + `fetchCallRecord`(신규)를 병렬로 불러 채운다. 실 계약은 추천 카드와 필요서류 판정이 서로 다른 배열이라 `panelCardsFromRecord`로 변환(판정마다 표시용 카드를 하나씩 합성). 번역·TTS·콜가드·악센트힌트 재생은 실서버에 없어 항상 빈 채로 둔다. 확정된 요약은 폼이 잠긴 채 열려 곧바로 재수정 가능(`SummaryConfirmationForm`에 `initiallyConfirmed`). 버그 하나 발견·수정 — 대기화면에서 열면 `shell`이 `standby`로 남아 자막 보기 전환 시 대기화면이 대신 뜨던 것, `openHistory`가 `shell: "assist"`도 같이 정하도록 고침. 헤드리스 크롬+CDP(Node 내장 WebSocket)로 실 클릭 왕복 확인, 콘솔 에러 없음. `tsc --noEmit`·`vite build` 클린. 남은 것: J-5 배정 판정 호출 주체(정성윤 결정 대기), 블랙리스트 보존 정리 "해제" 요청(사용자 의미 확인 대기). |

---

## 실측값 (2026-09-09)

```
2026-09-09 · 골든셋 v1-150(156건) · 지식베이스 98조항 · 커밋 c9da0a3-dirty · run_id=2
ELASTICSEARCH_URL=http://localhost:9200 .venv/bin/python scripts/run_eval.py --runs 3 --record

[retrieval]    recall@5 0.833 ✅ · mrr 0.659 ✅ · n 96
[masking]      누락 2 ❌ · 패턴 오분류 1 · 과잉 0.0 · n 28   **절대규칙 위반**
[call_guard]   재현율 1.0 · 정밀도 1.0 · n 15              ⚠ 자기충족 — 상한이지 성능 아님
[closure_gate] 측정 불가 — 채점 대상 0건
[trigger / compliance / domain_routing]  측정 불가 — 미구현 또는 의도적 미배선
```

**⚠ C-5 절대 규칙이 처음으로 ❌ 다.** 08-27 의 「누락 0 ✅」은 표본 18건 위의 값이었다.
뚫린 둘은 **전부 P6(인명)** — `"저는 최지훈이고요"`·`"신청인 이름은 한서윤으로"` 가
규칙 폴백의 문맥 밖이다. 고칠 곳은 `ai/` NER(류준). 08-27 수치(0.857/0.702, n14)는
4개 도메인·20조항 기준이라 **무효다.**

<details><summary>2026-08-27 값 (4개 도메인·조항 20개 — 무효)</summary>

```
[retrieval] recall@5 0.857 · mrr 0.702 · n 14      [masking] 누락 0 · n 18
[closure_gate] 정확도 1.0 · n 16                    [domain_routing] 0.857 ❌ (B-0 폐기됨)
```
</details>

`eval_run.run_id` 로 DB 에 남는다(커밋·골든셋 버전·표본 수 포함, §5).
재현: 위 명령 그대로. 기본 골든셋이 `v1-150.json` 이라 `--golden-set` 을 안 줘도 된다.
ES 는 `docker build -t callguard-es:local infra/elasticsearch/` 후 9200 으로 띄우고
`scripts/index_knowledge_base.py --to-es --recreate` 로 98조항을 적재한다.

**⚠ 기준선으로 고정하지 않았다.** 절대 원칙 5(미달 시 CI 실패)를 켜면 미구현 때문에 계속
빨간불이다. **수치가 나온 것과 게이트를 거는 것은 다른 결정**이다 → `w2-baseline-gate`.

**⚠ trigger 는 구현이 있는데도 일부러 채점하지 않는다.** 이벤트 도착 시각이 없어 상수로
모형화하고 있어, 채점하면 p50=p95=346·발동률 1.0 이라는 **가짜 만점**이 나온다(절대 원칙 10).

---

## 지금 막혀 있는 것

| 무엇 | 누구 | 비고 |
|---|---|---|
| ~~STT 오류 내성 곡선 미측정~~ | 류준 | **09-15 쟀다**(`w5-error-tolerance-curve`·`w5-masking-recall-curve`) — 주입기 기반이라 낙관적. 실제 전사 곡선은 배치 전사 뒤 |
| **A(STT) 코드 0줄** | 정성윤 | 「필수」 블록인데 착수 흔적이 없다. 3주차 실시간화 전에 범위를 정해야 한다 |
| **배치 전사 실행 검증** | 정성윤 | 오디오가 있는 머신이 필요하다. `--dry-run` 대조 + 소량 5~10건 → `w2-stt-batch` 완료 |
| 트리거 스포크 배선 | 류준 | 마지막 501 이 여기 걸린다 |
| **P6·P7 NER 운영 반영** | 류준·정성윤 | 09-15 로컬 누락 0(`ai/apps/pii_ner`). **운영은 규칙만이라 골든셋 기준 4건이 그대로 뚫린다** — 이미지·모델 볼륨 결정 대기([미결](/open-items/)) |
| **AI Hub 505/71479 신청** | 류준 | A-5 본체가 여기서 막혀 있다. 승인에 시간이 걸린다 |
| ~~J 서버 어댑터·라우터~~ | ~~장민석~~ | **09-14 만들었다**(`w4-blacklist-api`) — 남은 것: 상담원 인증·`admin_account.agent_id` 채우기 |
| ~~F-2 규칙표·`closure` 테이블이 다산을 모른다~~ | ~~장민석~~ | **09-14 다시 만들었다**(`decisions/305`) — 골든셋 F-2 케이스는 류준 몫으로 넘어갔다 |
| ~~`transcript_segment` UPSERT 복합키 미반영~~ | ~~장민석~~ | **09-11 에 이미 고쳐졌다**(`w4-segment-composite-upsert`) — 09-15 단위 11 · integration 2 로 재확인 |
| ~~`call` 행 생성 경로 없음~~ | ~~장민석~~ | **`POST /hub/calls` 로 풀렸다**(`decisions/301`) |
| **운영 `document` 테이블 비어 있음** | 정성윤·류준 | `scripts/seed_documents.py` 를 운영 RDS 에 안 돌렸다(런북 17-3). 안 돌리면 콜 가드·추천 카드의 근거 조항이 NULL 로 저장된다 |
| 컴플라이언스(C-1~C-4) 분류기 | 류준 | 09-15 규칙 v1 로 501 은 걷었다. 명세의 분류기는 학습 데이터가 없다 |
| D-1~D-3 | 류준·장민석 | `server/apps/postcall/` 미생성. 7주차 |
| ~~B-0 0.857 ❌~~ | ~~팀~~ | **2026-08-28 폐기됐다**(`decisions/201`) — 다산 단일 도메인이라 라우팅할 대상이 없다 |

---

## 팀 회신 대기

| 누구 | 무엇 |
|---|---|
| **류준** | P6·P7 NER (지금은 `server/` 규칙 폴백. GS-056 이 한계를 고정) |
| **류준** | 다산콜DB **전량 전사 보류** — 시나리오 56개뿐이라 고유 텍스트 상한이 112건이다. 클래스 가중치(트레이너에 없음)부터 → [미결](/open-items/) |
| 류준 | nori 복합명사 분해가 주석 예시와 다름 (사용자 사전) |
| 류준 | ⚠ **사후 공유** — `golden-set/v1-50.json` 음성 6건 추가 · `ai/tests/test_eval_wiring.py` 배선 테스트 3건 |
| ~~정성윤~~ | ~~배포를 한 컨테이너로 할지~~ → **답 나왔다: 한 컨테이너·한 도메인**(2026-09-03, `decisions/105`). `ai.solidbob.cloud` 서술은 문서 5곳에서 삭제 |
| **조서희** | `ClosureType` `"사고·보상"` → `"보상"` (안 고치면 422) |
| 팀 | `segment_id` `string` vs `int` — 7.3절 **예시**가 틀렸다 |
| 팀 | 기획서 정본 — `jekyll/docs/`(800ms) vs `plan.md`(1,500ms). 팀 컨펌은 1,500 쪽 |

---

## 구조 (2026-08-26 확정)

```
server/   요청이 흐르는 길        계약(포트·DTO)·파이프라인 배선·클린 아키텍처
ai/       품질을 만들고 재는 쪽    청킹·BM25·리랭크·모델 학습·평가 하네스
```

의존 방향은 **ai → server 한쪽뿐**이다. 역방향은 `server/.importlinter` 계약 2 가 막는다.
**브랜치 이름 = 디렉터리 이름 = 담당자** — 류준 `ai`, 장민석 `server`, 정성윤 `PM`, 조서희 `frontend`.

> ⚠ **2026-08-26 이전 기록의 `ai` 브랜치는 장민석**이다. 이름이 사람을 갈아탔다.
> 옛 기록은 그 시점의 사실이라 고치지 않는다(절대 원칙 8).

`ai/` 모듈: `retrieval` · `evaluation` · **`call_guard`(C-6)** · **`voice_signal`(D-5)**.
`server/` 스포크: `masking` · `closure_gate` · **`blacklist`(J)**.
DB **22테이블** — 2026-09-09 스키마 QA 로 J 3종 + `call_guard_flag`·`voice_outlier` 추가,
`transcript_segment`·`blacklist_entry` 키 결함 수정(`decisions/205`). `db/schema.sql` 은
**생성물**이다 — 고칠 곳은 `db/generate_schema_docs.py` 의 `TABLES` 다.

**합성 루트**(`.importlinter` `root_packages` 에 **없는** 파일)는 누가 고쳐도 된다 —
`server/main.py` · `ai/provider.py` · `scripts/run_eval.py` · 양쪽 `tests/`.
협의를 절차로 요구하지 않는다(`decisions/023`).

---

## 결정 기록

공동 번호대는 **`024` 까지 찼다.** 담당자별로는 정성윤 `106`·류준 `205` 까지 썼다 —
정성윤 `1xx` · 류준 `2xx` · 장민석 `3xx` ·
조서희 `4xx` · 공동 `024~099` (`decisions/022` ④). 하루에 **세 번** 겹친 뒤 정했다.

**문서 우선순위**: 결정 기록 > 기획서 + 보완지시서 > 파생 문서(`CLAUDE.md`·`rfp-harness`·`jekyll/docs`).
기능을 추가하거나 바꾸려면 결정 기록을 쓴다 — 그것이 기획서를 고치는 공식 경로다.

---

## 내부 메모

- **파생 문서가 기획서보다 빡빡해진 사례가 2026-08-27 대조에서 3건 나왔다** — F·G·H·I 동결의
  「6주차 종료 시점에」 누락 · 「B·E·C-5 절대 사수」 누락(둘 다 `ee5c137`) · 도메인 4종의
  「예시로도」 추가(출처 없음). **팀이 "규칙이 빡빡하다"고 겪은 것의 상당수가 옮겨 적기였다.**
  대조 검사가 없어 우연히 찾았다 — [미결](/open-items/)에 올렸다.
- 이 저장소는 두 사람이 서로 모르고 같은 작업을 한 이력이 있다(사이트·ERD·골든셋 양식).
  **작업 전에 `jekyll/_logs/` 를 먼저 읽는다.**
- 원격 인증: `gh` = SeongYuna (**소유자·admin** — 2026-09-03 이전, `decisions/106`). 저장소 설정을 직접 바꾼다.
- 로컬 지킬 포트: 이 저장소 = **4000**. 다른 클론들이 4100·4200 을 쓴다.
