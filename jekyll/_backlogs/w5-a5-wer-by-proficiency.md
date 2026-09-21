---
title: "A-5 1차 범위 — 숙련도 등급별 WER/CER"
assignee: "류준"
role: "ai"
status: "done"
sprint: 5
priority: 55
date: 2026-09-15
requirement:
  - "A-5"
depends_on:
  - "w3-a5-translation-spike"
note: "09-21 실측 — 8 kHz WER Beginner 0.412 · Intermediate 0.266 · Advance 0.225 · Fluent 0.198(n=20/등급, 상한). 측정 기록은 w3-a5-translation-spike 09-21 절"
paths:
  - "ai/apps/evaluation/metrics/asr.py"
  - "scripts/measure_a5_proficiency.py"
  - "jekyll/assets/a5-wer-2026-09-21.json"
---

## 무엇을

A-5 의 **1차 범위 ⓑ**(서툰 한국어를 정확히 전사)를 **숙련도 등급별 WER/CER** 로 잰다.
[요구사항표](https://github.com/SeongYuna/call.solidbob.cloud/blob/main/.claude/rules/rfp-harness.md)의
A-5 검수 기준이 그대로 이것이다.

## 왜 A-5 인가 (A-3 이 아니다)

기획서의 `A-3` 은 「브라우저 실시간 전달(WebSocket)」이다.
`decisions/201` 초안의 `A-3` 표기는 **오기**이며 2026-08-28 에 정정됐다.
**코드 주석에는 `# Requirement: A-5` 를 쓴다.**

## 무엇이 막고 있는가

`STATE.md` 「지금 막혀 있는 것」 — **AI Hub 505/71479 미신청**으로 A-5 본체가 대기 중이고,
8kHz 대역 페널티 분리만 끝나 있다. 승인에 시간이 걸린다.

⚠ [미결 항목](/open-items/)의 최대 리스크도 여기다 — **외국인 화자 한국어 음성 데이터 0건.**
다산 데이터는 전부 내국인 발화다. 출처를 못 찾으면 **측정할 방법 자체가 없다**(절대 원칙 10).

## 완료 조건

- [x] 숙련도 등급을 **데이터에 있는 라벨로** 가른다 — `SpeakerMetadata.proficiency` 4등급(71479)
- [x] **평균 하나로 뭉개지 않는다**(검수 기준 명시) — 등급별 4행, 전체는 참고로만
- [x] **목표치를 지어내지 않는다** — 측정·기록만 한다(절대 원칙 2)
- [x] ~~데이터를 못 구하면 「측정 불가 — 표본 없음」으로 닫는다~~ — 09-21 데이터가 와서 잰 값으로 닫는다

## 2026-09-15 — 상태 그대로다

**AI Hub 505·71479 신청이 여전히 안 됐다.** 신청은 AI Hub 계정으로 사람이 해야 하는 일이라 이번 세션에서 할 수 없었다. 외국인 화자 음성이 0건인 상태에서
이 티켓으로 잴 수 있는 것은 없다(09-09 에 8kHz 페널티 분리만 끝냈다). **데이터가 오기 전에는 「측정 불가 — 표본 없음」이다.**

## 2026-09-21 — 잰 값으로 닫는다

**측정은 `w3-a5-translation-spike` 09-21 절**(명령·커밋·표본 설계·원본 vs 8 kHz·정규화 전/후·한계 8개)에 있다. 여기는 요약만.

```
2026-09-21 · 97f7b25-dirty · seed 20260921 · AI Hub 71479 validation · Google STT v1 기본 모델(ko-KR)
scripts/measure_a5_proficiency.py · 8 kHz 다운샘플 · 등급당 20건(3~6초, 화자당 ≤2) · STT 482.3초
```

| 등급 | n | WER | CER |
|---|---|---|---|
| Beginner | 20 | 0.412 | 0.221 |
| Intermediate | 20 | 0.266 | 0.198 |
| Advance | 20 | 0.225 | 0.087 |
| Fluent | 20 | 0.198 | 0.067 |

원본(48 kHz) 대비 8 kHz 는 같은 20건에서 WER +0.065 · CER +0.029.

⚠ **상한이다** — 온라인 녹음을 다운샘플만 했고(코덱·잡음 없음), 낭독·질문답변이라 민원 어휘가 아니며, 3~6초 짧은 발화만 골랐고,
모어가 인도네시아·베트남에 몰려 있고, 등급당 n=20 이다. Chirp 3 가 아니라 v1 기본 모델이다. 실제 통화에서는 더 나쁘다.
공개 요약 `jekyll/assets/a5-wer-2026-09-21.json`(건별 전사 없음).

이 티켓이 맡은 「등급별로 잰다」는 끝났다. 남은 왕복 지연·코어 유지 판단은 `w3-a5-translation-spike` 에 그대로 있다.

