# STATE — 지금 어디까지 왔는가

> 세션 인수인계용 비공개 메모. **지금 상태만 적는다.**
>
> - 세션에 무엇을 했는지 → `jekyll/_logs/` (`/progress/` 가 렌더링). **여기 적지 않는다.**
> - 아직 정하지 못한 것 → `jekyll/open-items.markdown`
> - 지난 세션 기록 → `_project/STATE-archive.md` (2026-08-24 ~ 08-27, 보관용)
>
> **⚠ 이 파일에 세션 기록을 쌓지 않는다.** 자기 영역에 해당하는 줄을 **덮어쓴다.**
> 맨 위에 블록을 끼워 넣으면 네 사람이 같은 자리에서 충돌한다 — 그게 2026-08-27까지
> 실제로 일어난 일이다(`_project/decisions/101`). 「최종 갱신」 줄도 그래서 없앴다.
> 마지막 갱신 시각은 `git log -1 --format=%ai -- _project/STATE.md` 가 갖고 있다.

---

## 현재

**3주차** / 8스프린트 (2026-08-20 ~ 2026-10-27). 1주차 목표 6개 전부 달성.

성공 조건은 F-2가 아니라 **STT 오류 내성 실험(4.2절) + 검색 품질 개선 수치**다.
F·G·H·I 동결 판정은 **6주차 종료 시점**이다(그 전까지는 적용되지 않는다).

---

## 영역별 상태

**자기 줄만 고친다.** 남의 줄은 건드리지 않는다.

| 영역 | 담당 | 상태 |
|---|---|---|
| `server/` | 장민석 | 엔드포인트 14개 · 테스트 327 + integration 3 · CORS 열림(기본 로컬 Vite, 운영 origin 은 `CORS_ALLOWED_ORIGINS`). **모델 없이 할 수 있는 일은 끝났다.** 남은 501 은 `POST /hub/recommendations`(트리거 대기) 하나 |
| `ai/` | 류준 | 검색(BM25+nori) ✅ · 트리거 v1 ✅ · 평가 하네스 ✅ · **C-6 콜 가드 ✅**(`ai/apps/call_guard/`) · **D-5 통화 온도 ✅**(`ai/apps/voice_signal/` — `decisions/203`). **지식베이스 98조항 · 골든셋 156건**(3주차 목표 달성). 테스트 191 · 계약 3종. **실측: Recall@5 0.833 · MRR 0.659 · n96** (`run_id=2`). ⚠ **C-5 절대 규칙 ❌** — P6 인명 2건 누락, `ai/` NER 이 내 몫. A-5 는 AI Hub 505/71479 미신청으로 본체 대기(8kHz 페널티만 분리 완료). 컴플라이언스(6주차) 미착수 |
| 인프라 · CI | 정성윤 | CI 3종 · main 보호 · **사이트 배포 ✅ `https://docs.solidbob.cloud`**(DNS 는 클라우드플레어 — `decisions/102~104`). **저장소 소유권 `SeongYuna` 로 이전 완료**(09-03, `decisions/106` — 룰셋·Pages·협업자 전부 보존). **프론트 2종 배포 ✅ 정성윤 Vercel + Git 연동** — 소개 `www.solidbob.cloud`(`apps/platform`) · 데모 `call.solidbob.cloud`(`apps/dashboard`, mock 모드). 조서희 계정에서 무중단 이관(TXT 검증). ⚠ **`main` 머지로 자동배포가 실제로 도는지는 아직 안 봤다.** **운영 AWS 는 코드까지만** — `infra/terraform/`(EC2+RDS+ES, `validate` 통과) · `infra/docker/`(Dockerfile·compose.prod·Caddyfile) 를 09-03 에 썼으나 **`apply` 안 함, 뜬 리소스 0개**(자격증명 미설정). 도커 빌드도 미검증(데몬 없음). **A(STT) 는 `services/` 디렉터리 자체가 없다 — 코드 0줄.** 배치 전사 `scripts/transcribe_batch.py` 는 결함 3건 수정했으나 **실제 API 경로 여전히 미검증** — 이 머신에 오디오도 `.venv` 도 없다 |
| `apps/` | 조서희 | 대시보드: `/` = 대기화면 ⇄ 어시스트/요약. `ko-masking`은 권한 확인 후 스팬 클릭으로 원문 토글. `ko-grant-delay` 욕설은 별표 마스킹+배너. 랜딩: 다크 레퍼런스 + 해/달 토글. **09-09**: 프론트 계약에 `fired` 반영(`decisions/401`) — 검색 안 함/결과 없음/결과 있음 3상태 구분 + 카드 대기 중 로딩 UI. 실서버엔 로딩 신호가 없어(§7.3 미정) 라이브 모드는 아직 스피너가 안 뜬다. **09-10**: 통화 후 처리 화면에 블랙컨슈머 수동 분류 카드(C-6 확장) 추가 — 자동 탐지 아님, 관리자 알림은 mock. `services/gateway` 알림 API 생기면 교체 대기. `main`(J 블록) 병합 후 프론트 타입을 09-09 스키마 QA에 맞춤(`BlacklistEntryItem.display_hint` 제거·`evidence_snapshot_at` 추가). ⚠ 블랙컨슈머 카드와 J 블록 전환 요청이 의미상 겹침 — [미결](/open-items/), 결정 기록 미작성. |

