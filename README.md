# CallGuard — call.solidbob.cloud

**StreamRAG : CallGuard** — 통화를 실시간으로 들으면서 고객이 방금 물은 내용에 필요한 사내 문서를
상담원 화면에 자동으로 띄우고, 컴플라이언스 위반 표현과 개인정보를 실시간으로 탐지·마스킹하는 시스템.

- 팀: SOLIDBOB (4인) — 정성윤(AWS·인프라) · 류준·장민석(백엔드·AI, 공동) · 조서희(프론트엔드)
- 개발기간: 2026-08-20 ~ 2026-10-27 (1주 1스프린트, 총 8스프린트)
- **기획서 사이트: <https://docs.solidbob.cloud/>**
  — [개발목차](https://docs.solidbob.cloud/toc/) ·
  [진행 기록](https://docs.solidbob.cloud/progress/) ·
  [칸반 보드](https://docs.solidbob.cloud/kanban/) ·
  [미결 항목](https://docs.solidbob.cloud/open-items/)
  `main` 에 머지되면 `.github/workflows/pages.yml` 이 `jekyll/` 을 빌드해 자동 배포한다.
- 소개 페이지: <https://www.solidbob.cloud/> — `apps/platform` (Vercel)
- **데모 사이트: <https://call.solidbob.cloud/>** — `apps/dashboard` 상담원 화면 (Vercel).
  게이트웨이·코어가 아직 없어 **mock 으로 돈다**(`VITE_GATEWAY_WS_URL` 이 비면 `MockGatewayClient`).
  둘 다 `main` 머지로 자동 배포된다 (`_project/decisions/106`).

## 저장소 구조

| 경로 | 내용 |
|---|---|
| `CLAUDE.md` | 프로젝트 규칙. 작업 시작 전 필독 |
| `jekyll/` | **지킬 사이트 루트.** 표지 · 목차 · `docs/NN` 본문 · `sprints/` · 진행 기록 |
| `db/` | `schema.sql`(DDL) · ERD(`ERD.md` · `erd.dot` · `ERD.png`) · 생성 스크립트 |
| `server/` | **요청이 흐르는 길**(Python 3.13). 계약(포트·DTO)·파이프라인 배선·클린 아키텍처. `apps/hub` · `core/config.py` · `.importlinter`. → `server.solidbob.cloud` |
| `ai/` | **품질을 만들고 재는 쪽**(Python 3.13). 청킹·BM25·리랭크·모델 학습·평가 하네스. `apps/retrieval` · `apps/evaluation`. **서비스가 아니라 라이브러리라 `server` 와 한 컨테이너로 배포된다**(`decisions/024`·`105`) |
| `infra/` | `docker/`(server 이미지) · `elasticsearch/`(nori 이미지) · `k8s/`(k3s 매니페스트 — `base/` 운영 · `local/` 리허설). **도커 컴포즈는 2026-09-08 에 걷어냈다**(`decisions/107`) |
| `knowledge-base/` | `dasan/` × terms / manual / policy — **다산콜센터 단일 도메인**(2026-08-28, `decisions/201`) |
| `golden-set/` | 골든셋 시나리오 (`v1-10.json` · `v1-50.json` — 다산 기준. 3주차에 재확장) |
| `scripts/`, `data/` | 유틸리티 / 데이터 (원본은 커밋하지 않는다) |
| `_project/` | 비공개 — 기획서 원본·보완지시서, 결정 기록, 세션 인수인계 상태 |
| `.github/workflows/` | `pages.yml`(사이트 배포) · `test.yml`(CI — 하네스 테스트 · 구조 계약 · 사이트 빌드·링크 검사) |

## 로컬 실행

```bash
cd jekyll
bundle exec jekyll serve --host 0.0.0.0 --port 4000
```

```bash
cd server && pytest && PYTHONPATH=apps lint-imports --config .importlinter        # 파이프라인·계약 (4종)
cd ai     && pytest && PYTHONPATH=apps:../server/apps lint-imports --config .importlinter  # 검색·평가 (3종)
python3 scripts/check_site_links.py jekyll/_site   # 내부 링크 (빌드 후)
python3 scripts/check_session_end.py               # 진행 기록·티켓 상태·중복 티켓
python db/generate_schema_docs.py                  # ERD 재생성
```
