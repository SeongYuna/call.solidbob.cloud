---
title: "C-6 베타 — 폭언 안내 일시정지 덮개 · 안내 음성 · 종료 권고 표시 (call_guard_intervention)"
assignee: "조서희"
role: "app"
status: "todo"
sprint: 8
priority: 6
date: 2026-10-06
requirement:
  - "C-6"
depends_on:
  - "w8-c6-intervention-beta"
paths:
  - "apps/call/src/lib/ws/realCallMediatorClient.ts"
  - "apps/call/src/types/contract.ts"
  - "apps/call/src/store/callStore.ts"
---

> 요청: 류준(2026-10-06). 설계·근거 `_project/decisions/221`. 미디에이터 쪽은 류준(`w8-c6-intervention-beta`).
> **베타 — 미디에이터가 `CALL_GUARD_INTERVENTION_BETA=1` 일 때만 이 메시지를 보낸다.** 운영에서는 오지 않는다. 메시지가 안 와도 화면이 지금과 똑같아야 한다.
> ⚠ 10-15 부터 새 기능 금지(`decisions/129`).

## 무엇을

고객이 욕설·폭언을 하면 미디에이터가 기존 `call_guard` 다음에 **`call_guard_intervention`** 을 보낸다. 화면은 단계에 따라 —

| `stage` | 화면 |
|---|---|
| `warning` | `pause_ms` 동안 상담 영역 위에 **「일시정지 — 고객 안내 중 (1차)」** 덮개 + `announcement` 문구 표시 + 음성으로 읽기(브라우저 `speechSynthesis`, `ko-KR`). 끝나면 덮개를 걷고 「상담을 이어가세요」 |
| `final_warning` | 같은 모양, 「(2차)」 |
| `end_suggested` | 덮개 없음. 경고 배너 **「매뉴얼 5.1·5.2 — 통화 종료를 판단할 수 있습니다. 종료 여부는 상담원이 정합니다」** — **자동 종료 버튼·자동 동작을 만들지 않는다** |

```json
{"type": "call_guard_intervention",
 "payload": {"call_id": "…", "segment_id": "12", "stage": "warning", "abuse_count": "1",
             "pause_ms": "8000", "announcement": "고객님, 원활한 상담을 위해 …", "source_doc_id": "DASAN-MANUAL-5.1",
             "beta": "true"}}
```

값은 전부 문자열. `end_suggested` 는 `pause_ms: "0"`, `announcement: null`.

## 지켜야 할 것

- 모든 표시에 **「베타」 꼬리표** — 탐지 성능은 측정 불가다(`221` 5절)
- **전사·자막은 덮개 아래에서도 계속 쌓인다** — 덮개는 화면을 가릴 뿐 데이터를 버리지 않는다. 덮개를 상담원이 닫을 수 있게 한다
- 「위험 고객」·점수·퍼센트 표현 금지(부록 A-1). 서버가 주는 문구를 그대로 쓴다
- 지금 안내 음성은 **상담원 PC 에서만** 나온다 — 고객에게 들리게 하는 것은 교환기 연동이 필요하다(정성윤 `w8-c6-intervention-telephony`). 화면 문구에 「고객에게 안내했습니다」라고 쓰지 않는다 → 「고객 안내 문구」

## 완료 조건

1. 파서 + vitest — 모르는 `stage`·빠진 필드면 무시(오류 배너 없이)
2. mock 모드에 세 단계 예시
3. 실서버 + 미디에이터 개발 페이지(`dev_page`)에서 고객 화자로 폭언 어휘를 입력해 덮개가 뜨고 `pause_ms` 뒤 걷힌다