---

## 실측값 (2026-09-09)

```
2026-09-09 · 골든셋 v1-150(156건) · 지식베이스 98조항 · 커밋 c9da0a3-dirty · run_id=2
ELASTICSEARCH_URL=http://localhost:9200 .venv/bin/python scripts/run_eval.py --runs 3 --record

[retrieval]    recall@5 0.833 ✅ · mrr 0.659 ✅ · n 96
[masking]      누락 2 ❌ · 패턴 오분류 1 · 과잉 0.0 · n 28   **절대규칙 위반**
[call_guard]   재현율 1.0 · 정밀도 1.0 · n 15              ⚠ 자기충족 — 상한이지 성능 아님
[closure_gate] 측정 불가 — 채점 대상 0건
[trigger / compliance / domain_routing]  측정 불가 — 미구현 또는 의도적 미배선
```

**⚠ C-5 절대 규칙이 처음으로 ❌ 다.** 08-27 의 「누락 0 ✅」은 표본 18건 위의 값이었다.
뚫린 둘은 **전부 P6(인명)** — `"저는 최지훈이고요"`·`"신청인 이름은 한서윤으로"` 가
규칙 폴백의 문맥 밖이다. 고칠 곳은 `ai/` NER(류준). 08-27 수치(0.857/0.702, n14)는
4개 도메인·20조항 기준이라 **무효다.**

<details><summary>2026-08-27 값 (4개 도메인·조항 20개 — 무효)</summary>

```
[retrieval] recall@5 0.857 · mrr 0.702 · n 14      [masking] 누락 0 · n 18
[closure_gate] 정확도 1.0 · n 16                    [domain_routing] 0.857 ❌ (B-0 폐기됨)
```
</details>

`eval_run.run_id` 로 DB 에 남는다(커밋·골든셋 버전·표본 수 포함, §5).
재현: 위 명령 그대로. 기본 골든셋이 `v1-150.json` 이라 `--golden-set` 을 안 줘도 된다.
ES 는 `docker build -t callguard-es:local infra/elasticsearch/` 후 9200 으로 띄우고
`scripts/index_knowledge_base.py --to-es --recreate` 로 98조항을 적재한다.

**⚠ 기준선으로 고정하지 않았다.** 절대 원칙 5(미달 시 CI 실패)를 켜면 미구현 때문에 계속
빨간불이다. **수치가 나온 것과 게이트를 거는 것은 다른 결정**이다 → `w2-baseline-gate`.

**⚠ trigger 는 구현이 있는데도 일부러 채점하지 않는다.** 이벤트 도착 시각이 없어 상수로
모형화하고 있어, 채점하면 p50=p95=346·발동률 1.0 이라는 **가짜 만점**이 나온다(절대 원칙 10).

---

## 지금 막혀 있는 것

| 무엇 | 누구 | 비고 |
|---|---|---|
| **오류 주입기가 없다** | 미배정 | **성공 조건의 절반인데 티켓조차 없다.** 텍스트 레벨이라 STT 실물 없이 만들 수 있다 |
| **A(STT) 코드 0줄** | 정성윤 | 「필수」 블록인데 착수 흔적이 없다. 3주차 실시간화 전에 범위를 정해야 한다 |
| **배치 전사 실행 검증** | 정성윤 | 오디오가 있는 머신이 필요하다. `--dry-run` 대조 + 소량 5~10건 → `w2-stt-batch` 완료 |
| 트리거 스포크 배선 | 류준 | 마지막 501 이 여기 걸린다 |
| **P6·P7 NER** | **류준** | **C-5 절대 규칙이 여기서 뚫린다.** `server/` 규칙 폴백은 문맥 있는 이름만 잡는다 |
| **AI Hub 505/71479 신청** | 류준 | A-5 본체가 여기서 막혀 있다. 승인에 시간이 걸린다 |
| **J 서버 어댑터·라우터** | 장민석 | 도메인 규칙(`server/apps/blacklist/`)은 있고 저장·HTTP 가 없다 |
| **F-2 규칙표·`closure` 테이블이 다산을 모른다** | 장민석 | 넣으면 CHECK 거부 + `UnknownClosureType`. 골든셋 F-2 0건의 원인 → `w4-schema-qa-followup` |
| **`transcript_segment` UPSERT 복합키 미반영** | 장민석 | **스키마는 고쳤다. 어댑터를 안 고치면 UPSERT 가 터진다** |
| **`call` 행 생성 경로 없음** | 장민석 | 운영에서 첫 세그먼트가 FK 위반으로 실패한다(QA 중 실제로 부딪혔다) |
| **C-6·D-5 저장 경로 없음** | 류준 | 테이블은 만들었다. **D-5 는 오디오를 안 남겨 재계산 불가** → `w4-c6-d5-persistence` |
| 컴플라이언스(C-1~C-4) | 류준 | `ai/apps/compliance/` 미생성. 6주차 |
| D-1~D-3 | 류준·장민석 | `server/apps/postcall/` 미생성. 7주차 |
| ~~B-0 0.857 ❌~~ | ~~팀~~ | **2026-08-28 폐기됐다**(`decisions/201`) — 다산 단일 도메인이라 라우팅할 대상이 없다 |

