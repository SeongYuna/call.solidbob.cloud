---
title: "합성 통화 음성 — Google Cloud TTS(Wavenet) 어댑터 + 무료 한도 리밋"
assignee: "류준"
role: "ai"
status: "done"
sprint: 5
priority: 58
date: 2026-09-18
requirement:
  - "D-5"
  - "COST-1"
paths:
  - "services/call-mediator/scripts/persona_replay/google_tts.ts"
  - "services/call-mediator/scripts/persona_replay/google_voices.ts"
  - "services/call-mediator/scripts/persona_replay/tts_budget.ts"
  - "scripts/persona_sim/TTS.md"
depends_on:
  - "w5-persona-sim-scripts"
---

## 무엇을

합성 통화 재생기(`replay_persona_call.ts`)의 소리를 이 맥 `say` 에서 **Google Cloud Text-to-Speech(ko-KR Wavenet)** 로도
낼 수 있게 한다. **API 키 하나만 `.env` 에 넣으면 돈다** — `GOOGLE_TTS_API_KEY`. 키 발급은 정성윤 님(GCP 콘솔)에게 요청한다.

## 왜

- 대본이 STT 를 대신하므로(글자를 직접 흘린다) 소리 쪽만 있으면 「두 AI 가 통화하는」 시연이 된다
- `say` 는 이 맥에서만 나고 음성 종류가 적다. 페르소나별 목소리·톤(SSML prosody)을 갈라 들려주려면 Wavenet 이 필요하다
- 비용은 무료 한도(Wavenet 100만 자/월) 안이어야 한다 — 2026-09-18 사용자 지시: **무료 티어 안에서만 쓰도록 리밋**

## 완료 조건

- [x] `--speak google` · `--prefetch` — REST 직접 호출(의존성 추가 없음 → 콜 미디에이터 이미지 태그 불변)
- [x] 페르소나 → Wavenet 음성 배분표 + `tts_voice_hint` 성별 폴백, 톤 → SSML prosody (`google_voices.ts`)
- [x] **리밋 2단** — 1차 GCP 콘솔 할당량, 2차 앱 가드(`GOOGLE_TTS_MAX_CHARS_PER_MONTH`, 기본 900,000, 장부 `data/processed/tts-usage.json`)
- [x] 캐시 우선(`data/processed/synthetic-voice/google/`) — 시연 때 API 호출 0
- [x] `.env.example` 키 이름 · `scripts/persona_sim/TTS.md` 발급 절차(성윤님 전달용)
- [x] 단위 테스트(SSML·배분·예산·캐시 히트 시 호출 0·키 유출 없음)
- [x] **실제 키로 1회 합성 확인** — 2026-09-21 키 받아 `--prefetch SYN-001`: 7턴 381자 합성, mp3 7개(2.2~9.8초, `afinfo`), 상담원 `ko-KR-Wavenet-B`/고객 `ko-KR-Wavenet-C`(pitch +2) 배분 확인, 장부 `tts-usage.json` 381/900,000. 재실행은 캐시 7·호출 0

## 한계 (절대 원칙 10)

TTS 톤은 연기 지시다. D-5 통화 온도의 성능 근거가 아니다(`scripts/persona_sim/README.md` 「말할 수 없는 것」).

## 2026-09-21 — 실제 키로 확인, 닫음

- 명령: `cd services/call-mediator && node --env-file-if-exists=../../.env scripts/replay_persona_call.ts --prefetch SYN-001`
- 결과: 캐시 0 → 새로 합성 7(381자) → 재실행 캐시 7·합성 0. 무료 한도 앱 가드(월 900,000자) 장부가 `2026-09: 381` 로 쌓였다. 키 값은 로그·기록 어디에도 남기지 않았다.
- **못 확인한 것**: WaveNet 이 SSML `prosody volume` 을 얼마나 반영하는지는 **귀로 들어야** 한다 — `data/processed/synthetic-voice/google/SYN-001/` 의 mp3 를 사람이 들어 보고, 안 들리면 `google_tts.ts` `TONE_PROSODY` 값을 키운다(TTS.md 「남은 것」 그대로). 콘솔 문자 할당량을 낮출 수 있는지도 정성윤 님 콘솔에서 확인.
