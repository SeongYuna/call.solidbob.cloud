# CallGuard 멘토링 브리핑 — 2026-09-17 (4주차 종료 · 5주차 첫날 / 총 8스프린트)

> **이 문서가 무엇인가**: 오늘 멘토링에서 «지금 어디까지 왔고, 무엇이 남았는가»를 말하기 위한 정리다.
> 1차 자료만 읽고 썼다 — `_project/STATE.md`(09-15 18:14) · `jekyll/_logs/`(09-15·09-16 전부) ·
> `jekyll/_backlogs/` 티켓 187건 · `jekyll/open-items.markdown` · `docs/infra-runbook.md` · 결정 기록 `105~114`·`201~207`·`301~313`·`401~405` ·
> `infra/k8s/base/` · `.github/workflows/` · 코드 디렉터리 실물. 읽은 시점의 브랜치 머리:
> `origin/main` `6e755a8`(09-16 14:36, PR #96) · `PM` `c0b828b` · `origin/ai` `4c52035` · `origin/frontend` `6e61764`.
>
> **숫자는 전부 실측치이거나 «측정 불가»로 명시된 것만 썼다**(절대 원칙 2·10). 수치마다 출처를 붙였다.
> **인프라는 §7 에 따로 모았다.**
>
> ⚠ **팀 운영 변화 (2026-09-16)**: 남은 일은 전부 정성윤이 마무리한다. 아래 티켓의 `assignee`(류준·장민석·조서희)는
> 09-15 에 역할표대로 적은 «제안»이고, 실제 수행자는 정성윤이다. 이 문서의 «누구» 열은 그 전제로 읽는다.

---

## 1. 한눈에

| | |
|---|---|
| 기간 | 2026-08-20 ~ 10-27. 오늘 **5주차 첫날**(4주차 09-10~09-16 종료). 마감까지 **40일** |
| 성공 조건 | **STT 오류 내성 실험 + 검색 품질 개선 수치** (F-2 는 조건부·추가 성과) |
| 사수 대상 | **B(필요서류 검색) · E(평가 하네스) · C-5(개인정보 마스킹)** |
| 운영 | AWS EC2(k3s) + RDS + 콜 미디에이터 + 프론트 3종 Vercel 전부 떠 있다. **머지 = 배포**가 서버 쪽에서 실제로 돈다(09-15 완주) |
| 검색(B) | BM25 운영 **Recall@5 0.833** · 로컬 임베딩+리랭커 **0.979** — 목표 0.70 통과. **운영은 아직 BM25**(모델 미탑재) |
| C-5 | 로컬 규칙+NER **누락 0** · **운영은 규칙만이라 골든셋 기준 4건 뚫려 있다** — 절대 규칙 위반 상태가 운영에 남아 있다 |
| 오류 내성(E-3) | 0~20% 곡선 **쟀다**(09-15). 단 주입기가 실측 편집의 46.9% 를 못 흉내 내 **낙관 상한** |
| 가장 큰 미결 | ① 모델(NER·임베딩·리랭커)을 운영 이미지에 어떻게 실을지 ② 6주차 코어 기준선 판정(`w2-baseline-gate` 아직 todo) ③ A-5 데이터(AI Hub 505/71479) 미신청 |

---

## 2. 일정 위치와 성공 조건

| 주차 | 로드맵 목표 | 실제 |
|---|---|---|
| 1 (08-20~) | 기반·전제 확인 | 6개 전부 달성 |
| 2 | 베이스라인(BM25)·골든셋 50 | 달성 |
| 3 | 실시간화·C-5·골든셋 150 | 골든셋 150 ✅ · C-5 규칙 ✅ · **실시간 STT 는 4주차(09-11)에 됐다** |
| 4 (09-10~09-16) | 검색 품질(dense·RRF·청킹) | **로드맵 항목 4건 로컬 완료**(류준 09-15) + 로드맵에 없던 일이 대부분: 콜 미디에이터·블랙리스트(J)·관리자 로그인·운영 배포·스키마 따라잡기·통화 후 처리·프론트 실연동 |
| **5 (09-17~)** | **오류 내성 실험 (핵심 주차)** | 곡선은 이미 09-15 에 쟀다(w5 4건 done). 남은 w5 는 A-5 WER(막힘)·분류기 대조(막힘)·합성 통화(진행 중) |
| 6 | 생성·컴플라이언스 · **코어 기준선 통과 확인** | 생성·컴플라이언스는 로컬 done. **판정 티켓 `w6-core-baseline-check` todo** |
| 7 | 운영 관점 · **F-2 체크포인트** | postcall·캐시·토큰 비용 done. **F-2 체크포인트·지연 측정 todo** |
| 8 | 마감·발표 | 5건 todo |

**로드맵보다 구현이 앞서 있다.** 4~7주차 `ai/`·`server/` 티켓 대부분이 done 이고, 남은 것은 «판정·측정·운영 반영·문서» 쪽이다.

---

## 3. 기능 블록별 상태

| 블록 | 코드 | 로컬 측정 | **운영** | 화면 |
|---|---|---|---|---|
| **A-1~A-4 STT·콜 미디에이터** | `services/call-mediator`(Node, 토큰 2종, COST-1 캡) | 09-11 ngrok → 운영 백엔드 → 대시보드 E2E 성공 | **배포됨** `/call-mediator/*`, call-mediator `0.1.4`(main 은 `0.1.5`) | 라이브 모드는 `?call_mediator=` 로만. **공개 데모는 mock** |
| **A-5 통번역(차별점)** | ⓑ(서툰 한국어 전사)만 1차 범위 · 8kHz 페널티 분리만 됨 | **측정 불가 — 외국인 화자 음성 0건** | — | mock 시나리오 |
| **B 필요서류 검색(메인)** | BM25 + KoE5 dense + bge 리랭커 + LRU 캐시 | Recall@5 **0.979**(임베딩+리랭커) / 0.833(BM25) | **BM25 만**(이미지에 torch 없음). 지식베이스 98조항 ES 적재 ✅ · `document` 98행 ✅ | 카드·수동 검색 실연동 |
| **B-4~B-6 생성** | `ai/apps/generation` kanana(`decisions/207`) | 원출력 환각 카드 96→27/96, 화면 노출 0 | **미반영**(ollama 파드 없음, 켜면 p95 +0.9~1.0s 로 예산 초과) | 조항 스니펫 그대로 |
| **C-1~C-4 컴플라이언스** | 규칙 v1 스포크 + 서버 배선 | 골든셋 1.0(상한), 실제 상담원 발화 과탐지 2/4,952 | 배선됨 | **경고 UI 미연결**(`w6-compliance-alert-ui`) |
| **C-5 마스킹(사수)** | 규칙(P1~P5·P6 폴백) + `ai/apps/pii_ner`(NER) | 규칙만 누락 4 · 규칙+NER **누락 0** (n=28) · 곡선 0/0/1/1/1 | **규칙만 → 4건 뚫림** | 마스킹 자막 실연동 |
| **C-6 콜 가드** | `POST /hub/call-guard-checks` + 저장 + 콜 미디에이터 알림 | 1.0/1.0 (n=15, 자기충족) | 배포됨, 알림 켜짐(0.1.4) | 4종 배너(distress 분리) |
| **D-1~D-3 통화 후** | 규칙 발췌 초안 → 확정 → 재수정(+이력) | D-2 유형 제안 0.872(AI Hub 1,009) — **운영은 유형 null** | `0.1.10` 배포됨 | 확정·재수정 폼 실연동 |
| **D-4 공백 리포트** | 수집·조회·해제 API | — | 배포됨 | 관리자 갭 탭 실연동(09-16) |
| **D-5 통화 온도** | `ai/apps/voice_signal` 규칙(화자별 로버스트 z) | **측정 불가 — 음성 골든셋 없음**, 가설 2 반대로 나옴 | **호출부 없음** | mock |
| **E 하네스(사수)** | `ai/apps/evaluation` + `eval_run` DB 기록 | 09-09 정식 run_id=2 | CI 에서 회귀만 · **기준선 게이트 없음** | — |
| **F-2 필요서류 체크리스트** | 다산 규칙표 25개 + 자동 판정(`decisions/305`) | **측정 불가 — 골든셋 케이스 0건** | 배포됨 | 실연동 |
| **J 블랙리스트·J-5 배정** | 요청·승인·해제·연장·보존정리·배정 판정 API | — | 배포됨. **`admin_account.agent_id` NULL → 승인·해제 409** · **J-5 판정을 부르는 곳 없음** | 관리자 화면 실연동 |
| 관리자 로그인 | 구글 OAuth + JWT/Redis + refresh(RDS) | — | **운영 로그인 성공(09-15)** | ✅ |

---

## 4. 실측값 — 출처와 함께

### 4-1. 정식 하네스 (STATE.md 「실측값」)

```
2026-09-09 · 골든셋 v1-150(156건) · 지식베이스 98조항 · 커밋 c9da0a3-dirty · run_id=2 · 3회 최저치
[retrieval]    recall@5 0.833 ✅ · mrr 0.659 ✅ · n 96          (BM25)
[masking]      누락 2 ❌(P6 인명) · 과잉 0.0 · n 28             절대규칙 위반
[call_guard]   재현율 1.0 · 정밀도 1.0 · n 15                    자기충족 — 상한
[closure_gate] 측정 불가 — 채점 대상 0건
[trigger]      의도적 미채점(도착 시각 상수 → 가짜 만점) — 09-14 received_at_ms 로 풀려 운영 경로에서 잴 수 있게 됨
```

### 4-2. 류준 로컬 측정 (09-15, `STATE.md` `ai/` 줄 · 운영 미반영)

| 항목 | 값 | 비고 |
|---|---|---|
| 검색 KoE5 dense + bge 리랭커(후보 5) | Recall@5 **0.979** · MRR **0.919** | RRF 하이브리드는 dense 보다 낮아 **비채택**(`decisions/206`). 청킹 「1조항=1청크」 유지 |
| 오류 내성 곡선 — 검색 10% | 0.979 | 주입기가 실측 편집 46.9% 를 못 흉내 → **낙관 상한** |
| C-5 규칙+NER 누락 (0/5/10/15/20%) | 0 / 0 / 1 / 1 / 1 | 10% 이상의 1건은 주입기가 만든 비실재 음절(GS-037) |
| C-5 규칙만 (0%) | 누락 4 | 09-09 의 2건에 하네스 가짜 통과 수정으로 2건 더 드러남 |
| B-4 kanana 환각 | 원출력 27/96 (EXAONE 96/96) · 화면 노출 0 | 규칙 후처리가 걸러냄 |
| C-1~C-4 규칙 v1 | 골든셋 1.0(상한) · 실제 상담원 발화 과탐지 2/4,952 | 학습 데이터 없어 분류기 없음 |
| D-2 유형 제안 | 0.872 | AI Hub 1,009 대화 |

**이 값들은 `eval_run` 에 정식 기록된 값이 아니다.** 발표에 쓰려면 하네스 `--record` 로 다시 낸다(§5 규칙).

### 4-3. 말할 수 없는 것

- A-5 WER/CER(데이터 0건) · D-5 톤 판정 성능(음성 골든셋 없음) · F-2 정확도(케이스 0건) · 트리거 지연 분포(하네스에 도착 시각 없음) ·
  E2E 지연(`w7-latency-budget` 미착수) · 상담 품질 관련성(라벨 없음).

---

## 5. 4주차(09-10~09-16)에 실제로 한 일

- **운영이 «떠 있는 것»에서 «머지하면 바뀌는 것»이 됐다** — 릴리스 태그 게이트(`decisions/111`) · 필수 검사 5종 · PR #83 머지→이미지→SSM→`/openapi.json` 변화 완주 · CI 결함 5건 닫음(`114`).
- **서버 `0.1.5 → 0.1.10` 운영 배포 6회** — 통화 시작·전사 복합키·F-2 다산 규칙표·블랙리스트 API·상담원 토큰·통화 후 초안/확정/재수정·만료 연장·보존 정리·J-5 판정 API. 운영 DB **22 → 29 테이블**(마이그레이션 4개, 이름 일치 확인).
- **관리자 화면 신설·운영 로그인 성공** — `admin.solidbob.cloud` · 세션 Redis 파드 · 첫 관리자 행.
- **AI 로드맵 4~7주차 대부분 로컬 완료** — 임베딩·리랭커·청킹 비교·NER·오류 주입기·곡선 2종·생성·컴플라이언스·통화 후 요약·캐시·토큰 비용.
- **프론트 실연동** — mock 위에서만 돌던 화면(통화 목록·자막·수동 검색·블랙리스트·콜가드 집계·요약 확정·상담기록 재생·카드 피드백·지식베이스 갭)을 `/hub/*` 에 붙였다. `?call_mediator=` 허용 목록 구멍도 막았다.
- **테스트 음성 S3 보관**(`decisions/110`) · `document` 98행 적재 · 발신 번호 유출 검사 깜빡임 수정.
- **09-16**: 합성 통화 대본 10건 + 재생기(류준, `origin/ai` 미머지) · 카드 피드백·갭 탭 화면 연결(조서희, PR #96 머지).

테스트 규모(09-15 실측): server **783** + integration 20 · ai **392** · call-mediator **101~107** · 계약 4+3종 KEPT.

---

## 6. 남은 일 — 인프라 제외

### 6-1. 열린 티켓 (status ≠ done, 21건)

| 주차 | 티켓 | 상태 | 무엇이 남았나 |
|---|---|---|---|
| w1 | `w1-platform-landing` | in-progress | 완료 조건이 4도메인 순환(옛 것) — 조건 고쳐 닫으면 된다 |
| w2 | **`w2-baseline-gate`** | todo | **6주차 판정의 도구.** 기준선 미달 시 CI 실패 · 표본 0건은 통과 아님 |
| w2 | `w2-stt-batch` | in-progress | 오디오 있는 머신에서 5~10건 실행 검증만 남음 |
| w3 | `w3-a5-translation-spike` | in-progress | **AI Hub 505/71479 신청**(사람이 계정으로) → 등급별 WER |
| w3 | `w3-call-temperature` | in-progress | 음성 골든셋 없음 · 「감정분석」 대체 용어 확정 |
| w4 | `w4-admin-google-login` | in-progress | 운영 로그인은 09-15 성공 — 마지막 체크 닫고 done 처리 |
| w4 | `w4-dashboard-live-contract` | in-progress | 넷 다 붙었다(09-15·16) — done 처리 가능 |
| w5 | `w5-a5-wer-by-proficiency` | todo | 위 A-5 와 같은 막힘 |
| w5 | `w5-classifier-ner-benchmark` | todo | 학습 데이터 없음·파인튜닝 안 하기로 기울면 「측정 불가」로 닫음 |
| w5 | `w5-persona-sim-scripts` (ai 브랜치) | in-progress | 사람 검토 · 결정 기록 `2xx` · 운영 시연 · `source: synthetic` 분리 집계 |
| w6 | **`w6-core-baseline-check`** | todo | **판정 자체.** B·E·C-5 통과/측정불가를 갈라 로그로 남김 → F·G·H·I 착수 여부 |
| w6 | `w6-compliance-alert-ui` | todo | 위반+대체 표현 화면, 501 이면 「탐지 미동작」 표시 |
| w7 | `w7-f2-checkpoint` | todo | 구현 진행 vs 설계 문서 전환 판정 |
| w7 | `w7-latency-budget` | todo | 운영 경로 구간별 p50/p95(표본 수 포함) |
| w8 | `w8-f2-wrapup` | todo | 골든셋 F-2 케이스 · `DASAN-POLICY-1` 정정. ~~`verdict blocked→incomplete`~~ — **이미 코드에 반영돼 있다**(`gate.py:54`, 09-17 확인). 티켓·`CLAUDE.md` 서술이 낡은 것 |
| w8 | `w8-extension-pick` | todo | 6주차 판정 뒤 G-2 / H·I 택1 또는 「여유 없었다」 |
| w8 | `w8-final-docs` | todo | 파생 문서 ↔ 기획서·결정 기록 대조 · 숫자 출처 넷 |
| w8 | `w8-presentation` | todo | 후반 3일 |
| w8 | `w8-demo-rehearsal` | todo | 운영 주소로 한 통 · 대체 경로(녹화) |
| w4 | `w4-aws-resource-hygiene` | todo | → §7 |

### 6-2. 티켓 밖에 남은 것 (미결 항목 103건 중 코드·판정에 걸리는 것)

**품질·절대 규칙**
- **운영 C-5 가 규칙만이라 골든셋 기준 4건 뚫려 있다** — NER 운영 반영은 §7 「모델 탑재」에 달렸다.
- QA 페르소나가 합성 대본에서 찾은 규칙 결함 4건(재현 전): P7 과잉(「하시면」의 «면»·「~으로」의 «로»를 주소로 봄 — 09-15 「주민센터로 가시면」 과잉과 같은 뿌리) · P7 번지·호수 누락 · P6 문맥 없는 이름·띄어 쓴 외국인 이름 누락 · C-6 사전 밖 표현.
- 골든셋 **P1·P2·P3·P5 표본 0건** — 합성 대본이 채우지만 STT 미경유라 상한.
- B-6 「관련 문서 없음」을 낼 문턱 규칙이 없다(검색이 항상 5건) · 지식베이스에 여권 발급 조항이 없다.
- 골든셋 C-4 라벨이 기획서 C-4(대체 표현 제시)와 뜻이 다르다.

**계약·설계 결정**
- `admin_account.agent_id` 를 무엇으로 채울지(선택지 셋) — 이것 없이는 승인·해제·연장이 409.
- 상담원 토큰을 어디까지 걸지(카드 피드백은 설계상 걸면 안 됨) · 토큰 만료 없음.
- J-5 배정 판정을 누가 부르나(콜 미디에이터 `/dev` 콜이 통화 시작 직후 부를지) + 인증.
- D-5 를 누가 부르나(콜 미디에이터가 F0 특징값을 보낼지).
- 「감정분석」 대체 용어 · `distress_count` 미저장 판단 · 블랙리스트 만료 기간 · 베테랑 「3년」 근거 · 원문 열람 기능 폐기 여부 · 블랙컨슈머 수동 분류 카드 결정 기록.
- 상담기록 목록에 요약 미리보기 넣을지 · 공개 데모 라이브 전환(A/B/C).
- 학습 방향: 「모델을 학습하지 않는다」가 확정되면 결정 기록 + 티켓 3건 정리.

---

## 7. 인프라 — 따로 정리

### 7-1. 지금 구성 (실물 기준, 런북 머리말·`infra/k8s/base/`)

```
[브라우저] ─ Vercel ×3 ─ www / call / admin .solidbob.cloud     (정성윤 계정, Git 연동, Ignored Build Step)
     │ HTTPS
[Cloudflare DNS 회색 구름] → server.solidbob.cloud → EC2 1대 (Amazon Linux 2023, k3s)
     ├ Traefik Ingress + cert-manager(Let's Encrypt)
     ├ Deployment callguard-server   seongyuna/callguard-server:0.1.10 운영 (main newTag 0.1.13)   ← server/ + ai/apps 한 컨테이너
     ├ Deployment callguard-call-mediator  seongyuna/callguard-call-mediator:0.1.4 운영 (main 0.1.5, ai 브랜치 0.1.6)  Ingress /call-mediator
     ├ StatefulSet elasticsearch-0   seongyuna/callguard-es:9.5.1 (nori, ClusterIP, 볼륨)  지식베이스 98조항
     ├ Deployment redis              관리자 세션 5분, 볼륨 없음(decisions/112)
     └ 시크릿 server-env · gcp-stt-credentials · call-mediator-tokens (저장소 밖)
[RDS] callguard-pg  PostgreSQL 17, db.t4g.micro, SSL 강제 — 29 테이블 (09-15 이름 일치 확인)
[S3]  assist-apne2  uploads/ (테스트 음성, decisions/110) · IAM 역할 callguard-ec2-role (정적 키 없음)
[CI]  test.yml(4잡) · tag-check.yml · release.yml(plan→image/call-mediator-image/es-image→k3s-deploy, OIDC callguard-deploy-role main 한정, SSM 적용)
      · pages.yml(docs.solidbob.cloud) · main 룰셋 필수 검사 5종 · 복원본 .github/ruleset-main.json
[부팅] infra/systemd/converge.sh — main tarball 을 렌더해 적용, server·call-mediator 롤아웃 둘 다 본다
```

- **컨테이너 하나·도메인 하나**(`decisions/105`) · **콘솔로 세웠다** — `infra/terraform/` 은 설계서, `destroy→apply` 재현 경로 없음.
- 운영 EC2 등급은 로그·STATE 어디에도 실물 기록이 없다(런북 원안은 g4dn.xlarge, GPU 파드는 아직 없음). **콘솔에서 확인해 적어 둘 것.**

### 7-2. 4주차에 닫은 것 (인프라)

| 무엇 | 근거 |
|---|---|
| 릴리스 태그 게이트 fail-closed · PR 시점 검사(`tag-check.yml`) · `sha-` 전환 기각 | `decisions/111` |
| 룰셋 필수 검사 5종 · `ruleset-main.json`·`branch-protection.json` 라이브와 일치 | 09-15 |
| OIDC 신뢰 정책 실물 확인(`main` 한정, ID 고정형, 유일 역할) | 09-15 |
| CI 결함 5건 — ES 이미지 잡 · converge 콜 미디에이터 롤아웃 · 중복 CI · 보호 사본 · 이미지에서 tests 제외 | `decisions/114` |
| 「머지 = 배포」 서버 경로 완주 · 배포 프로브 넣고 걷음 | `w4-swagger-deploy-probe` |
| `admin.solidbob.cloud` · 세션 Redis 파드 · OAuth 키 · CORS · 첫 관리자 행 → 운영 로그인 성공 | `decisions/112`, 런북 16-3·17-4·18-3 |
| 운영 DB 마이그레이션 4개 적용 · 29 테이블 확인 · `document` 98행 적재 | 런북 17-3, 09-15 |
| S3 업로드 경로 운영 완주(CORS·역할·토큰) | `decisions/110` |
| Vercel 3종 Ignored Build Step · 대조표(런북 18-4) — 하루 배포 한도 사고 뒤 | 09-15 |
| 문서 동기화 5건 · `.env` Neon 잔재·`.gitignore` 구멍 수정 | 09-15 |

### 7-3. 남은 일 (인프라) — 우선순위 순

**🔴 지금 바로 — 절대 규칙·데이터 손상·비용**
1. **모델을 운영에 싣는 방식 결정** — NER(0.45GB)·KoE5(2.2GB)·리랭커(2.2GB)가 코드로는 있는데 이미지에 torch·가중치가 없어 **운영 C-5 가 규칙만이고 골든셋 4건이 그대로 뚫린다.** 선택지: ① 이미지에 굽기(런북 13-1 «~12GB» 예상) ② `hf-cache` PVC(런북 12-3) ③ 벡터 적재를 어디서 돌릴지(서버 파드는 BM25 만 적재). **GPU 인스턴스 여부·비용과 묶인다**(런북 21 — 8h×5일 $142 vs 24/7 $597).
2. **자동 중지 cron(런북 21-1) 상태 확인** — 티켓 두 건(`w3-cicd-release-pipeline`·`w3-k3s-image-and-manifests`)에 `[ ]` 로 남아 있는데 `decisions/111`·09-14 로그는 「매일 02시 중지」를 전제로 서술한다. **둘 중 하나가 틀렸다.** 걸려 있으면 매일 켤 때 Cloudflare `server` A 레코드 수동 갱신이 따라온다(탄력적 IP 안 붙임, 09-09 결정).
3. **AMI 스냅샷** — 「19장 통과 즉시」인데 아직 없다. 지금 구성이 EC2 안에만 있다.
4. **스키마가 배포보다 늦게 따라가는 구조** — 09-14 실제로 났다(`/health` 는 ok 인데 500). `tag-check` 에 「`db/migrations/` 새 파일 있으면 적용 확인 체크박스」를 붙일지 정한다.

**🟠 이번 주**
5. `w4-aws-resource-hygiene` — RDS 권장 사항 2건(퍼블릭 액세스·백업 보존이면 즉시) · Enhanced Monitoring 의도 확인 · 7월 잔재(두 번째 VPC·`admin-security`·`launch-wizard-1`) 정리.
6. **DNS 정리** — 자리표시자 `ai` 레코드 삭제 · `docs` CNAME 을 `seongyuna.github.io` 로 · `api`(Railway, TLS 미발급) 정리.
7. **미머지 브랜치 셋을 main 에** — `PM`(런북 18-4) · `origin/ai`(합성 통화 + call-mediator `0.1.6`) · `origin/frontend`(09-16 로그·STATE). 태그 충돌 주의(ai 가 call-mediator 0.1.6 선점).
8. **0.1.13 릴리스 성공 확인** — PR #94 머지로 `0.1.13`·`0.1.5` 가 구워졌어야 한다. 이 머신에 `gh` 가 없어 이 문서에서는 확인하지 못했다. 운영 `/admin/auth/test` 가 404 인지도 같이 본다.
9. **STT 일 캡 600초 = 하루 약 4통화** — 시연·리허설 일정에 맞춰 캡(`call-mediator.yaml`)과 GCP 쿼터를 조정할지.
10. `w2-stt-batch` 실행 검증(오디오 있는 머신) · `speaker=auto` 실제 구글 응답 검증(`decisions/303`).

**🟡 6주차 판정 전까지**
11. **`w2-baseline-gate`** — 기준선 미달 시 CI 실패 · 표본 0건은 통과 아님 · 미구현은 측정 불가 통과. 6주차 판정의 도구.
12. **측정 전용 t3.micro**(런북 22) — `w7-latency-budget` 을 g4dn 위에서 재면 오염된다.
13. 배포된 이미지 태그를 응답으로 알 방법(`app.version` 0.1.0 고정) — 빌드 인자 → `/health`.
14. ES `statefulset configured` 노이즈 — 매 릴리스에 찍혀 진짜 변경이 묻힌다.
15. 런북 실물 정정 잔여 — SSH 키 이름(`assist-key.pem` 아님) · 13장(클론)·16-2(Caddy) 원안 표시.
16. Vercel 설정을 `vercel.json` 으로 옮길지(`apps/` 전담 문제) · Root Directory 3종 눈으로 확인 · **Vercel 자동배포 실측은 아직 없다**(사이트 `pages.yml` 은 09-16 확인됨).
17. 관리자 토큰 TTL 운영값(지금 5분/10분은 테스트값) · 업로드 토큰 보관 · `uploads/` 수명 주기.

**⚪ 마감 즈음**
18. 파이프라인 자체(SSM·OIDC·렌더 방식)의 결정 기록 — 번호가 `108`·`111` 로 나가 아직 없다.
19. Terraform state 원격화 여부(혼자 쓰는 동안 로컬).
20. **프로젝트 종료 정리 순서**(런북 「되돌리기·정리」 8단계) · 전시용 최소 구성(문서 + 녹화, 월 ~$4) · GCP 무료 크레딧 만료 11-24 전 정리.

### 7-4. 인프라에서 팀·멘토 판단이 필요한 것

| 질문 | 걸린 것 |
|---|---|
| GPU 인스턴스를 켜서 모델(NER·임베딩·리랭커·kanana)을 운영에 올릴지, 아니면 「운영은 BM25+규칙, 품질 수치는 로컬 측정」으로 발표할지 | 비용($142 vs $597) · C-5 절대 규칙 · 4.3절 지연 예산(kanana 켜면 초과) |
| 공개 데모를 라이브로(B) 할지 mock 유지(A) 할지 | 「주소를 아는 사람은 자막을 본다」 수용 여부 · 상담원 로그인 없음 |
| J-5 판정·D-5 를 콜 미디에이터가 부르게 할지 | 계약(§7.3)·인증 |
| 자동 중지 + 수동 DNS 갱신을 유지할지, EIP($3.6/월)를 붙일지 | 운영 손질 vs 비용 |

### 7-5. 비용·리스크

- 예산 **$400**, 런북 정가 근사치 6주 **≈ $198**(GPU 8h×5일 기준). **실제 청구액은 이 문서에서 확인하지 않았다** — Cost Explorer 를 본다.
- 24/7 로 켜면 $597 → 예산 초과. 자동 중지 상태 확인(7-3 ②)이 곧 예산 관리다.
- 인스턴스에만 있는 것: 클러스터 구성(AMI 없음) · 업로드 토큰 · 콜 미디에이터 토큰 · **OIDC 신뢰 정책 원문**(코드로 없음, 콘솔 유일본).
- 「만들지 말 것」(NAT·EKS·ALB·Kinesis·ElastiCache·Multi-AZ·device plugin·직접 VPC)은 전부 지켜지고 있다.

---

## 8. 지난 멘토 피드백 6건 — 09-17 현황

| # | 피드백 | 09-11 판정 | 09-17 |
|---|---|---|---|
| ① | 감정은 톤·길이로 | 일부 | 톤 모듈 있음(`voice_signal`). **통화 길이 축은 여전히 보류**(통화 단위 음성 없음) |
| ② | 이상치가 얼마나 튀는지 | 일부 | 로버스트 z 있음. 기준값 3.5 관례값 그대로. **호출부 없음**(D-5 를 누가 부르나 미결) |
| ③ | 길이·톤으로 평가 | 일부 | 품질 라벨 없어 **못 잰다**. 저장 경로는 09-14 생겼으나 호출부 없음 |
| ④ | KPI 는 건수 | 원칙 반영 | **관리자 현황판이 실 API(콜가드 집계·블랙리스트)로 바뀌었다**(09-15). `fell_back` 집계 화면은 아직 없음 |
| ⑤ | 블랙리스트는 베테랑만 | 일부 | **J-5 판정 API 생김**(`decisions/313`, 기준 관리자 설정 가능). 폴백은 유지. **부르는 곳 없음** |
| ⑥ | 「감정분석」 대체 용어 | 미정 | **여전히 미정** — 화면 문구(`CallSummaryPanel.tsx`)에 남아 있다 |

---

## 9. 멘토에게 묻고 싶은 것 (제안)

1. **운영 반영 범위** — 검색 0.979·C-5 누락 0 이 로컬에서 나왔는데 운영은 BM25·규칙이다. 남은 40일에 GPU 를 켜서 운영까지 맞출지, 「운영은 경량·수치는 로컬」로 갈지. 어느 쪽이 발표에서 설득력 있나.
2. **오류 내성 곡선의 한계 표기** — 주입기가 실측 편집의 46.9% 를 못 흉내 낸다. 이 곡선을 성공 조건 수치로 쓸 수 있는지, 「상한」으로만 써야 하는지.
3. **A-5 데이터 0건** — 차별점인데 AI Hub 505/71479 승인 시간이 남은 기간과 맞는지. 못 받으면 A-5 를 어떻게 발표할지.
4. **합성 통화(페르소나 대본)** — 시연·파이프라인 점검용으로 한정할지, 골든셋 표본 0건(P1·P2·P3·P5)을 채우는 데 써도 되는지.
5. **6주차 판정** — `w2-baseline-gate` 를 지금 켜면 F-2·A-5 는 측정 불가로 남는다. 「측정 불가」를 통과와 갈라 보고하는 방식이 평가에서 어떻게 읽히는지.
6. (⑤ 이어서) 베테랑 기준 「근속 3년」의 근거를 어디서 가져오면 되는지 · 폴백 유지가 맞는지.
7. **팀 4인 → 잔여 작업 1인 마무리**로 바뀐 상황에서 범위를 어디까지 줄여야 하는지 — G-2/H·I 는 이미 「여유 시」다.

---

## 10. 브랜치 상태 (09-17 아침, 이 머신)

| 브랜치 | main 대비 | 내용 |
|---|---|---|
| `origin/main` `6e755a8` | — | PR #96(frontend) 까지. `newTag` server `0.1.13` · call-mediator `0.1.5` · es `9.5.1` |
| `PM` `c0b828b` | +1 | 런북 18-4(Vercel 대조표) · 09-15-21 로그 |
| `origin/ai` `4c52035` | +2 | 합성 통화 대본·재생기 · **call-mediator `0.1.6`** · 09-16 로그 2건 · `w5-persona-sim-scripts` |
| `origin/frontend` `6e61764` | +1 | 09-16 로그 · STATE `apps/` 줄 |
| `origin/server` | 0 | main 과 같다 |

셋 다 PR 을 내면 된다. `ai` 는 call-mediator 태그를 먼저 집었으므로 다른 갈래가 `0.1.6` 을 쓰지 않는다.

---

## 11. 데이터 흐름 — 어디로 들어와서 어디로 나가는가 (코드 실물 기준, 09-17 추가)

> 근거: `services/call-mediator/src/adapters/hub_http.ts`(콜 미디에이터→서버 호출 5개) · `app/call_registry.ts`(발화 처리 순서) ·
> `server/apps/*/adapter/inbound/api/v1/*_router.py`(라우터 34개) · `outbound/postgres/*_repository.py`(INSERT 대상) ·
> `apps/call/src/lib/api/coreClient.ts` · `apps/admin/src/lib/api/hubClient.ts` · `db/schema.sql`(29 테이블).

### 11-1. 들어오는 문

| 문 | 무엇 | 누가 |
|---|---|---|
| `WS /call-mediator/ingest` | 오디오 PCM16, 화자별 채널 (`speaker=auto` 는 모노 화자 분리) | 오디오 생산자 — `scripts/stream_wav.ts`. 전화 사업자는 없다 |
| `GET /call-mediator/dev` · `WS /call-mediator/dev/text` | 브라우저 음성 인식이 글자로 바꾼 발화 | 개발자 폰·PC · 합성 대본 재생기(`origin/ai`) |
| 상담원 화면 REST | 수동 검색어 · 블랙리스트 요청 · 통화 종료·요약 확정·재수정 · 카드 채택 | `apps/call` |
| 관리자 화면 REST | 승인·해제·연장 · 근속 기준 · 상담원 토큰 발급 · 보존 정리 · 갭 해제 | `apps/admin`(구글 로그인) |
| `POST /hub/uploads/ticket` | 테스트 음성 → S3 presign | 팀원 브라우저 페이지 |
| 오프라인 스크립트 | 지식베이스 98조항 · 골든셋 156건 · AI Hub 원본 음성 · 합성 대본 | 사람이 돌린다 (11-5) |

### 11-2. 실시간 한 발화의 흐름

```
오디오 ─WS /ingest─▶ 콜 미디에이터 ─▶ Google STT (interim / final)
  첫 채널 열릴 때        POST /hub/calls                 → call (+customer — 발신 번호는 HMAC 식별자로만)
  final 발화마다         POST /hub/transcripts   원문 → C-5 마스킹 → transcript_segment · masking_event
                             ▲ 원문이 존재하는 유일한 구간(SEC-1). 응답부터는 마스킹본만
                         ─WS /ws─▶ {type:"transcript"}                          → 상담원 자막
  고객 발화면            POST /hub/call-guard-checks    → call_guard_flag         ─WS─▶ {call_guard} → 폭언·위기 배너
  발화마다               POST /hub/required-docs-checks → closure · closure_item  ─WS─▶ {closure}    → 필요서류 체크리스트
  트리거 발동 시         ─WS─▶ {recommendation_pending}                          → 「검색 중」
                         POST /hub/recommendations  트리거 → ES(BM25) → recommendation · recommendation_card
                         ─WS─▶ {recommendation}                                  → 필요서류 카드
통화 종료(화면이 부름)   POST /hub/calls/{id}/close      → 규칙 발췌 초안 call.summary_text · follow_up_action(draft)
                         POST …/summary-confirmation     → 확정(상담원 토큰) · summary_confirmed_at
                         POST …/summary-revision         → call_summary_revision(이력) · 후속조치 superseded
```

- 콜 미디에이터 → 서버 호출은 **다섯**이 전부다: `calls` · `transcripts` · `recommendations` · `call-guard-checks` · `required-docs-checks`.
- 콜 미디에이터 → 대시보드 WS 메시지는 **여섯**이 전부다: `transcript` · `recommendation_pending` · `recommendation` · `call_guard` · `closure` · `end`.
- 값은 전부 문자열(§7.3, `StrField`) — 화면 파서가 그 전제다.

### 11-3. 화면이 직접 부르는 REST (콜 미디에이터를 거치지 않음)

- **상담원** `apps/call`: `GET /hub/calls`(목록·`?customer_id=` 재상담 이력) · `GET /hub/calls/{id}/transcript` · `GET /hub/calls/{id}/record`(요약·카드·판정 재생) · `POST /hub/search` · `POST /hub/cards/{id}/feedback` · `POST /hub/blacklist-requests`(상담원 토큰) · `close` / `summary-confirmation` / `summary-revision`.
- **관리자** `apps/admin`: `GET/POST /hub/blacklist-requests(/decision)` · `GET /hub/blacklist-entries` + `/release` · `/expiry` · `/expiry-changes` · `POST /hub/blacklist-retention/purge` · `GET /hub/call-guard-flags` · `GET/PATCH /hub/knowledge-gaps` · `GET/PUT /hub/routing-settings` · `GET /hub/calls` · `/admin/agent-tokens`(발급·목록·폐기) · `/admin/auth/*`.

### 11-4. 어디에 남는가

| 저장소 | 무엇 |
|---|---|
| RDS `callguard-pg` 29 테이블 | 통화·고객 `call` `customer` `agent` / 전사 `transcript_segment` `masking_event` / 추천 `recommendation` `recommendation_card` `card_feedback` / F-2 `closure` `closure_item` / 통화 후 `follow_up_action` `call_summary_revision` / 탐지 `call_guard_flag` `voice_outlier` `compliance_flag` / J `blacklist_request` `blacklist_entry` `blacklist_entry_expiry_change` `routing_log` / 공백 `knowledge_gap` / 평가 `eval_run` `eval_result` / 인증·설정 `admin_account` `admin_refresh_token` `agent_token` `app_setting` / 참조 `document` `compliance_rule` `resource_center` |
| Elasticsearch `callguard-kb-single` | 지식베이스 98조항, nori BM25 (**운영엔 벡터 없음**) |
| S3 `assist-apne2/uploads/` | 테스트 음성 (`decisions/110`) |
| Redis 파드 | 관리자 access 세션 5분, 휘발 |
| 콜 미디에이터 hostPath 장부 | STT 사용 초 (COST-1 2차 캡) |
| **저장하지 않는 것** | 마스킹 전 원문(SEC-1) · 오디오 · 발신 번호 평문 · `distress_count`(`decisions/205`) |

### 11-5. 오프라인 흐름 (사람이 돌린다)

- `knowledge-base/dasan/` → `scripts/index_knowledge_base.py --to-es --recreate` → ES 인덱스 (운영은 파드 안에서, 런북 15-1) · `scripts/seed_documents.py` → RDS `document`(근거 조항 FK, 런북 17-3).
- `golden-set/v1-150.json` → `scripts/run_eval.py --runs 3 --record` → `eval_run`·`eval_result` — **수치의 유일한 정식 출처**(§5).
- AI Hub 원본 `data/raw/`(커밋 금지) → `scripts/transcribe_batch.py` → `data/processed/` · 오류 주입기 `measure_error_tolerance.py` → 곡선.
- 합성 대본 `scripts/persona_sim/dasan-v0/` → `services/call-mediator/scripts/replay_persona_call.ts` → `/dev/text?producer=script`(`origin/ai`, 미머지).
- 모델 가중치: 로컬 `PII_NER_MODEL_DIR`·`RETRIEVAL_*_MODEL_DIR` 로만 켜진다 — 운영 이미지에 없다.

### 11-6. 들어오는데 나갈 곳이 없거나, 나가야 하는데 들어오는 곳이 없는 것

| 데이터 | 상태 |
|---|---|
| C-1~C-4 위반 (`POST /hub/compliance-checks`) | 서버 엔드포인트만 있다. **콜 미디에이터도 화면도 부르지 않는다** → 경고가 화면에 못 나간다(`w6-compliance-alert-ui`) |
| J-5 배정 판정 (`POST /hub/routing-decisions`) | **부르는 곳이 없다**(교환기 없음, 콜 미디에이터 미호출) → `routing_log` 빈 채. 인증도 없다 |
| D-5 통화 온도 (`voice_outlier`) | 저장 포트만 있고 **오디오 특징값을 서버로 보내는 입구가 없다**(서버는 텍스트만 받는다) |
| F-2 게이트 원형 (`POST /hub/closure-checks`) | 콜 미디에이터는 `required-docs-checks` 만 부른다 → 호출부 없음 |
| A-5 번역·TTS · 감정 | 입구·출구 둘 다 없다. 상담기록 재생에서 늘 빈 칸 |
| D-4 「못 찾았다」 신고 (`POST /hub/knowledge-gaps`) | 입력 API 는 있으나 **상담원 화면이 부르지 않는다** — 관리자 조회·해제만 붙어 있다 |
| NER·임베딩·리랭커·생성 | 코드 경로는 있으나 **운영 이미지에 모델이 없어** 규칙·BM25·스니펫으로 내려간다(§7-3 ①) |
| 카드 피드백 | 09-16 화면 연결됨 — `card_id` 가 있는(저장된) 카드만 |

---

## 12. AI 가 하는 일 · 모델 훈련 방침 (09-17 추가)

> 근거: `decisions/010`(모델 구성 확정) · `206`(임베딩+리랭커, RRF 비채택) · `207`(kanana) · `ai/CLAUDE.md` §0·§2 ·
> `scripts/download_models.py` · `server/core/config.py`(모델 키 5종) · `_logs/2026-09-14-02-ryujun`(학습 방식) · `origin/ai` 미결 항목(09-16 류준 메모).

### 12-1. 대원칙 — 판정은 규칙, AI 는 찾기·읽기·설명만

절대 원칙 1·9. 마스킹 대상·종결 요건·위반 여부를 생성 모델에 맡기지 않고, 채점에 LLM 을 쓰지 않는다. AI 가 들어가는 자리는 다섯뿐이다.

| 자리 | 하는 일 | 모델 | 학습 | 상태 |
|---|---|---|---|---|
| A-1 STT | 음성 → 글자 | Google Cloud STT | 외부 API, 없음 | 운영 배포 |
| B-2 검색 | 발화 → 조항 찾기 | `KoE5` 임베딩 + `bge-reranker-v2-m3` (BM25 폴백) | 사전학습 그대로 | 로컬 0.979 / 운영 BM25 |
| B-4 생성 | 조항에서 서류 목록만 뽑아 카드 문구 | `kanana-1.5-2.1b`(Ollama) + 규칙 필터 | 사전학습 그대로 | 로컬만 |
| C-5 NER | 인명(P6)·주소(P7) 탐지, 규칙 P1~P5 위에 두 겹 | `koelectra-base-v3-naver-ner` | 사전학습 그대로 | 로컬 누락 0 / 운영 규칙만 |
| D-1·D-2 통화 후 | 요약 초안·유형 제안 | 초안은 규칙 발췌(LLM 아님) · 유형은 `postcall_summary` 0.872 | — | 운영 유형 null |

규칙이 하는 것: 트리거(B-1) · F-2 판정 · C-1~C-4 규칙 v1 · C-6 사전 · D-5 로버스트 z · P1~P5 마스킹 · 모든 채점.
명세의 C-1~C-4 «분류기»는 **학습 데이터가 없어 규칙 v1 로 대체**됐다.

### 12-2. 훈련 방침 — «훈련»이 아니라 «측정해서 고른다»

**남은 40일에 파인튜닝을 하지 않는 쪽으로 결정 기록을 쓴다.** 근거:

- 학습이 필요한 자리는 컴플라이언스 분류기 하나인데 **라벨이 없다** — 골든셋 C 라벨 양성 14·음성 6 은 채점용(학습에 쓰면 평가가 무너진다), AI Hub 상담원 발화 9,881건은 라벨 없음(`w5-classifier-ner-benchmark`).
- 나머지(검색·NER·생성)는 사전학습 모델 + 규칙으로 목표를 넘었다. 남은 문제는 학습이 아니라 **운영 탑재**(§7-3 ①).
- 학습을 시도한 유일한 사례 B-0 이 두 번 다 규칙 v1 을 못 넘었고(AI Hub 0.815 / 골든셋 0.786, 08-27) B-0 자체가 폐기됐다. 학습 코드도 그때 지워졌다(`ai/CLAUDE.md` §2).
- 결정이 두 갈래로 걸려 있다 — 09-14 「정성윤 개인 PC 학습·파일만 업로드」 ↔ 09-16 류준 메모 「학습 안 함·S3 는 측정용」(확정 아님). **닫으면** `w5-classifier-ner-benchmark`·A-5·D-5 의 「학습 후 진행」 메모를 「측정 불가 — 학습 안 함」으로 정리한다.

모델 작업의 본보기는 `206`·`207` 이다 — 같은 골든셋·같은 커밋에서 후보를 나란히 재고, 진 쪽 수치도 남기고, 결정 기록을 쓴다.

### 12-3. 그래도 학습한다면 지킬 것

1. 골든셋은 학습에 넣지 않는다 — 학습·검증·채점 세 벌을 가른다.
2. 라벨은 사람이 검수한 것이어야 한다. 규칙 v1 출력을 라벨로 쓰면 규칙을 복제한다.
3. 오류율 0%·10% 양쪽에서 잰다. 추론 p95 ≤1,000ms 안.
4. 개인 PC 에서 돌려도 데이터 버전·시드·명령·모델 버전을 저장소에 기록한다. `eval_run` 에 모델 버전 칸을 먼저 만든다.
5. AI Hub 원본이 모델 파일에 섞이지 않게 하고, 가중치는 비공개 S3 에 둔다(`/mnt/scratch` 금지).
6. 진 쪽 수치도 남기고 `decisions/010` 을 고치는 새 결정 기록(`2xx`)을 쓴다.

**멘토에게 한 문장**: 우리 AI 는 찾고 읽고 설명하는 데만 쓰고 판정과 채점은 규칙이 한다. 모델은 훈련하지 않고 골든셋으로 재서 고른다. 유일하게 훈련이 필요한 컴플라이언스 분류기는 라벨이 없어 규칙으로 갔고, 그 한계를 측정값으로 남겼다.

---

## 13. 아티팩트 3종과 대조해 더한 것 (09-17)

> 대조한 것: 「CallGuard 잔여 작업 대장」(09-16, 88항목) · 「미구현 기능 해결표」(09-16, 27항목) · 「장민석 작업 지시서」(09-16, 20항목).
> 아래는 그 셋에는 있는데 이 브리핑 §1~§12 에 없던 것이다. 주장은 09-17 코드로 다시 확인했다(확인 결과를 「확인」 열에 적었다).

### 13-1. 브리핑을 고친 것

- **`verdict blocked→incomplete` 는 이미 반영돼 있다** — `server/apps/closure_gate/domain/services/gate.py:54` 가 `"incomplete" if missing else "complete"`. §6-1 의 `w8-f2-wrapup` 줄을 고쳤다. 낡은 것은 티켓 본문·`CLAUDE.md`·`rfp-harness.md` 의 「코드 미반영」 서술이다 → `w8-final-docs`.
- **통화 후 초안 읽기 경로** — 미결 항목은 「없다」고 적혀 있으나 `GET /hub/calls/{id}/record` 가 `summary_text` 를 준다(지시서 #3). 초안도 돌려주는지 테스트로 확인하면 닫힌다.

### 13-2. 기획서에 있는데 티켓도 코드도 없는 것 (해결표 §1·§6)

| # | 무엇 | 확인 | 어떻게 닫나 |
|---|---|---|---|
| 1 | **matplotlib 시각화** — 3.1절 «필수» 도구, 10.2절·5주차 로드맵의 「오류율별 성능 곡선 · 레이턴시 분포 · 오류 축 둘(STT 품질 × 숙련도)을 한 그림에」 | 저장소에 matplotlib 호출 **0건**, PNG 는 ERD 뿐 | `scripts/plot_curves.py` — 하네스 JSON 만 입력. 오류율 0~20% × Recall@5·C-5 재현율 한 그림 → `jekyll/assets/` + 캡션에 측정일·커밋·표본 수. 숙련도 축은 A-5 데이터 뒤 |
| 2 | **D-6 통화 종료 즉시 핵심 제시** — rev.5 신설, 7주차 | `# Requirement: D-6` **0건**. 그런데 `POST /hub/calls/{id}/close` 가 즉시 규칙 발췌 초안을 준다 | 결정 기록 「close 즉시 초안이 D-6」 + 주석. **close 를 누가 부르나**(프론트 버튼 / 콜 미디에이터 채널 닫힘 자동) — §11-6 과 같은 자리 |
| 3 | **B-4 생성 스트리밍** — 4.3절 「첫 토큰 500ms, 카드 점진 표시」 | `ollama_chat.py:55` `stream: False` 고정 | 생성을 운영에 켜기로 할 때만. 안 켜면 「미착수 · 예산표 생성 행 미측정」 명시 |
| 4 | **프론트 자동화 테스트(QUA-1)** — 요구 표는 `apps/call/test` Jest 명시 | `apps/call`·`apps/admin` 테스트 파일 0 · `package.json` test 없음 · CI 에 `apps` 잡 없음 | vitest 최소 범위 — WS 파서 4종이 §7.3 문자열 계약을 읽는지 + `isAllowedCallMediatorUrl`. `test.yml` 에 `apps` 잡 + 룰셋 + `ruleset-main.json` |
| 5 | **2.1절 「고객 원문 병기 + 숙련도」 칸** | mock 시나리오에만 있고 실서버 계약에 필드 없음 | 결정 기록 `4xx` — 라이브 모드에서 두 칸은 빈칸(숙련도 라벨은 데이터셋 것이지 고객 판정이 아니다). 마스킹 원문 토글 폐기도 같은 기록에 |
| 6 | **8주차 로드맵 산출물** — 아키텍처 다이어그램 · **실패 사례 분석** · **데이터 한계(5.5절)** · 성능 리포트 | 티켓 어디에도 명시 없음 | `w8-presentation`·`w8-final-docs` 본문에 산출물 넷을 적는다 |
| 7 | **J KPI 집계 API** — `routing_log` 의 목적이 「떨어뜨린 건수를 센다」인데 세는 곳 없음 | `GET /hub/routing-stats` 없음 | `{total, fell_back, blacklisted}` 문자열, `require_admin`, **상담원 단위로 쪼개지 않는다**(부록 A-1). J-5 호출부(§11-6) 없이는 값이 0 |

### 13-3. 서버·운영 정직성 — 지시서에서 가져온 것

| # | 무엇 | 확인 | 어떻게 닫나 |
|---|---|---|---|
| 8 | **`/health` 에 배포 이미지 태그** | `server/main.py:376` `version="0.1.0"` 고정. 프로브 삭제 뒤 밖에서 태그를 알 방법 없음 | Dockerfile `ARG APP_VERSION` → `release.yml` `build-args` → `config.py` → `/health` `version`. 없으면 `unknown`(지어내지 않는다). 런북 가드 대상 |
| 9 | **`/health` 가 DB 에 `SELECT 1`** — 지금 `postgres_configured` 는 환경변수 «있음»만 본다 | 런북 19장·09-14 사건 둘 다 「`/health` ok 인데 DB 는 안 붙음」 | `{"configured","reachable"}` 로 넓힌다. 실패해도 `status: ok`(k8s probe 가 재시작하지 않게). ES 도 같은 모양 |
| 10 | **`display_hint` 채우는 경로 없음**(늘 null) — 관리자 블랙리스트 목록이 HMAC 만 보여 준다 | `blacklist_request_create_schema.py:33` 「채우는 경로 없다」 | 발신 번호 → HMAC 만드는 자리에서 뒤 4자리 `****1234` 를 같이 저장. 원문은 남기지 않는다 |
| 11 | **상담원 인증 구멍** — `agent.role="admin"` 을 호출자가 본문에 실어 주장하면 승인 통과 | `open-items:220`. 재료(`require_agent`·`require_admin`)는 09-15 에 생겼으나 승인·해제·연장에 붙었는지 미확인, **토큰 만료 없음** | 승인·해제·연장에 `require_admin` 확인 → 라우터 34개를 «콜 미디에이터/상담원/관리자/무인증» 표로 → 만료 컬럼 + 기본값(예시값) |
| 12 | **보존 기간 셋 미정** — 추천 저장(308) · 만료 변경 이력 사유(309) · 반려 요청 사유(205) | 전례는 블랙리스트 문장 180일(312)뿐, 그 값도 근거 없음 | 결정 기록 하나로 묶고 같은 purge 엔드포인트가 세 테이블을 비운다. 추천은 본문만 비우고 건수는 남긴다 |
| 13 | **F-2 게이트 호출 시점** — 요청 시만인지, close 에서 최종 판정을 한 번 더인지 | `docs/architecture.md §6` 미결. 코드는 둘 다 반쯤(`closure_router` + `required-docs-checks`) | 권고 「close 에서 최종 `missing` 을 초안에 싣는다」 — #2 D-6 와 같은 자리 |
| 14 | **계약 테스트가 필드명·타입을 단언하는가** — `score` 어긋남이 3주 간 원인 | 전사·종결 라우터 테스트 미점검. 알려진 어긋남 둘(`ClosureType` 「사고·보상」·`segment_id` 예시) | 세 라우터 테스트에 키 집합 + 전부 문자열 단언 1건씩 |
| 15 | **관리자 토큰 TTL 운영값** — access 5분·refresh 10분은 테스트값 | `config.py:138` 기본값 · 발급기 머리 「테스트 전용」 | 결정 기록에 관례값(예시값 표기) → `server-env` 에만 넣는다 |
| 16 | **스키마 선행 확인 게이트** — §7-3 ④ 와 같은 항목. 권고 ① PR 본문 체크박스 | `check_release_tags.py` 한 벌 | `db/migrations/` 새 파일 + `newTag` 상승이면 체크박스 요구. 결정 기록은 `1xx` |
| 17 | **운영 `/admin/auth/test` 404 확인 · 관리자 가드 401 이 `0.1.13` 에 포함됐는지** | 아직 아무도 안 봄(§7-3 ⑧ 과 묶음) | `curl -i …/hub/routing-settings` 401 기대. 500 이면 다음 태그 |
| 18 | **`.env.example` 키 5개** — `PII_NER_MODEL_DIR`·`RETRIEVAL_EMBED_MODEL_DIR`·`RETRIEVAL_RERANK_MODEL_DIR`·`OLLAMA_URL`·`GENERATION_MODEL` | `config.py` 는 읽는데 예시 파일에 없음(보호 훅이 막아 사람이 넣는다) | 값 없이 키 이름만 |

### 13-4. 문서가 실물과 어긋난 곳 — `w8-final-docs` 에 넣을 목록 (대장 G 절)

- **런북이 원안 그대로인 곳**: g4dn.xlarge · Ubuntu DLAMI · `assist-gpu-01` · `assist-key` · EIP · 네임스페이스 `assist` — 실물은 Amazon Linux 2023 · EIP 없음 · `callguard`. 0장 자원표 · 7-2 · 20 · 21-2 · VRAM 표 전면 대조. 5-3 데이터셋 프리픽스 ↔ `data/README.md` 통일.
- **낡은 서술**: `.claude/rules/call.md:86`(콜 미디에이터 0줄) · `README.md:16`(콜 미디에이터·코어 없음) · `infra/CLAUDE.md §3` 「아직 없는 것」(Dockerfile 있음·Caddy 폐기) · `docs/architecture.md §6` 미결 4건(도메인 라우팅 폐기 반영) · `jekyll/docs/03` 표 「nori+dense_vector+RRF」(206 비채택 반영) · `CLAUDE.md` 서류 문의 174건·69종 → 146건·64종 · `docs/06` 지표표 빈 값·F-3 잔존 · `jekyll/sprints/` 01 뿐.
- **STATE.md 낡은 줄**: 「현재 3주차」 → 5주차 · 이미지 태그 `0.1.10/0.1.4` → main `0.1.13/0.1.5` · 「A(STT) 코드 0줄」 · 「운영 `document` 비어 있음」(09-15 채움).
- **결정 기록 미작성**: 파이프라인(SSM·OIDC·렌더) `1xx` · 런북 부록 B 9건 · D-6 · 보존 기간 · 상담원 토큰 범위 · 블랙컨슈머 카드 `4xx` · 「감정분석」 대체 용어 `2xx`.
- **작은 것**: `// Requirement: J-3` 주석 0건(`RequestsTab.tsx`·`EntriesTab.tsx`) · `ERD.png` 미갱신(29 테이블) · `fetchCallList` 낡은 주석 · nori 복합명사 사용자 사전 · `check_session_end.py` 에 STATE 검사 붙일지.

### 13-5. 순서가 있는 것 (해결표 「앞이 없으면 뒤가 헛돈다」)

1. AI Hub 신청 → A-5 측정 → 숙련도 축 그림 → 2.1 원문·숙련도 칸
2. 모델 운영 반영 → C-5 절대 규칙 운영 회복 → E2E 지연 실측 → 레이턴시 그림 → 6주차 기준선 판정
3. 생성을 켤지 → 켜면 스트리밍 · 안 켜면 예산표 생성 행 「미측정」
4. F-2·D 골든셋 케이스 → 하네스 숫자 → `w7-f2-checkpoint` → `w8-f2-wrapup`
5. 컴플라이언스 WS 메시지 계약 → 콜 미디에이터 호출 → 경고 화면 → 파서 테스트
6. J-5 호출 → `routing_log` 행 → KPI API → 현황판
7. E-4 게이트(`w2-baseline-gate`)는 4·2 뒤에 켜야 「미구현 때문에 계속 빨강」이 안 된다

---

## 14. 최종 점검 — 미결 항목 98건 · 로그 「남은 것」 · 결정 기록 「남는 것」 전수 대조 (09-17)

> 대조한 것: `jekyll/open-items.markdown` 열린 체크박스 **98건**(PM) + `origin/ai` 추가 1건 · 09-15·16 로그 45건의 「남은 것」 전부 · 결정 기록 `107~114`·`206·207`·`303~313` 의 「남는 것」 절.
> §1~§13 에 없던 것만 아래에 적었다. 그 밖의 항목은 전부 이미 §6·§7·§11·§13 에 있다.

### 14-1. 브리핑에 없던 것 12건

| # | 무엇 | 출처 | 어떻게 닫나 |
|---|---|---|---|
| 1 | **LangChain·LangGraph 오케스트레이션** — `ai/CLAUDE.md` §0 과 요구 표가 `ai/` 의 일로 적어 뒀는데, 코드에 import 0건(주석·requirements 주석뿐) | `open-items:136` | 안 쓰기로 결정 기록 `2xx` 로 닫는다(허브-스포크가 그 자리를 대신한다). 문서 두 곳에서 서술 삭제 |
| 2 | **A-5 통번역 이벤트 계약**(원문+번역본+언어코드) — §7.3 에 없음 | `open-items:156` | ⓐ 미착수 결정 기록(§13-2 #5)에 「계약도 미정」을 함께 적는다 |
| 3 | **재상담 고객 이력 요약(메모)** — 프론트 mock 의 「메모」칸에 대응 컬럼이 없다 | `open-items:323` | 폐기 또는 `summary_text` 미리보기로 대체 — 조서희 09-16 「목록에 요약 미리보기」 결정과 같은 자리 |
| 4 | **초안과 확정본의 차이가 남지 않는다** — 확정이 초안을 덮어쓴다. 요약 품질 측정 재료가 사라진다 | `decisions/310` 남는 것 | `call_summary_revision` 전례대로 초안을 보존할지 결정. 안 하면 「D-1 품질은 재지 않는다」로 명시 |
| 5 | **LLM 요약이 들어오면 규칙 발췌 어댑터를 폴백으로 둘지** | `decisions/306` · `open-items:592` | 생성 운영 여부(§7-4)와 함께 결정. kanana 를 안 켜면 규칙 발췌가 최종 |
| 6 | **추천 저장 INSERT 가 실시간 경로에 더하는 지연 미측정** | `decisions/308` | `w7-latency-budget` 구간에 「추천 저장」을 넣는다 |
| 7 | **STT 비용 전제 정정** — 배치 스크립트가 Dynamic Batch 가격을 못 받는다(V1 동기 API) | `open-items:174` | `w2-stt-batch` 검증 때 실제 청구 단가를 적는다. 전량 전사 판단(§13-4)과 같은 자리 |
| 8 | **다산 필요서류 실측 데이터** — `POLICY.md`·`MANUAL.md` 의 서비스별 구비서류 목록이 팀 작성분이라 실제 목록과 대조된 적 없음 | `open-items:163` | 출처(120 홈페이지·정부24) 확인 후 갱신. 절대 원칙 6(원문 전재 금지). 여권 조항 추가(§13-2)와 한 번에 |
| 9 | **상담기록 해결률 통계 패널** — 팀 결정 없이 프론트 개인 판단으로 추가, 재문의율 검증 없음 | `open-items:161·162` | 유지·제거 결정. 유지하면 「데모 건수」 표기 |
| 10 | **백엔드 생산성을 막는 규칙 4건 완화** — 08-27 팀 논의 항목 | `open-items:123` | 잠금 해제(302)·협의 철폐(023)로 대부분 풀렸다. 남은 것이 있는지 보고 닫는다 |
| 11 | **중복 티켓** — `w2-dashboard-scaffold`(todo) ↔ `w1-dashboard-scaffold-seohee`(done). 세션 종료 검사가 매번 경고 | `open-items:175` | 앞 티켓 삭제 |
| 12 | **4주차 로드맵 vs 실제** — 로드맵(`docs/08`)에 없던 일을 4주차에 했고, 로드맵 항목은 티켓 없이 갔다 | `open-items:510` | `docs/08` 4주차 행을 실제에 맞게 고칠지 결정. 발표의 「계획 대 실제」 재료 |

### 14-2. 미결 항목에서 이미 끝났는데 열린 채인 것 — 닫는 작업 자체가 남은 일이다

`open-items.markdown` 열린 체크박스 98건 중 아래는 **끝났거나 폐기됐다.** 지우지 않고 `[x]` + 「닫힘 — 근거」 한 줄로 닫는다(절대 원칙 8). `w8-final-docs` 범위.

- **B-0 폐기로 무의미**: 143(검색 v1+분류기) · 144(dasan 보강) · 145·149(B-0 표본) · 146(골든셋 문체 차이 — `source` 필드로 갈라 뒀으니 측정은 가능, 판단만 남음) · 137(`RetrievalPort` 도메인) · 127(도메인별 인덱스) · 138(nori 개선 폭 — 206 이 BM25 대조군을 쟀다).
- **이미 구현·결정됨**: 120(청킹 비교 → `w4-chunking-compare` done) · 122(계약 어긋남 → 09-10·09-15 문자열 정본) · 124(하네스 C-5·F-2 배선 → `w2-eval-wiring-c5-f2`) · 125(NER → `ai/apps/pii_ner`) · 132(수동 검색·통화 후 메시지 → §7.3 허브 HTTP 표면) · 134(`generation`·`compliance` 위치 → 302) · 155(통화 목록 API → `w4-call-list-api`) · 157(C-6 계약 → 콜 미디에이터 `call_guard`) · 184(콜 미디에이터 EC2 → 09-11 배포) · 185(운영 배포 CI → `release.yml`) · 194(`score` 방어 코드 → 서버가 고쳤다) · 201(카드 피드백 500 → 308) · 204(ngrok 인증 → 터널 닫음) · 214(C-6 갈래 → 09-15 프론트 4종) · 215(J 계약·어댑터 → `w4-blacklist-api`) · 285(조서희 계약 전달 → 09-15·16 처리) · 325(태그 안 올린 머지 → 111 게이트) · 590(PR #86 순서 → 머지됨) · 597(관리자 가드 500 → 코드 수정, 운영 확인만 §13-3 #17) · 177(DNS 공지 → 런북 18장).
- **`origin/main` 에서 이미 닫힘(PM 미머지)**: 565(갭 탭 재설계) · 588(`contract.ts` — 오판으로 정정).
- **보류로 닫을 것**: 135(Neo4j — 저장소에 언급 0건, 도입 안 함) · 153(스케줄러 — 지킬 칸반 유지) · 160(G-2 계약 — `w8-extension-pick` 뒤).

### 14-3. 점검 결과 요약

- 티켓 21건 + §6-2·§7-3·§11-6·§13·§14-1 항목을 합치면 **남은 일은 약 90건**이고, 그중 **결정만 하면 되는 것이 30건 안팎**이다. 코드를 써야 하는 것 중 성공 조건에 직접 걸리는 것은 §7-3 🔴 넷과 `w2-baseline-gate`·`w6-core-baseline-check`·그래프(§13-2 #1)뿐이다.
- **이 브리핑 밖에 남은 것은 없다** — 09-17 기준 미결 항목·로그·결정 기록·아티팩트 3종·티켓·기획서 기능 표를 전부 대조했다. 새로 생기는 것은 앞으로의 세션 로그와 미결 항목에서 나온다.
- 이 머신에서 확인하지 못한 것 둘은 그대로다: PR #94 뒤 `0.1.13`·`0.1.5` 릴리스 결과(`gh` 없음) · 운영 EC2 등급·자동 중지 cron(AWS 자격증명 없음).