---

## 팀 회신 대기

| 누구 | 무엇 |
|---|---|
| **류준** | P6·P7 NER (지금은 `server/` 규칙 폴백. GS-056 이 한계를 고정) |
| **류준** | 다산콜DB **전량 전사 보류** — 시나리오 56개뿐이라 고유 텍스트 상한이 112건이다. 클래스 가중치(트레이너에 없음)부터 → [미결](/open-items/) |
| 류준 | nori 복합명사 분해가 주석 예시와 다름 (사용자 사전) |
| 류준 | ⚠ **사후 공유** — `golden-set/v1-50.json` 음성 6건 추가 · `ai/tests/test_eval_wiring.py` 배선 테스트 3건 |
| ~~정성윤~~ | ~~배포를 한 컨테이너로 할지~~ → **답 나왔다: 한 컨테이너·한 도메인**(2026-09-03, `decisions/105`). `ai.solidbob.cloud` 서술은 문서 5곳에서 삭제 |
| **조서희** | `ClosureType` `"사고·보상"` → `"보상"` (안 고치면 422) |
| 팀 | `segment_id` `string` vs `int` — 7.3절 **예시**가 틀렸다 |
| 팀 | 기획서 정본 — `jekyll/docs/`(800ms) vs `plan.md`(1,500ms). 팀 컨펌은 1,500 쪽 |

---

## 구조 (2026-08-26 확정)

```
server/   요청이 흐르는 길        계약(포트·DTO)·파이프라인 배선·클린 아키텍처
ai/       품질을 만들고 재는 쪽    청킹·BM25·리랭크·모델 학습·평가 하네스
```

의존 방향은 **ai → server 한쪽뿐**이다. 역방향은 `server/.importlinter` 계약 2 가 막는다.
**브랜치 이름 = 디렉터리 이름 = 담당자** — 류준 `ai`, 장민석 `server`, 정성윤 `PM`, 조서희 `frontend`.

> ⚠ **2026-08-26 이전 기록의 `ai` 브랜치는 장민석**이다. 이름이 사람을 갈아탔다.
> 옛 기록은 그 시점의 사실이라 고치지 않는다(절대 원칙 8).

`ai/` 모듈: `retrieval` · `evaluation` · **`call_guard`(C-6)** · **`voice_signal`(D-5)**.
`server/` 스포크: `masking` · `closure_gate` · **`blacklist`(J)**.
DB **22테이블** — 2026-09-09 스키마 QA 로 J 3종 + `call_guard_flag`·`voice_outlier` 추가,
`transcript_segment`·`blacklist_entry` 키 결함 수정(`decisions/205`). `db/schema.sql` 은
**생성물**이다 — 고칠 곳은 `db/generate_schema_docs.py` 의 `TABLES` 다.

**합성 루트**(`.importlinter` `root_packages` 에 **없는** 파일)는 누가 고쳐도 된다 —
`server/main.py` · `ai/provider.py` · `scripts/run_eval.py` · 양쪽 `tests/`.
협의를 절차로 요구하지 않는다(`decisions/023`).

---

## 결정 기록

공동 번호대는 **`024` 까지 찼다.** 담당자별로는 정성윤 `106`·류준 `205` 까지 썼다 —
정성윤 `1xx` · 류준 `2xx` · 장민석 `3xx` ·
조서희 `4xx` · 공동 `024~099` (`decisions/022` ④). 하루에 **세 번** 겹친 뒤 정했다.

**문서 우선순위**: 결정 기록 > 기획서 + 보완지시서 > 파생 문서(`CLAUDE.md`·`rfp-harness`·`jekyll/docs`).
기능을 추가하거나 바꾸려면 결정 기록을 쓴다 — 그것이 기획서를 고치는 공식 경로다.

---

## 내부 메모

- **파생 문서가 기획서보다 빡빡해진 사례가 2026-08-27 대조에서 3건 나왔다** — F·G·H·I 동결의
  「6주차 종료 시점에」 누락 · 「B·E·C-5 절대 사수」 누락(둘 다 `ee5c137`) · 도메인 4종의
  「예시로도」 추가(출처 없음). **팀이 "규칙이 빡빡하다"고 겪은 것의 상당수가 옮겨 적기였다.**
  대조 검사가 없어 우연히 찾았다 — [미결](/open-items/)에 올렸다.
- 이 저장소는 두 사람이 서로 모르고 같은 작업을 한 이력이 있다(사이트·ERD·골든셋 양식).
  **작업 전에 `jekyll/_logs/` 를 먼저 읽는다.**
- 원격 인증: `gh` = SeongYuna (**소유자·admin** — 2026-09-03 이전, `decisions/106`). 저장소 설정을 직접 바꾼다.
- 로컬 지킬 포트: 이 저장소 = **4000**. 다른 클론들이 4100·4200 을 쓴다.
