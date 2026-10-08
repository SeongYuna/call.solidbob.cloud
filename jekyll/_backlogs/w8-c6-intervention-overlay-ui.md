---
title: "C-6 베타 — 폭언 안내 일시정지 덮개 · 안내 음성 · 종료 권고 표시 (call_guard_intervention)"
assignee: "조서희"
role: "app"
status: "in-progress"
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
3. ~~실서버 + 미디에이터 개발 페이지(`dev_page`)에서 고객 화자로 폭언 어휘를 입력해 덮개가 뜨고 `pause_ms` 뒤 걷힌다~~
   → **2026-10-08 고쳐 적는다.** 이 조건을 글자 그대로 하려면 **운영 미디에이터에 `CALL_GUARD_INTERVENTION_BETA=1` 을 넣어야 하는데,
   `decisions/221` 이 「운영 매니페스트에 넣지 않는다 · 켜려면 새 결정 기록을 쓴다」고 정해 두었다.** 티켓 조건이 결정 기록과 어긋나 있었다.
   **운영은 건드리지 않고 사슬을 쪼개 확인한다** — ⓐ 운영이 내는 실제 `call_guard` 카테고리(베타와 무관하게 나온다) ·
   ⓑ 그 카테고리로 단계 판정이 맞는가 · ⓒ 그 단계가 덮개로 그려지는가(vitest). **ⓐⓑ 확인함 ↓**

## 2026-10-08 — 조건 3 을 쪼개 확인했다 (정성윤). 운영 베타는 켜지 않았다

**왜 안 켰나** — `decisions/221` 제목이 **「베타 — 운영 미적용」**이고, 본문이 *「기본값은 꺼짐이다. 운영에 켜려면
「베타를 벗어나는 조건」을 채우고 **새 결정 기록을 쓴다**」* 라고 정하고 있다. 그 조건은 **측정 데이터**를 요구하는데
(분류기를 학습·측정할 고객 데이터가 없다, 절대 원칙 7) 우리에겐 없다. **10초짜리 연기 시험 때문에 그 결정을 뒤집지 않는다.**

### ⓐ 운영이 실제로 내는 `call_guard` — 베타와 무관하게 나온다 (통화 `c6guard-052523`)

| 보낸 발화 | 잡힌 것 |
|---|---|
| 「이 멍청한 놈이 말귀를 못 알아듣네」 | `insult` · 「멍청한」 · `DASAN-MANUAL-5.1` |
| 「아니 **이따위로** 일하면서 뭐하는 거야 진짜」 | **0건 — 사전에 없다** |
| 「거기 **찾아가서 가만 안 둔다** 진짜」 | `threat` ×2 · `DASAN-MANUAL-5.2` |

`call_guard_intervention` 은 **0건** — 운영 베타가 꺼져 있다는 증거이기도 하다(`221` 의도대로).
가운데 줄은 미결에 이미 적힌 **C-6 사전 구멍**(「이따위로」)이 운영에서 그대로 재현된 것이다.

### ⓑ 그 실제 카테고리로 단계 판정

```
insult        → stage=warning        근거 DASAN-MANUAL-5.1  pause 8,000ms  누적 1
(사전에 없음) → 개입 없음
threat        → stage=end_suggested  근거 DASAN-MANUAL-5.2  pause 0        누적 2
```

**`threat` 이 1차 안내 뒤 곧바로 `end_suggested` 로 갔다** — 매뉴얼 5.2(「성적 표현·위해 협박은 1차 안내 후 곧바로」) 그대로다.
`pause 0` 인 것도 맞다 — 종료 권고는 덮개를 걷고 배너만 띄운다.

### ⓒ 단계 → 화면

vitest 18건이 덮는다(PR #169). 미디에이터 쪽도 「켜짐이면 `call_guard` 다음에 `call_guard_intervention` 이 나간다」를
테스트로 고정해 두었다(`w8-c6-intervention-beta`).

### 남은 것 — 브라우저에서 눈으로

덮개가 실제로 그려지고 `pause_ms` 뒤 걷히는 **타이밍**은 화면에서만 보인다. **촬영 때 같이 본다**(F-3 와 같은 처지).
그때도 운영 베타를 켜지 않을 거라면, 로컬 미디에이터에 `=1` 을 주고 띄워서 본다 — 운영 매니페스트는 그대로다.
