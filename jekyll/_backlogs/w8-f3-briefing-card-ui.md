---
title: "F-3 통화 수신 전 고객 브리핑 카드 — 「통화받기」 모달에 지난 통화·추정 목적을 띄운다"
assignee: "조서희"
role: "app"
status: "in-progress"
sprint: 8
priority: 5
date: 2026-10-06
requirement:
  - "F-3"
depends_on:
  - "w8-f3-customer-briefing"
paths:
  - "apps/call/src/components/AgentCallBox.tsx"
  - "apps/call/src/components/CustomerBriefingCard.tsx"
---

> 요청: 류준(2026-10-06). 설계·근거 `_project/decisions/220`. 서버 API 는 류준이 만든다(`w8-f3-customer-briefing`).
> ⚠ **10-15 부터 새 기능 금지**(`decisions/129`) — 그 전에 머지가 목표다.

## 무엇을

전화가 와서 상담원이 **「통화받기」를 누르기 전**, 모달(`AgentCallBox`)에 **고객 브리핑 카드**를 띄운다.
AI 가 같은 번호로 걸려 온 지난 통화들을 읽고 **이번 통화의 목적을 추정**한 결과다.

## 언제 부르나

콜 미디에이터가 이미 보내는 **`started`(`{call_id}`)를 받으면** 아래 API 를 한 번 부른다. 새 WS 메시지는 없다.
시연에서는 재생기가 `--ring-seconds` 동안 발화를 보내지 않으므로, 그동안 모달이 떠 있고 카드가 채워진다.
모델이 3~8초 걸릴 수 있어 **「브리핑 준비 중」** 상태가 필요하다(서버 상한 10초 — 넘으면 서버가 규칙 브리핑을 돌려준다).

## API — `GET {SERVER}/hub/calls/{call_id}/briefing`

인증은 다른 통화 읽기(`/transcript`·`/record`)와 같다.

```json
{
  "call_id": "…",
  "status": "ready",                    // ready | first_contact | unidentified
  "prior_call_count": "2",
  "purpose": {
    "category": "서류 보완",              // 재문의 | 후속 확인 | 서류 보완 | 컴플레인 | 신규 문의 | null
    "text": "지난 통화에서 안내한 위임장을 준비하다 막혀 다시 건 것으로 보입니다",
    "source": "model"                     // model | rule
  },
  "briefing_lines": ["…", "…", "…"],
  "evidence": [
    {"call_id": "…", "started_at": "2026-10-05T14:02:00+09:00", "inquiry_type": "일반행정",
     "summary_confirmed": "true", "incomplete_procedures": ["DASAN-TERM-4.1"]}
  ],
  "signals": {"open_follow_ups": "1", "call_guard_categories": ["insult"], "blacklisted": "false"},
  "generated_at": "…"
}
```

## 화면에 그릴 것 — 상태별

| `status` | 카드 |
|---|---|
| `ready` | 아래 「ready 카드」 |
| `first_contact` | 「같은 번호로 걸려 온 지난 통화가 없습니다 — 첫 문의로 보입니다」 한 줄 |
| `unidentified` | 「발신 번호를 확인할 수 없어 지난 통화를 찾지 않았습니다」 한 줄 |
| 404 · 네트워크 실패 | 카드를 그리지 않는다(모달은 그대로) — **「통화받기」를 막지 않는다** |
| 응답 대기 | 「브리핑 준비 중…」 |

**ready 카드**
- 맨 위: **「추정 통화 목적」** 꼬리표 + `purpose.category` + `purpose.text`
  - `source: "rule"` 이면 꼬리표 옆에 작게 「규칙 요약」 (모델이 아니라는 표시)
- `briefing_lines` 세 줄
- 근거: `evidence` 를 날짜 · 유형으로 나열(「10-05 · 일반행정」), `summary_confirmed: false` 면 「초안」 표시
- 신호: `open_follow_ups > 0` → 「마치지 않은 후속조치 N건」 · `blacklisted` → 「블랙리스트 적용 중」 · `call_guard_categories` 가 있으면 「지난 통화에서 언성이 있었습니다」 류의 **사실 문장**
- 제목은 **「같은 번호로 걸려 온 지난 통화」** — 「이 고객의」라고 단정하지 않는다(가족이 같은 번호를 쓸 수 있다)

## 지켜야 할 것

- **「추정」을 지우지 않는다** — 목적은 AI 의 추측이고 판정이 아니다(절대 원칙 9).
- **단정·점수 표현 금지**(부록 A-1) — 「위험 고객」·「요주의」·퍼센트·신뢰도 숫자를 만들지 않는다. 서버가 주는 문장과 사실만 그린다.
- 고객 ID·번호를 화면에서 만들거나 추정하지 않는다 — 서버도 주지 않는다(`304`·`322`).
- 카드는 「통화받기」 버튼을 가리지 않는다.

## 완료 조건

1. `ready`·`first_contact`·`unidentified`·실패·대기 다섯 상태가 화면에 나온다(mock 모드에 다섯 상태 예시를 넣어 확인)
2. 실서버 모드에서 재생기 `--ring-seconds` 시연(류준 대본 `dasan-briefing/`)으로 카드가 「통화받기」 전에 뜬다
3. 파서 회귀 테스트(vitest) — 필드가 빠지거나 `status` 가 모르는 값이면 카드를 그리지 않는다(오류 배너 없이)

## 2026-10-08 — 서버 쪽은 운영에서 봤다 (정성윤). 화면은 아직

완료 조건 2 의 **절반**이다. 브라우저를 열어 「통화받기」 전에 카드가 뜨는 것을 **눈으로 보지는 못했다** —
여기 적는 것은 그 카드를 채우는 **API 가 운영에서 도는 것을 확인했다**는 것뿐이다.

`GET /hub/calls/shoot1-stt3/briefing` (운영, 토큰은 노드에서 읽음):

```
status            ready
prior_call_count  4
purpose           { category: "재문의", source: "rule" }
briefing_lines    ["같은 번호로 걸려 온 지난 통화 4건 — 최근 10-02 유형 미정"]
evidence          4건 (shoot1-stt2 · shoot1-stt · real-stt-02 · real-stt-01)
signals           open_follow_ups 0 · call_guard_categories [] · blacklisted false
```

**`source: "rule"` 이 찍힌 것이 중요하다** — 모델 범주 판정이 0/9 라 규칙으로 되돌린 `decisions/220` 의
결론이 운영에서 그대로다. 화면이 「추정 통화 목적」 꼬리표를 붙이는 근거이기도 하다(절대 원칙 9).

**남은 것**: 재생기 `--ring-seconds` + `dasan-briefing/` 대본으로 **벨이 울리는 동안** 카드가 뜨는지 —
타이밍은 화면에서만 보인다. 촬영 때 같이 본다.
