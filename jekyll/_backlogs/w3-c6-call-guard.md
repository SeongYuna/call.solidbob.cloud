---
title: "C-6 콜 가드 — 고객 욕설·폭언 탐지"
assignee: "류준"
role: "ai"
status: "done"
sprint: 3
priority: 6
date: 2026-08-28
requirement:
  - "C-6"
---

## 무엇을

**고객** 발화에서 욕설·폭언을 탐지한다.

## 왜 C-1~C-4 로는 안 되는가

방향이 반대다. C-1~C-4 는 **상담원**의 금지 표현을 잡고, C-6 은 **고객**의 폭언을 잡는다.
화자가 다르고 사전이 다르므로 별도 블록이다(`_project/decisions/201`).

## 완료 조건

- [x] 재현율 우선 — C-1~C-4 와 같은 기준(재현율 ≥0.90, 정밀도 ≥0.60)
- [x] **판정은 규칙, 설명만 LLM**(절대 원칙 9). 위험도 점수를 화면에 내지 않는다(부록 A-1)
- [x] 골든셋에 폭언 케이스가 실려 있고 하네스가 채점한다

---

## 결과 (2026-09-09)

```
server/apps/hub/app/dtos/call_guard_dto.py          계약 — CallGuardFlag
server/apps/hub/app/ports/output/call_guard_port.py 포트
ai/apps/call_guard/domain/value_objects/lexicon.py  사전·패턴
ai/apps/call_guard/domain/services/detector.py      판정 (순수 규칙)
ai/apps/call_guard/adapter/outbound/…_adapter.py    포트 구현
ai/apps/evaluation/metrics/call_guard.py            채점
knowledge-base/dasan/manual/MANUAL.md 5장           근거 조항 5개
```

### 갈래를 넷으로 나눴다 — `distress` 를 따로 두는 것이 핵심

`insult` · `threat` · `sexual` · **`distress`**. 앞의 셋은 `MANUAL-5.1~5.2`(단계적 안내 후
통화 종료)이고 `distress`(자해·극단적 선택 암시)는 **`MANUAL-5.4` — 종료하지 않고 전문
기관 연결**이다. **대응이 정반대라 하나로 뭉치면 위기 상황에서 전화를 끊게 된다.**

그래서 ① 판정기가 `distress` 를 **먼저** 본다 ② 채점기가 이진 재현율 옆에
`distress_misrouted`(위기를 폭언으로 분류) · `distress_missed` 를 따로 센다. 이진 지표만
보면 이 오분류가 TP 로 집계돼 사라진다.

### 과탐지를 일부러 막은 자리

- **정상 발화 6건을 골든셋에 넣었다.** 재현율만 보면 「전부 폭언」이라고 답하는 구현이
  만점을 받는다(절대 원칙 10).
- **「죽겠네」는 위기 신호가 아니다.** 한국어에서 힘듦을 나타내는 관용 표현이다.
  `DISTRESS_EXEMPT` 로 면제하고 `GS-512`(정상) ↔ `GS-507`(위기)를 짝으로 고정했다.
  잡으면 전문 기관 연결이 남발되고, 정작 진짜 위기 때 상담원이 경고를 무시하게 된다.
- **욕설 없는 인격 모독을 사전 밖 패턴으로 잡는다.** `MANUAL-5.2` 가 「반복되는 인격
  모독」을 종료 사유로 두는데 그 대부분이 욕설이 아니다 — 사전만 있으면 이 구간이
  통째로 비어 재현율이 구조적으로 막힌다.

### ⚠ 수치를 목표 달성으로 읽지 않는다

`재현율 1.0 · 정밀도 1.0 · n 15` 가 나왔지만 **케이스와 규칙을 같은 사람이 같은 날 만들었다.**
`golden-set/README.md` 가 F-2 에 대해 경고한 자기충족 문제가 그대로 걸린다 —
**이건 상한이지 성능이 아니다.** 교차검수가 필요하고, 그 전까지 "C-6 목표(재현율 ≥0.90)
달성"으로 인용하지 않는다.

### 남긴 것

- **§7.3 계약에 C-6 이벤트가 없다** — 프론트가 `CallGuardFlag`(`category: "폭언"|"욕설"|"위협"`)를
  임시로 먼저 정의해 뒀는데 **`sexual`·`distress` 가 없다.** 특히 `distress` 는 화면 대응이
  달라야 하므로 그냥 매핑할 수 없다. 조서희 님과 맞춰야 한다.
- 어댑터는 받은 문자열을 그대로 자른다. **C-5 뒤에 꽂아야** `MANUAL-5.5`(폭언 기록에
  개인정보를 남기지 않는다)를 지킨다 — 파이프라인 순서는 `server/` 배선의 몫이다.
