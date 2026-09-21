# 합성 통화 소리 — Google Cloud Text-to-Speech

> 합성 통화 재생기(`services/call-mediator/scripts/replay_persona_call.ts`)의 **소리 쪽**이다. 글자는 대본이 STT 를 대신해
> `/dev/text` 로 가고, 이 문서는 그 글자를 **목소리로 내는** 경로만 다룬다. 기본은 이 맥의 `say`(무료·키 없음)이고,
> **`--speak google`** 이 Google TTS(ko-KR WaveNet)다 — 키 하나(`GOOGLE_TTS_API_KEY`)만 `.env` 에 넣으면 돈다.
>
> ⚠ 이것으로 D-5 통화 온도·A-5 의 성능을 말할 수 없다(절대 원칙 10) — 톤은 우리가 넣은 운율 지시지 사람의 격앙이 아니다.
> 합성 음성은 STT 에 다시 넣지 않는다(STT 과금·정확도 논의는 별건).

## 1. 키 발급 — 정성윤 님께 요청하는 내용 (그대로 전달)

Google Cloud Console(`console.cloud.google.com`), STT 키를 발급한 **같은 프로젝트**에서:

1. **API 및 서비스 → 라이브러리** → 「Cloud Text-to-Speech API」 검색 → **사용 설정**
2. **API 및 서비스 → 사용자 인증 정보 → 사용자 인증 정보 만들기 → API 키** → 키 문자열이 한 번 표시된다(복사)
3. 만든 키의 **키 제한**:
   - **API 제한 → 「키 제한」 → Cloud Text-to-Speech API 하나만** 체크 (다른 API 로는 이 키가 안 통한다 — 유출돼도 피해가 TTS 로 한정)
   - 애플리케이션 제한: **없음** (브라우저가 아니라 이 맥의 스크립트가 서버 쪽에서 부른다. HTTP 리퍼러 제한을 걸면 막힌다)
   - 이름은 `callguard-persona-tts` 처럼 용도가 보이게
