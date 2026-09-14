---
title: "C-6·D-5 탐지 결과 저장 — 지금은 출력이 버려진다"
assignee: "류준"
role: "ai"
status: "done"
sprint: 4
priority: 8
date: 2026-09-09
requirement:
  - "C-6"
  - "D-5"
paths:
  - "server/apps/hub/adapter/outbound/postgres/call_guard_flag_repository.py"
  - "server/apps/hub/adapter/outbound/postgres/voice_outlier_repository.py"
  - "ai/apps/voice_signal/adapter/outbound/voice_outlier_recorder.py"
  - "scripts/seed_documents.py"
---

## 무엇을

`call_guard_flag`·`voice_outlier` 테이블에 실제로 쓰는 경로를 만든다.
**스키마는 2026-09-09 에 만들었다**(`_project/decisions/205` ②③) — 배선이 없다.

## 왜 — 오늘 구현한 기능의 출력이 사라지고 있다

스키마 QA 가 짚은 것: C-6 탐지 결과(`CallGuardFlag`)와 D-5 이상 구간
(`SpeakerTemperature`)을 담을 테이블이 **아예 없었다.** 그래서 —

- **관리자가 「폭언 3건」을 검증할 수 없다.** J-6 근거는 프론트가 세션 메모리에서
  센 값이고, 「어느 발화가 걸렸는지」를 볼 방법이 없다 —
  `decisions/204` 의 *"통화를 다시 듣지 않고 판단"* 전제가 깨진다.
- **D-5 는 재계산이 불가능하다.** 우리는 **오디오를 보관하지 않는다**(절대 원칙 7).
  통화가 끝나면 톤 이상 구간은 영영 사라진다.

`compliance_flag` 로 대체할 수 없다 — `rule_code` 가 `compliance_rule`(C-1~C-4)에
FK 로 묶여 있고, 무엇보다 **화자가 반대라** 섞으면 D-4 재학습 데이터가 오염된다.

## 완료 조건

- [x] C-6 결과를 `call_guard_flag` 에 남기는 포트·어댑터 — `CallGuardRecordPort` · `PostgresCallGuardFlagRepository`.
      **전사 수신 경로에 배선했다** — 고객 확정 발화가 마스킹·저장된 뒤 콜 가드가 돌고 발화 단위로 갈아끼운다
- [x] `phrase` 가 **마스킹된 자막에서 잘라낸 것**임을 테스트로 고정(MANUAL-5.5) — 인터랙터 스파이 테스트 +
      합성 루트에서 실제 마스킹·실제 콜 가드를 함께 돌리는 테스트
- [x] D-5 결과를 `voice_outlier` 에 남기는 경로 — `VoiceOutlierRecordPort` · 리포지토리 · `record_speaker_temperature`.
      ⚠ **부르는 실시간 경로는 없다** — 톤 특징값은 오디오에서 나오는데 `server/` 는 텍스트만 받는다
- [x] `robust_z` 를 저장하되 **화면에 내지 않는다** — HTTP 표면에 이름이 나타나면 실패하는 테스트
- [x] `document` 테이블 적재 — `scripts/seed_documents.py`(98조항, UPSERT). ⚠ **운영 RDS 에는 아직 안 돌렸다**
      (런북 17-3). 안 돌리면 욕설이 걸린 고객 발화의 전사 요청이 FK 위반으로 500 이다

## 설계 결정 (2026-09-14)

- **리포지토리를 `ai/` 가 아니라 `server/` 에 뒀다.** 티켓을 쓸 때 `paths` 는 `ai/…/*_repository.py` 였지만
  `ai/CLAUDE.md` §0 이 **DB 저장은 `ai/` 가 하지 않는다**고 정하고, 커넥션 팩토리·다른 리포지토리 전부가
  `server/apps/hub/adapter/outbound/postgres/` 에 있다. 담당 잠금이 풀린 것(`decisions/302`)과 무관한 아키텍처 경계다
- **콜 가드가 없으면 501 이 아니라 건너뛴다.** 전사 수신에 얹혀 돌기 때문에 501 이면 자막·마스킹까지 멈춘다.
  빠진 것은 `/health` `spokes` 의 `call_guard` 로 보인다
- **탐지기의 `strip()` 버그를 고쳤다.** 앞 공백을 잘라낸 문자열 기준으로 오프셋을 내서, 공백만큼 저장 구간이 밀릴 수 있었다

## 검증

`server` 341 · `ai` 204 · 계약 4+3종 KEPT · integration 6(로컬 `postgres:17` + 현재 `schema.sql`) ·
실제 앱 → 실제 DB 로 「전화번호 + 욕설 + 위기 신호」 발화를 넣어 `call_guard_flag` 에 `insult`(5.1)·`distress`(5.4)
두 행이 마스킹된 자막 구간으로 남는 것을 확인
