# 209 — 합성 통화(페르소나 대본)를 데모·파이프라인 점검용으로 채택하고, 소리는 Google TTS(무료 한도 안), 왕복은 E2E 검사로 본다

- 날짜: 2026-09-18
- 작성: 류준 (`2xx` 번호대)
- 상태: **제안** — 팀 합의 전. 미결 「합성 통화를 채택할지 — 결정 기록 없음」(2026-09-16) 을 닫는 기록이다
- 영향: `scripts/persona_sim/`(대본·생성기·TTS·E2E 문서) · `services/call-mediator/scripts/`(재생기 — `src/` 아님, 이미지 태그 불변) ·
  `.env.example`(`GOOGLE_TTS_API_KEY` · `GOOGLE_TTS_MAX_CHARS_PER_MONTH`) · `data/processed/`(캐시·장부·보고서, gitignore)
- 관련: 티켓 [w5-persona-sim-scripts](../../jekyll/_backlogs/w5-persona-sim-scripts.md) · [w5-persona-tts-google](../../jekyll/_backlogs/w5-persona-tts-google.md) ·
  [w5-persona-e2e](../../jekyll/_backlogs/w5-persona-e2e.md) · `109`(dev 텍스트 경로) · `304`(발신 번호 헤더) · `208`(운영 NER·임베딩 — 이 검사가 그 효과를 볼 도구가 된다)

---

## 맥락

실제 통화 음성·외국인 화자 데이터가 없어(미결 2026-08-28 「외국인 화자 한국어 음성 0건」) 파이프라인을 **한 통화로 끝까지**
돌려 볼 입력이 없었다. 09-16 에 상담원·고객 페르소나 대본 14건과 재생기(`/dev/text?producer=script`)를 만들었고,
09-17 로컬 E2E 4건에서 SEC-1 누락·컴플라이언스 미배선·필요서류 오카드 등 실제 구멍을 찾았다 — 눈으로 본 결과였다.

2026-09-18 사용자 지시: ① 페르소나·대본을 성격별로 늘리고 ② **대시보드 → 파이프라인 → DB → 대시보드** 왕복을 검사로
만들고 ③ 대본이 STT 를 대신하니 **TTS 만** 붙여 「API 키만 넣으면」 소리가 나게 하되 ④ **무료 티어 안에서만** 쓰도록 리밋을 건다.

## 선택지

| | 내용 | 판단 |
|---|---|---|
| 용도 A | 합성 통화를 **데모·파이프라인 점검 전용**으로 한정 | ✅ 채택 |
| 용도 B | 합성 수치를 발표 성능표에 사용 | ❌ STT 미경유라 상한값이고, 라벨을 우리가 썼다(자기충족) |
| 소리 1 | 이 맥 `say`(무료, 키 없음) | 유지 — 기본값 |
| 소리 2 | **Google Cloud TTS Wavenet** — REST 직접 호출, 파일 캐시, 톤은 SSML prosody | ✅ 채택 — 페르소나별 목소리·톤 연기 가능. 무료 100만 자/월, 대본 24건 ≈ 수만 자 |
| 소리 3 | Chirp3-HD | ❌ SSML prosody 미지원 → 톤(폭발·가라앉음)을 못 살린다 |
| 소리 4 | 브라우저 TTS(대시보드에서 재생) | ❌ `apps/` 수정 필요(조서희 전담) — 프론트 무수정 원칙 유지 |
| 왕복 검사 | 대본 `expected` 라벨과 `GET /hub/calls/{id}/transcript`·`/record`·DB 를 규칙으로 대조 | ✅ 채택 — 대시보드가 읽는 API 그 자체를 본다 |

## 결정 (제안)

1. **용도는 데모·파이프라인 점검**이다. 수치는 `source: synthetic` 으로 실제·작성 골든셋과 **섞지 않고**, 발표에 쓰면 「STT 미경유 상한」을 붙인다.
2. **소리는 `say`(기본) + Google TTS Wavenet(`--speak google`).** 키는 `GOOGLE_TTS_API_KEY` 환경변수로만, 로그·URL 에 남기지 않는다.
   **리밋은 COST-1 과 같은 2단** — 1차 GCP 콘솔 할당량(문자 수/월), 2차 앱 가드 `GOOGLE_TTS_MAX_CHARS_PER_MONTH`(기본 900,000,
   장부 `data/processed/tts-usage.json`, 넘으면 호출하지 않는다). 합성 결과는 캐시해 **시연 때 API 호출 0**.
3. **왕복 검사 `scripts/persona_sim/e2e_check.py`** 가 대본마다 왕복(자막 수·화자·DB 행)·SEC-1(가짜 PII 원문 부재)·라벨 재현
   (콜 가드·컴플라이언스·필요서류)·통화 후 요약을 판정한다. 실패는 원인 가설과 함께 그대로 남긴다(절대 원칙 8).
4. 대본은 **공개 저장소에 둔다** — 개인정보는 전부 실존 불가 가짜 값이고, 폭언·성적 표현은 C-6 검증에 필요한 최소(README 내용 경고).
   새 대본에는 폭언·성적 표현을 **추가하지 않는다**(수위는 SYN-005~007 로 충분).
5. 운영 시연은 콜 미디에이터 ingest 토큰·TTS 키가 갖춰진 뒤 별건으로 한다(SYN-010 한 건 동의 — 미결 그대로).

## 근거

- 대본은 프론트를 안 고치고 실제 통화와 같은 메시지를 흘린다(`109`) — 대시보드·서버·DB 가 그대로 검증 대상이 된다
- TTS 를 재생기 쪽(이 맥)에 두면 서버·콜 미디에이터·프론트 어느 것도 바뀌지 않는다 — 이미지 태그·배포 무관
- 리밋 없이 키를 넣으면 실수 한 번(루프·캐시 삭제)에 무료 한도를 넘길 수 있다 — STT 에서 이미 같은 이유로 COST-1 을 뒀다

## 이 결정으로 말할 수 없는 것 (절대 원칙 10)

- STT 정확도 · A-5 WER/CER · 트리거 지연 p95 · D-5 통화 온도의 실제 성능 — 전부 `scripts/persona_sim/README.md` 「말할 수 없는 것」 그대로
- E2E 검사의 통과는 「배선과 규칙이 대본에서 동작한다」이지 재현율·정밀도가 아니다

## 되돌리는 법

- Google TTS 를 걷으려면 `persona_replay/google_tts.ts`·`google_voices.ts`·`tts_budget.ts` 와 재생기의 `--speak google` 분기, `.env.example` 두 줄을 지운다 — `say` 경로는 독립이다
- 합성 통화 자체를 접으려면 `scripts/persona_sim/` 과 `services/call-mediator/scripts/replay_persona_call.ts`·`persona_replay/` 를 지우고 콜 미디에이터의 `producer=script`(엔진 `synthetic-script`)만 남기거나 함께 걷는다(`109` 의 dev 경로는 별개)
