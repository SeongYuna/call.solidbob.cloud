---
title: "C-6·D-5 탐지 결과 저장 — 지금은 출력이 버려진다"
assignee: "류준"
role: "ai"
status: "todo"
sprint: 4
priority: 8
date: 2026-09-09
requirement:
  - "C-6"
  - "D-5"
paths:
  - "ai/apps/call_guard/adapter/outbound/*_repository.py"
  - "ai/apps/voice_signal/adapter/outbound/*_repository.py"
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

- [ ] C-6 결과를 `call_guard_flag` 에 남기는 포트·어댑터
- [ ] `phrase` 가 **마스킹된 자막에서 잘라낸 것**임을 테스트로 고정(MANUAL-5.5)
- [ ] D-5 결과를 `voice_outlier` 에 남기는 경로
- [ ] `robust_z` 를 저장하되 **화면에 내지 않는다**(부록 A-1) — 임계값 3.5 는 재서 고른
      값이 아니라 나중에 바꿔 재판정해야 하므로 저장은 필요하다. **저장과 표시는 다르다**
- [ ] `document` 테이블에 `DASAN-MANUAL-5.1/5.2/5.4` 행이 있어야 FK 가 선다
