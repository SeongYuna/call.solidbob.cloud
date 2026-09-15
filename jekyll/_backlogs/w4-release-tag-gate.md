---
title: "릴리스 태그 게이트 — fail-closed · PR 시점 검사"
assignee: "정성윤"
role: "infra"
status: "done"
sprint: 4
priority: 3
date: 2026-09-14
paths:
  - ".github/workflows/release.yml"
  - ".github/workflows/tag-check.yml"
  - "scripts/check_release_tags.py"
---

## 무엇을

`release.yml` 의 「코드가 바뀌었는데 `newTag` 가 그대로면 실패」 게이트를 고친다.

## 왜

릴리스 실패 5건 중 4건이 이 게이트였다(`#55`·`#59`·`#61`·`#73`). 게이트는 옳게 동작했지만
**걸리는 시점이 머지 후**였고, **레지스트리 조회가 실패하면 게이트가 조용히 사라지는** 경로가 있었다.

`sha-<커밋>` 태그로 전환해 게이트를 통째로 없애는 안을 먼저 검토했으나 `converge.sh` 가
저장소의 `newTag` 를 직접 읽어 **매일** CI 배포를 되돌리므로 기각했다 — `_project/decisions/111`.

## 완료 조건

- [x] 레지스트리 조회 fail-closed (200/404/판정 불가)
- [x] PR 시점 검사 `tag-check.yml` (이미지 안 굽고 AWS 안 건드림)
- [x] `fetch-depth: 0` + 조용한 폴백 제거
- [x] `deploy` → `k3s-deploy` 개명
- [x] 판정을 `scripts/check_release_tags.py` 한 벌로
- [x] `#73` 재현 · 새 태그 · 문서만 · 조회 불가(401) 네 경우 확인
- [ ] 룰셋에 `tag-check` 를 필수 통과 검사로 등록 — **저장소 admin(콘솔)**, 미결
