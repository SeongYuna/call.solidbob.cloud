---
title: "배포 태그 번호 선점 방식을 정한다 — 하루에 세 번 겹쳤다"
assignee: "정성윤"
role: "infra"
status: "done"
sprint: 6
priority: 70
date: 2026-09-22
---

> **정성윤이 09-22 오늘 진행 기록·미결 항목을 보고 만든 티켓이다.** 담당은 «제안»이다 — 본인이 확인하고 맞으면 착수, 아니면 옮긴다.

## 무엇을

09-22 하루에 server 태그가 세 번 겹쳤다 — `0.1.28`(#114·#117), `0.1.29`(`server` 브랜치 선점), `0.1.31`(#119). `tag-check` 가 막아 사고는 아니지만 **PR 마다 한 번씩 되돌아온다**(결정 기록 번호와 같은 병, `decisions/022` ④).

## 선택지 ([미결](/open-items/) 09-22)

1. 브랜치별 번호대(패치 자리 대신 빌드 번호)
2. 머지 시 `release.yml` 이 채번하고 `newTag` 는 «올려야 함» 표시만
3. 지금대로 두고 `check_release_tags.py` 의 「다른 브랜치가 선점」 경고를 오류로 격상

## 완료 조건

- [x] 결정 기록(`1xx`) + 선택한 방식대로 `scripts/check_release_tags.py`·`release.yml`·런북 갱신(파이프라인 파일은 런북 먼저)

## 결과 (2026-09-22)

**3번 채택** — `_project/decisions/131`. `scripts/check_release_tags.py` 의 ⑥ 「다른 브랜치가 선점」을 `::warning::` 에서 `::error::` 로 올려 `failed` 에 합쳤다(함수 `tag_taken_elsewhere`, 반환값이 오류 목록). 물려받은 값은 여전히 걸리지 않는다. `release.yml` 은 손대지 않았다 — 판정 로직이 한 벌(`decisions/111`)이라 스크립트만 바뀌면 된다.
