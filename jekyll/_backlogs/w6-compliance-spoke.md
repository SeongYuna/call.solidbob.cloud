---
title: "컴플라이언스 분류기 스포크 — 배선은 있는데 판정이 없다"
assignee: "류준"
role: "ai"
status: "done"
sprint: 6
note: "09-15 규칙 v1 · 골든셋 재현율·정밀도 1.0(상한) · 실제 상담원 발화 보류 절반 과탐지 2/4,952"
priority: 64
date: 2026-09-15
requirement:
  - "C-1"
  - "C-2"
  - "C-3"
  - "C-4"
paths:
  - "ai/apps/compliance/*"
---

## 무엇을

`POST /hub/compliance-checks` 뒤에 붙는 **실제 판정 스포크**를 만든다.
지금은 **501** 이다 — [w6-compliance-pipeline](/backlog/w6-compliance-pipeline/)이 경로만 깔아 뒀다.

## 왜 지금까지 없었나

`STATE.md` 「지금 막혀 있는 것」 — **`ai/apps/compliance/` 미생성 · 6주차 · 류준**.
[8주 마일스톤](/docs/08/) 6주차 목표가 「생성 + **컴플라이언스**」다.

## 재현율 우선이다

검수 기준 **재현율 ≥0.90 · 정밀도 ≥0.60.** 순서가 있다 — **애매하면 잡는다.**
정밀도를 올리려고 재현율을 깎지 않는다.

## 501 을 빈 목록으로 바꾸지 않는다

파이프라인 티켓이 적어 둔 그대로다 — **빈 목록을 돌려주면 탐지가 죽은 것이 「깨끗하다」로 읽힌다.**
스포크가 없으면 501 을 유지한다.

## [부록 A-1](/docs/12/) — 등급·점수를 만들지 않는다

응답 필드는 `call_id`·`segment_id`·`findings` **셋뿐**이고, 그 계약을 테스트가 고정하고 있다.
스포크가 등급을 계산해도 실어 보낼 자리가 없다 — **그대로 둔다.**

> 발견이 없는 것은 **「잡힌 것이 없음」**이지 **「안전함」**이 아니다.
> 재현율 0.90 은 10건 중 1건은 놓친다는 뜻이다.

## 완료 조건

- [x] `ai/apps/compliance/` — 분류기 + 대체 표현(C-4) + 포트 어댑터
- [x] `ai/.importlinter` 에 스포크 등록, 계약 KEPT
- [x] 골든셋으로 **재현율 ≥0.90 · 정밀도 ≥0.60** 을 재고, 미달이면 숫자 그대로 적는다
- [x] 프로바이더를 501 → 실제 구현으로. 화면 연결은 [별도 티켓](/backlog/w6-compliance-alert-ui/)

---

## 2026-09-15 — 규칙 v1 로 501 을 걷었다. 분류기는 아니다

### 무엇을 만들었나 — 분류기가 아니라 규칙이다

완료 조건은 「분류기」인데 **규칙으로 만들었다.** 기획서 2.4절이 정한 방식은 KcELECTRA 파인튜닝이지만 **학습 데이터가 없다**(골든셋 컴플라이언스
라벨은 양성 14·음성 6 — 채점용이다). 학습은 정성윤 님 개인 PC 몫이기도 하다. C-6 콜 가드와 같은 길로 **규칙 v1 을 먼저 두고, 분류기가 오면 어댑터를 갈아끼운다.**

```
ai/apps/compliance/domain/value_objects/rules.py   조항별 규칙표 — MANUAL 1.1·1.2·1.3·1.4·1.6·3.1·4.1·4.3
ai/apps/compliance/domain/services/detector.py      판정(요청 동사·건강 문맥·의무/부정 예외·대리 신청 안내 누락)
ai/apps/compliance/adapter/outbound/rule_compliance_adapter.py   CompliancePort — rule_code · phrase · alternative_source 만
ai/provider.py build_compliance_provider · server/main.py _wire_compliance (설정 조건 없음 — 콜 가드와 같다)
```

