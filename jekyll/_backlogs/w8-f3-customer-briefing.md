---
title: "F-3 통화 수신 전 고객 브리핑 — 서버 API · 목적 추정 모델 · 재생기 벨 시간 · 대본 고객"
assignee: "류준"
role: "ai"
status: "done"
sprint: 8
priority: 4
date: 2026-10-06
requirement:
  - "F-3"
paths:
  - "server/apps/briefing/*"
  - "ai/apps/customer_briefing/*"
  - "services/call-mediator/scripts/replay_persona_call.ts"
  - "scripts/persona_sim/dasan-briefing/*"
---

> 설계·근거 `_project/decisions/220`. 화면 카드는 조서희(`w8-f3-briefing-card-ui`).
> ⚠ **10-15 부터 새 기능 금지**(`decisions/129`) — 10-14 머지가 목표.

## 무엇을

「통화받기」 전에 같은 번호의 지난 통화를 읽고 **통화 목적을 추정한 브리핑**을 돌려준다.
사실은 규칙이 모으고, 모델(운영 kanana, `146`)은 **목적 범주 + 세 줄**만 쓴다. 검사에 걸리면 규칙 브리핑.

## 할 일

1. **서버 슬라이스 `briefing`** — `GET /hub/calls/{call_id}/briefing`(계약은 `220` 3절). schema → router → dto → input port → interactor → output port → adapter → provider → test 전부
   - 지난 통화 사실 수집(규칙): `call` · `follow_up_action` · `closure` · `call_guard_flag` · `blacklist_entry`. **`compliance_flag` 는 싣지 않는다**
   - 규칙 폴백: 최근 통화의 유형 · 미완료 후속조치 · 미완료 절차로 목적(`서류 보완` > `후속 확인` > `컴플레인` > `재문의`)
   - `call_id` 별 메모리 캐시 · 모델 상한 10초
   - 고객 ID·번호·`display_hint` 를 응답에 싣지 않는다 — 테스트로 고정
2. **`ai/` 모델 어댑터** — 운영 `OLLAMA_URL` + `POSTCALL_MODEL` 재사용(새 키 없음). 출력 검사: 목록 밖 범주 · 재료에 없는 숫자 · 금지 표현 · 길이
3. **재생기 `--ring-seconds N`** — 통화를 열고 N초 동안 발화를 보내지 않는다
4. **대본 `scripts/persona_sim/dasan-briefing/`** — 고객 A(서류 보완)·B(컴플레인)·C(후속 확인), 각자 지난 통화 1~2건 + 이번 통화. **정답 목적을 출력 보기 전에 라벨**
5. **채점** — 대본별 범주 일치(규칙). 결과는 「synthetic · n건 · 상한」. 몇 번 돌려 범주가 흔들리는지 같이 기록
6. 진행 기록 · `STATE.md` `ai/` 줄 · 미결

## 완료 조건

- server·ai 테스트 통과, importlinter 계약 유지(server → ai 금지)
- 로컬 스택에서 대본 A·B·C 를 지난 통화 → 이번 통화(`--ring-seconds`) 순으로 돌렸을 때, 벨 시간 안에 브리핑 API 가 `ready` 를 돌려준다
- 채점 결과를 숫자 그대로 기록(틀린 것도 그대로)

## 결과 (2026-10-06)

- 서버 `GET /hub/calls/{call_id}/briefing`(규칙 브리핑 기본 · 캐시 · 동시 요청 합치기 · 취소 안전) · `ai/apps/customer_briefing` 모델 겹 · 재생기 `--ring-seconds` · 대본 `dasan-briefing/` SYN-301~306 · `briefing_check.py`
- 커밋 `91df0ed`..`6aaf5cc`(브랜치 `ai`, 푸시 전). 테스트 server 1,479 · ai 599+ · call-mediator 187 · persona_sim 5 통과, 계약 5·3 KEPT
- **실측(synthetic · 상한)**: 규칙 **2/3** · 처음 설계한 모델 겹 **0/9**(전부 「재문의」) → **범주는 규칙이 정하도록 바꾼 뒤 6/9**(출처 rule 9, 흔들림 없음), 벨 15초 안에 9/9 준비(최대 1,740 ms). 틀린 1건은 SYN-304(폭언 없는 언성 → 콜 가드 신호 없음). 자세히 `decisions/220` 「결과」
- 남은 것: 화면 카드(조서희 `w8-f3-briefing-card-ui`) · 운영 배포는 PR 뒤