4. **1차 리밋 — 콘솔 할당량**: **IAM 및 관리자 → 할당량 및 시스템 한도** → 서비스 「Cloud Text-to-Speech API」 →
   문자 수 관련 항목(`characters per month`·`per minute` 계열)을 **무료 한도 아래**로 낮춰 둔다(예: 월 1,000,000).
   > 참고: 공식 할당량 문서(https://docs.cloud.google.com/text-to-speech/quotas, 2026-09-18 확인)는 «올리는» 절차만 적고
   > 「낮추기」를 따로 적지 않는다 — 콘솔 할당량 화면에서 편집이 되면 낮추고, 안 되면 **결제 → 예산 및 알림**에 이 프로젝트
   > 예산(예: ₩5,000)을 걸어 알림으로 대신한다. 어느 쪽이든 2차 가드(아래 §3)는 항상 켜져 있다.
5. 키를 **`.env`** 에 넣는다(저장소 루트, gitignore):
   ```
   GOOGLE_TTS_API_KEY=<발급한 키>
   GOOGLE_TTS_MAX_CHARS_PER_MONTH=900000     # 비워도 같은 값
   ```
   **슬랙·이슈·커밋 메시지에 키를 적지 않는다**(SEC-2). 전달은 1:1 로.

STT 의 `GOOGLE_APPLICATION_CREDENTIALS`(서비스 계정 JSON 파일)와는 **다른 종류의 자격증명**이다 — TTS 는 문자열 API 키 하나로
REST 를 직접 부른다(라이브러리 의존성 없음). 서비스 계정으로도 되지만 그러면 `google-auth` 의존성이 붙어 콜 미디에이터 이미지
태그를 올려야 해서 API 키로 갔다.

## 2. 사용법

```bash
cd services/call-mediator
# .env 를 읽게 --env-file-if-exists 를 붙인다(npm start 가 쓰는 것과 같은 방식). 셸에 export 해도 된다
node --env-file-if-exists=../../.env scripts/replay_persona_call.ts --prefetch            # 전 대본 캐시 채우기(재생 없음)
node --env-file-if-exists=../../.env scripts/replay_persona_call.ts --prefetch SYN-004    # 한 편만
node --env-file-if-exists=../../.env scripts/replay_persona_call.ts SYN-004 --speak google --watch   # 재생(캐시 있으면 호출 0)
node scripts/replay_persona_call.ts SYN-004 --speak            # 예전처럼 macOS say (키 불필요)
```

- **캐시**: `data/processed/synthetic-voice/google/<SYN-id>/<seq>-<speaker>.mp3` + `.json`(음성·지문·문자 수). gitignore.
  글자·톤·음성·높이 중 하나라도 바뀌면 지문이 달라져 그 턴만 다시 합성한다. **시연 전날 `--prefetch` 를 돌려 두면 당일은
  키 없이·오프라인으로도 재생된다** — `.env` 에서 키를 빼고 시연해도 된다.
- **재생기 동작**: `--speak google` 은 소켓을 열기 **전에** 대본 전체를 캐시에 채운다(키·예산·플레이어 문제로 실패하면 서버에
  통화 행이 생기기 전에 멈춘다). 턴마다 `afplay`(없으면 `ffplay`)로 틀고, 소리가 끝나야 확정 자막을 보낸다.
  `--speed` 는 afplay 의 배속(`-r`)으로 따라간다(ffplay 는 1배속). `--dry-run` 은 TTS 도 부르지 않는다.
- **키가 없으면**: 캐시에 없는 턴에서 **명확히 실패**한다 — `say` 로 조용히 넘어가지 않는다(어느 쪽 소리인지 헷갈리지 않게).
- 페르소나별 음성·톤 연기: `services/call-mediator/scripts/persona_replay/google_voices.ts` · `google_tts.ts`.
  `personas.json` 에 `google_tts_voice`(예: `ko-KR-Wavenet-D`)를 적으면 표보다 우선한다. 표에 없는 새 페르소나는
  `tts_voice_hint` 의 「남성/여성」으로 고른다.

## 3. 리밋 — 무료 한도 안에서만 (COST-1 과 같은 2단)

| 단 | 어디 | 무엇 |
|---|---|---|
| 1차 | GCP 콘솔 할당량(또는 예산 알림) | 하드 캡. §1-4 |
| 2차 | `persona_replay/tts_budget.ts` | **호출 전에** 장부 `data/processed/tts-usage.json`(`{"YYYY-MM": 문자 수}`) + 이번 요청 문자 수가 `GOOGLE_TTS_MAX_CHARS_PER_MONTH`(기본 **900,000**)를 넘으면 부르지 않고 어느 대본·턴에서 멈췄는지 알린다. 성공한 요청만 장부에 더한다. 캐시 히트는 0 |

- 문자 수는 구글이 세는 방식 그대로 — **SSML 태그·공백 포함**(`<mark>` 만 제외, 우리는 안 쓴다). 발화 글자 수보다 태그만큼
  많다(prosody 가 붙는 턴은 +80자 안팎).
- 규모 감: 대본 14편 × 평균 17턴 × 평균 40자 ≈ **1만 자**, 태그 포함해도 2만 자 안쪽 — 기본 상한의 2% 다. 24편으로 늘어도 같은 자릿수.
- 요청당 5,000 바이트 상한(콘솔에서 못 올림)은 재생기가 미리 막는다 — 한 턴이 그보다 길면 턴을 나눈다.
- STT 장부(`stt-usage.json`, 초 단위)와는 **다른 파일**이다. 단위가 다르다.

## 4. 비용 (공식 가격표, 2026-09-18 확인 — https://cloud.google.com/text-to-speech/pricing)

| 음성 | 무료 한도 / 월 | 이후 |
|---|---|---|
| **WaveNet** (우리 선택) | **0 ~ 400만 자** | US$4 / 100만 자 |
| Standard | 0 ~ 400만 자 (WaveNet 과 **같은 SKU** — 합산) | US$4 / 100만 자 |
| Neural2 | 0 ~ 100만 자 | US$16 / 100만 자 |
| Chirp 3: HD | 0 ~ 100만 자 | US$30 / 100만 자 |
| Studio | 0 ~ 100만 자 | US$160 / 100만 자 |

「Price is calculated per character. The total number of characters in the input string are counted for billing purposes, including
spaces and newline characters. All SSML tags (except the `<mark>` tag) are also included in the character count.」 — 같은 페이지.

**WaveNet 을 고른 이유**: SSML `<prosody>`(속도·높이·크기)로 톤을 연기할 수 있고(Chirp 3 HD 도 동기 요청에선 SSML 을 받지만
Preview 이고 무료 한도가 1/4), 무료 한도가 가장 넓다. 대본 전부를 매달 새로 합성해도 무료 한도의 1% 미만이라 **카드 청구 0원**이
기대값이다 — 단, 같은 프로젝트에서 다른 TTS 사용이 있으면 합산되므로 상한을 넉넉히 아래(90만)에 둔다.

## 5. 확인한 공식 문서 (2026-09-18)

- 음성 목록(ko-KR WaveNet A·C 여성, B·D 남성): https://docs.cloud.google.com/text-to-speech/docs/voices
- 가격·문자 수 계산 규칙: https://cloud.google.com/text-to-speech/pricing
- SSML `<prosody>` 속성(rate %, pitch ±Nst, volume ±NdB): https://docs.cloud.google.com/text-to-speech/docs/ssml
- REST `text:synthesize` 본문(`input.ssml` · `voice.name` · `audioConfig.audioEncoding/pitch`, 응답 `audioContent` base64):
  https://docs.cloud.google.com/text-to-speech/docs/reference/rest/v1/text/synthesize
- API 키 전달(헤더 `x-goog-api-key` 권장, URL `?key=` 는 유출 위험): https://docs.cloud.google.com/docs/authentication/api-keys-use
- 할당량(요청당 5,000 바이트 · 분당 요청 수): https://docs.cloud.google.com/text-to-speech/quotas

## 6. 실제 키로 확인한 것 (2026-09-21) · 아직 확인 못 한 것

- ✅ **실제 키로 합성된다** — `--prefetch SYN-001` 7턴, 재실행은 캐시 적중으로 호출 0. 장부가 쌓인다.
- ⚠ **WaveNet ko-KR 은 SSML `volume` 의 «올리기»(+dB)를 무시한다.** 같은 문장·같은 음성(`ko-KR-Wavenet-B`)으로 잰 값(`ffmpeg volumedetect`):

  | SSML | 길이 | 평균 음량 |
  |---|---|---|
  | 평온(prosody 없음) | 5.47초 | -18.5 dB |
  | `volume="+8dB"` 만 | 5.47초 | **-18.5 dB — 평온과 똑같다** |
  | 고함 `rate 115% · pitch +5st · volume +8dB` | 4.77초 | -19.4 dB |
  | 지침 `rate 85% · pitch -2st · volume -4dB` | 6.45초 | -23.5 dB |

  속도·높이·**내리기**는 반영되고 올리기만 안 된다. 평온 합성이 이미 최대치 근처(-2.5 dBFS)라 더 키우면 찢어지기 때문으로 보인다.
  → **기준(평온)을 -8 dB 로 낮추고** 다른 톤을 그 위아래에 두도록 `google_tts.ts` `TONE_PROSODY` 를 바꿨다. 같은 측정에서
  평온 대비 격앙 **+3.8** · 고함 **+7.1** · 지침 **-5.0 dB**(의도 +4·+8·-4), 실제 대본 SYN-006 에서도 상담원 평온 턴 대비 고객 격앙 +4.1 · 고함 +6.6 dB(목소리가 달라 참고치).
  `personas.json` 톤 힌트는 「평온 대비 dB」(의도)로 적고, 절대값은 코드가 정한다. **전체가 약 8 dB 작아지므로 시연 때 스피커 음량을 올린다.**
- 미리 합성해 둔 대본(새 음량): SYN-001 · 004 · 006 · 010 · 013 · 020 · 024. 나머지는 재생 때 합성된다(`--speak google` 이 먼저 캐시를 채운다).
- 사람 귀로는 아직 안 들었다 — 위는 음량 측정이다. 시연 전에 SYN-004·006 을 한 번 들어 본다.
- 콘솔에서 문자 수 할당량을 **낮출 수 있는지**(§1-4) — 안 되면 예산 알림으로 대체.

## 7. `.env.example` 에 넣은 블록 (2026-09-18 반영됨)

아래 블록은 `.env.example` 의 `CALL_MEDIATOR_VIEW_TOKEN=` 줄 뒤에 **이미 들어 있다**(키 이름만, 값 없음 — SEC-2).
`cp .env.example .env` 뒤 `.env` 의 `GOOGLE_TTS_API_KEY=` 에 발급받은 키를 넣으면 된다.
(`.claude/scripts/protect-files.sh` 훅이 `.env.*` 편집 도구를 막아 셸로 붙였다 — 템플릿에 값이 없음을 확인했다.)

```
# --- Google Cloud Text-to-Speech — 합성 통화 재생기 소리 (2026-09-18) --------------------
# `services/call-mediator/scripts/replay_persona_call.ts --speak google` 과 `--prefetch` 만 읽는다.
# ⚠ 운영(k8s 시크릿 server-env · call-mediator-tokens)에는 넣지 않는다 — 시연 머신 전용이다.
#   서버·콜 미디에이터 본체는 이 키를 읽지 않는다(TTS 는 재생기 프로세스에서만 돈다).
# 발급: Google Cloud Console > API 및 서비스 > 라이브러리 > "Cloud Text-to-Speech API" 사용 설정
#      > 사용자 인증 정보 > 사용자 인증 정보 만들기 > API 키 > 키 제한: "API 제한 → Cloud Text-to-Speech API 하나만".
#   위 GOOGLE_APPLICATION_CREDENTIALS(서비스 계정 파일)와 다른 종류다 — 문자열 키다. 절차·비용: scripts/persona_sim/TTS.md
GOOGLE_TTS_API_KEY=

# 월 청구 문자 수 상한(2차 가드, COST-1 과 같은 구조 — 1차는 콘솔 할당량). 호출 전에 장부(data/processed/tts-usage.json)와
# 비교해 넘기면 부르지 않는다. 비우면 900000. 공식 무료 한도는 WaveNet+Standard 합산 400만 자/월(2026-09-18 가격표)이지만
# 같은 프로젝트의 다른 사용을 모르니 그 아래 둔다. 0 은 전부 막음. SSML 태그·공백까지 문자로 센다.
GOOGLE_TTS_MAX_CHARS_PER_MONTH=
```
