---
title: "F-2 필요서류 체크리스트 골든셋 케이스 99건 — 하네스가 실제로 채점하게 만든다"
assignee: "류준"
role: "ai"
status: "done"
sprint: 5
priority: 58
date: 2026-09-21
requirement:
  - "F-2"
  - "E-1"
paths:
  - "golden-set/*"
  - "knowledge-base/dasan/policy/*"
---

## 무엇을

`golden-set/v1-150.json` 에 F-2(필요서류 체크리스트) 케이스 **99건**(`GS-601~GS-699`, `module: "F-2"`)을 더해
하네스 `closure_gate` 가 `NO_SAMPLES` 대신 실제 채점 결과를 내게 한다. 같이 `DASAN-POLICY-1` 을 `decisions/201`·`305` 에 맞춰 고쳤다.

## 왜

`decisions/118`(2026-09-19)이 F-2 를 「설계 문서 전환」으로 판정한 근거는 구현 부족이 아니라 **채점 표본 0건**이었고,
*"골든셋에 F-2 케이스가 생기고 하네스가 실제로 채점하면 되돌린다"* 고 문을 열어 뒀다. 이 티켓은 그 조건을 채운다 —
**118 을 되돌릴지는 팀이 정한다.** 함께 처리하기로 한 셋(① 골든셋 케이스 ② rev.5 `incomplete` 반영 ③ `DASAN-POLICY-1` 어긋남) 중
②는 이미 되어 있었고, ①③을 여기서 한다.

## 어떻게

- 규칙표(`closure_rule.py`) **29조항**마다 ① 전부 안내 → `complete` ② 하나 빠짐 → `incomplete` + 그 이름 ③ 아무것도 안내 안 됨 → 전부 `missing`
  (87건) + 경계 12건(조건부만 안내 · 키 이름 불일치 · 규칙표에 없는 키 · 복수 누락 순서 · 조건부 false 무관).
- **기대값은 규칙표를 읽고 사람이 정했다** — 조항별 필수 서류를 손으로 옮겨 적은 표 위에서 적은 뒤 `gate.evaluate` 로 대조. 어긋남 0건.
- `EXCLUDED` 6조항(1.3·1.4·3.4·3.6·6.5·6.8)은 규칙이 없어 `UnknownProcedure` 가 나므로 넣지 않았다 — README 에 「규칙 없는 조항은 채점 대상이 아니다」로 적었다.
- 규칙표·판정 코드는 손대지 않았다.

## 완료 조건

- [x] 규칙표 29조항 전부에 케이스 3건 이상 · 경계 케이스 포함 — **99건**
- [x] 기대값을 손으로 정한 뒤 코드와 대조 — 어긋남 0건
- [x] 하네스 F-2 리포트가 `NO_SAMPLES` 가 아니다 — `{"accuracy": 1.0, "absolute_rule_passed": true, "failed_items": [], "n": 99}`
  (ES 없이 `Ports(closure_gate=RuleClosureGateAdapter())` 만 꽂아 `run_eval`, 커밋 `97f7b25-dirty`)
- [x] `cd ai && pytest` **429 passed** · `cd server && pytest` **1254 passed** · `lint-imports` 3 kept
- [x] `server/apps/closure_gate/tests/domain/test_golden_set_closure.py` skip 해제 → **199 passed**
  (⚠ 이 테스트가 `v1-50.json` 을 읽고 있어서 케이스를 넣어도 skip 이 안 풀렸다 — 공식 골든셋 `v1-150.json` 으로 **경로 한 줄**만 고쳤다)
- [x] `ai/apps/evaluation/tests/` 의 「F-2 케이스가 없다」 단언 2곳을 「있고 모양이 맞다 / 표본 없는 목록에서만 NO_SAMPLES」로 바꿨다
- [x] `DASAN-POLICY-1` — 「F-2 는 필요서류 체크리스트로 적용, 종결 차단 게이트는 미적용, `incomplete` 는 경고」로 고쳤다. ID·주석 유지, 이전 판 요지 한 줄 보존.
  골든셋 B 항목의 `expected_doc_ids`/`distractor_doc_ids` 에 `DASAN-POLICY-1` 참조 **0건** — 검색 라벨 영향 없음
- [x] `golden-set/README.md` F-2 절·분포 표 갱신

## 한계

- **상한이다.** 기대값을 규칙표 자체에서 정했으므로 `accuracy 1.0` 은 「코드가 규칙표를 그대로 따르는가」이지 「안내가 실제로 충분했는가」가 아니다.
  규칙표 작성자(장민석)와 케이스 작성자(류준)는 다르지만 같은 표를 보고 적었다 — C-6 자기충족 주의와 같은 결. 「F-2 판정 정확도 100% 달성」으로 인용하지 않는다.
- 자동 판정(상담원 발화 키워드 → evidence, `detection.py`)의 정확도는 재지 않았다 — 케이스의 evidence 는 이미 채워진 bool 이다. 발화가 붙은 케이스가 따로 필요하다(미결).
- `POLICY-1` 본문이 바뀌었으므로 다음 ES 재색인 때 검색 결과가 달라질 수 있다 — 골든셋 라벨에는 안 걸리지만 재측정 시 함께 적는다.

## 팀이 정할 것

- `decisions/118` 을 되돌려 `w8-f2-wrapup` 을 「구현 완결」 갈래로 옮길지(정성윤·장민석 티켓이라 여기서 건드리지 않았다).
- `EXCLUDED` 6조항에 조건 판정 규칙을 만들지 — 만들면 케이스 3건씩 더한다.