- **C-4 대체 표현은 조항을 가리킨다**(`alternative_source.doc_id` = MANUAL-1.4·1.2·1.6·3.1·4.1·4.3) — 문장을 지어내지 않는다
- 응답 필드는 셋뿐이다(테스트가 `vars()` 로 고정). 등급·점수 없음
- `POST /hub/compliance-checks` 가 이제 501 이 아니다. 「스포크 없는 배포」의 501 테스트는 배선을 꺼서 유지했다(콜 가드 테스트와 같은 방식)
- ⚠ **골든셋의 C-4 라벨은 「의학적 안심 발언」이다**(GS-312). 기획서의 C-4 는 「권장 대체 표현 제시」라 갈래 이름이 어긋난다 — 채점 기준(골든셋)을 따랐다 → [미결](/open-items/)

### 실측

```
측정일 2026-09-15 · 커밋 38f2fc3-dirty
① 골든셋 v1-150 컴플라이언스 20건(양성 14 · 음성 6)
   ELASTICSEARCH_URL=http://localhost:9200 .venv/bin/python scripts/run_eval.py
   [compliance] 재현율 1.0 · 정밀도 1.0 · tp 14 · fp 0 · fn 0

② AI Hub 민원 질의응답 validation · 다산콜센터 · 실제 상담사 발화 9,881건 (라벨 없음)
   .venv/bin/python scripts/measure_compliance_real_agents.py --split {dev|test}
   대화셋 번호 끝자리 홀짝으로 반씩 — dev 4,929건 · test 4,952건

                         걸린 발화
   첫 판 · 전체           165건 (1.67%)   ← 가르기 전. 158건이 C-1 금액 규칙
   고친 뒤 · dev(본 절반)   4건 (0.08%)
   고친 뒤 · test(안 본 절반) 2건 (0.04%)   택시비 예상 금액 2건
```

### ⚠ ① 은 상한이다 — 성능이 아니다

**규칙을 골든셋 문장을 본 뒤에 썼다.** 문구를 옮기지 않고 조항 갈래로 일반화했고 테스트는 **같은 갈래의 다른 문장**으로 짰지만, 1.0 은 자기충족이다.
C-6 콜 가드의 「⚠ 자기충족 — 상한이지 성능 아님」과 같은 경고를 붙인다.

### ② 가 말하는 것과 말하지 않는 것

- **첫 판은 실제 상담원을 1.67% 잡았다** — 거의 전부 **고정 요금 안내**(「기본요금은 1,250원입니다」)였다. MANUAL-1.6 은 «개별 산정 금액을 단정하지 말라» 인데
  규칙이 「X원입니다」 를 다 잡았다. 그 외: 의무 안내(「헬멧은 무조건 착용하셔야」) · 부정(「무조건 나오는 것이 아니라」) · 비율(「피해액의 100%」) ·
  교통 안내의 「걱정 안 하셔도」 · 고객에게 홈페이지 입력을 안내한 카드번호
- **같은 데이터로 고치고 같은 데이터로 보고하지 않으려고 반으로 갈랐다.** dev 만 보고 고쳤고, test 는 고친 뒤 **한 번만** 봤다. test 결과를 보고 규칙을 다시 고치지 않았다
- test 에 남은 2건(「택시비 24,900원 정도 나올 것으로 예상됩니다」)은 **위반인지 사람이 판단할 경계**다 — 이 스크립트는 판정하지 않는다
- **실제 데이터의 재현율은 모른다.** 실제 상담원이 위반을 거의 안 해서 적게 걸린 것인지, 규칙이 놓친 것인지 **라벨 없이는 가를 수 없다**

### 남는 것

- 분류기(KcELECTRA vs klue/roberta-base) — 학습 데이터부터 없다 → [w5-classifier-ner-benchmark](/backlog/w5-classifier-ner-benchmark/)
- 화면 연결 — [w6-compliance-alert-ui](/backlog/w6-compliance-alert-ui/)(조서희 님)
