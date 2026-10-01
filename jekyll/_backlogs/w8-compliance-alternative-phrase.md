---
title: "컴플라이언스 경고에 매뉴얼의 권장 문장을 보낸다 — 조항 번호 대신"
assignee: "정성윤"
role: "ai"
status: "in-progress"
sprint: 8
priority: 91
date: 2026-10-02
requirement:
  - "C-1"
  - "C-3"
  - "C-4"
paths:
  - "ai/apps/compliance/*"
depends_on:
  - "w6-compliance-spoke"
---

## 무엇을

상담원 화면의 컴플라이언스 경고에 **조항 번호 대신 매뉴얼의 권장 문장**이 뜨게 한다.

## 왜

10-02 사용자 지적: 지금은 위반 감지만 되고 대체 표현이 안 보인다. 실물 화면은 「근거 조항 · 무조건 · DASAN-MANUAL-1.4」 처럼 번호만 띄웠다 —
서버가 `alternative_source.title` 에 조항 ID 를 넣어 보냈기 때문이다. 화면은 `title` 이 문장이면 「권장 표현」 으로 띄우게 이미 돼 있다
([w6-compliance-alert-ui](/backlog/w6-compliance-alert-ui/) 09-30 `complianceLabel`).

문장을 지어내지 않는다 — **매뉴얼 조항에 글자 그대로 있는 문장만** 보낸다(절대 원칙 9 · `decisions/211`).

## 완료 조건

- [x] 규칙표에 권장 문장 칸(`alternative_phrase`) — 1.4 표의 두 문장(C-1 확정적 보장 여섯 규칙 · C-3 「제가 알기로는」)
- [x] 어댑터가 `title` 에 「문장 (민원응대매뉴얼 1.4)」 를 싣는다. 문장이 없는 갈래는 전처럼 조항 ID
- [x] 규칙표의 문장이 `MANUAL.md` 조항 본문에 글자 그대로 있는지 테스트가 본다(두 벌로 갈라지지 않게)
- [ ] 운영 배포(서버 태그 `0.1.45` 에 같이 실린다 — [w8-postcall-model-prod](/backlog/w8-postcall-model-prod/) 와 같은 이미지)
- [ ] 운영 화면에서 「무조건」 발화에 「권장 표현 · 소관 부서 확인 후 안내드리겠습니다」 가 뜨는 것을 눈으로 본다

## 범위 밖 (미결로 올렸다)

지침만 있는 갈래(1.6 · 3.x · 4.1)와 금지만 있는 갈래(1.2 · 4.3)는 그대로 조항 번호다 — [미결 항목](/open-items/) 10-02.

## 2026-10-02 — 코드 (정성윤)

- `ai/apps/compliance/` 의 `rules.py`(칸 추가 · 문장 상수 둘) · `detector.py`(판정 결과에 문장을 싣는다) · `rule_compliance_adapter.py`(`title`) · 테스트 +8.
  계약(DTO) · 콜 미디에이터 · 프론트는 건드리지 않았다 — 미디에이터는 `findings` 를 그대로 넘기고 화면은 `title` 을 그대로 띄운다(코드로 확인).
- 판정은 그대로다 — 무엇을 잡는지는 한 글자도 안 바뀌었고 하네스는 `title` 을 보지 않는다(이진 채점). 수치 변화 없음.
- ai `compliance` 47 통과 · ai 전체 579 통과(`test_harness_postcall` 2건은 이 Windows 머신의 심볼릭 링크 권한 문제 — 수정 전에도 같다) · server 1,451 통과 · ai 구조 계약 3종 KEPT.
- `decisions/138` 동결 중이지만 시연 화면에 닿는 변경이고 사용자 지시다.
