---
title: "실시간 경고 화면 — 컴플라이언스 실데이터 연결"
assignee: "조서희"
role: "app"
status: "in-progress"
sprint: 6
priority: 65
date: 2026-09-15
requirement:
  - "C-1"
  - "C-4"
depends_on:
  - "w6-compliance-spoke"
paths:
  - "apps/call/src/*"
---

## 무엇을

상담원 화면의 **실시간 위반 경고 + 대체 표현 제시**를 실서버 `findings` 에 붙인다.

## 화면이 만들 수 없는 것

응답에 오는 것은 `call_id`·`segment_id`·`findings` **셋뿐**이다 —
등급·점수·「안전」 필드가 **계약에 아예 없다**([부록 A-1](/docs/12/)).
그러니 화면에서 «위험도» 를 **계산해 만들지 않는다.** 재료가 없는 것이 설계다.

## 경고는 상담원 발화에만 붙는다

C-1~C-4 는 **상담원** 발화의 위반을 잡고, C-6 콜 가드는 **고객** 폭언을 잡는다 —
**방향이 반대다.** 같은 자리에 같은 모양으로 띄우면 상담원이 «내가 혼나는 것»과
«내가 보호받는 것»을 구분하지 못한다.

## 완료 조건

- [ ] 위반이 뜨고 대체 표현이 함께 보인다
- [ ] 스포크가 501 이면 **「탐지 없음」이 아니라 「탐지 미동작」으로** 보인다 — 조용히 초록색이 되지 않는다
- [ ] 위험도 점수·「안전합니다」류 표현이 UI 어디에도 없다

---

> **보드 최신화 (2026-09-21, 정성윤 — 사용자 지시로 전체 보드를 한 번에 맞췄다).** 상태는 그대로 `todo`. **선행 조건은 다 풀렸다** — 컴플라이언스 규칙 v1(`w6-compliance-spoke`) · 콜 미디에이터 `0.2.1` 이 상담원 발화마다
`/hub/compliance-checks` 를 부르고 `compliance_flag` 로 저장한다(09-18, 09-20 운영 저장 확인).
> 프론트에 없는 것은 **`compliance` 메시지 파서**다 — 지금 화면의 경고는 프론트 로컬 규칙이 만든다. 파서가 들어가면 정성윤이 미디에이터의
> `announceCompliance` 를 켠다(지금 false). **순서가 있다 — 파서 먼저, 방송 나중.** 거꾸로면 읽지 못한 메시지가 온다.

> **라벨 표시 기준 (2026-09-22, 류준 — 본문 메모만, status 는 건드리지 않았다).** 화면에 갈래 이름을 붙일 때는 `_project/decisions/211` 을 따른다 — **C-4 = 「의학적 안심 발언」(근거 없는 안전 보장)** 이고, 「대체 표현」은 C-1~C-4 모든 경고에 붙는 `alternative_source` 다(갈래가 아니다).

## 2026-09-23 — 파서 연결 (조서희, `w6-warning-badge-direction`과 같은 뿌리라 같이 고쳤다)

**실서버 파서가 정말 없었다.** `useCallMediatorSession.ts`의 `onCompliance`가 `callStore.applyCompliance`로
연결은 돼 있었지만(그래서 `state.compliance`에 서버 findings가 쌓이긴 했다), **그 값을 읽는
컴포넌트가 코드베이스 어디에도 없었다.** 화면에 실제로 뜨던 배너는 `detectComplianceRisk`
("불법체류" 한 단어만 잡는 자리표시자)였다 — 그래서 실제 위반 문장은 하나도 안 걸렸다.

`TranscriptPanel.tsx`를 고쳤다 — 실서버 모드(`isCoreApiConfigured()`)에서는 상담원 발화 줄에
`state.compliance[segment_id]`를 그대로 `ComplianceWarningBanner`로 그린다(대체 표현은
`alternative_source.title`, 없으면 "권장 대체 표현이 등록되지 않았습니다"). mock 모드는
기존 자리표시자를 그대로 쓴다(서버가 mock엔 이 신호를 안 보낸다).

**완료 조건 1번은 코드로는 됐지만 운영 검증이 없다** — 서버의 컴플라이언스 규칙이 QA가
지적한 문장("무조건 공제됩니다" 등)을 실제로 findings로 잡아 주는지는 `server/`·`ai/` 쪽
규칙 완성도에 달려 있고, 이번 변경은 **프론트가 그 findings를 받으면 그린다**는 것만
보장한다. **완료 조건 2번(탐지 미동작 표시)은 손대지 않았다** — `complianceUnavailable`도
스토어엔 있지만 여전히 화면에 안 그려진다. 빌드·타입체크만 통과, 운영 재확인 없음
— `status`는 `in-progress`로 둔다.
