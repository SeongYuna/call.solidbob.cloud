---
layout: doc
title: Sprint 1 진행 로그
permalink: /sprints/01/
---

[1주차](/docs/08/) (2026-08-20 ~ 08-26) 목표: **기반 + 전제 확인**

<table>
<thead>
<tr><th>날짜</th><th>진행 내용</th><th>상태</th></tr>
</thead>
<tbody>
<tr><td class="nowrap" rowspan="1">08-20 (목)</td><td>팀명 <strong>SOLIDBOB</strong>, 개발기간(2026-08-20~10-27) 확정</td><td>완료</td></tr>

<tr><td class="nowrap" rowspan="1">08-21 (금)</td><td>개발 환경 구축 — rbenv, Ruby 3.4.10, Jekyll 4.4.1, Bundler 설치. 표지·본문 공통 레이아웃 설계</td><td>완료</td></tr>

<tr><td class="nowrap" rowspan="4">08-25 (화)</td><td>기획서 rev.4(실시간 상담원 어시스트 RAG) 확정 — 사업명 <strong>CallGuard</strong>(StreamRAG : CallGuard)</td><td>완료</td></tr>
<tr><td>팀 구성 재확정: 정성윤(AWS·인프라) · 류준(백엔드·AI) · 장민석(앱·프론트엔드), 3인</td><td>완료</td></tr>
<tr><td>사이트 전체 마이그레이션 — 표지, 개발목차, 본문 15개 페이지(<code>docs/01</code>~<code>docs/15</code>) 재구성</td><td>완료</td></tr>
<tr><td>깃허브 원격을 <code>github.com/SeongYuna/call.solidbob.cloud</code>로 교체, 로컬 <code>backend</code> 브랜치 생성</td><td>완료</td></tr>

<tr><td class="nowrap" rowspan="6">08-26 (수)</td><td>AI Hub 데이터 신청·승인, <strong>V1~V4 전제 4건 실측</strong>(채널 구성 / GPU / STT 숫자 출력 / 부분 결과 지연)</td><td>완료</td></tr>
<tr><td>인터페이스 스키마 <strong>v2</strong> 확정 — interim 교체용 <code>segment_id</code> 추가</td><td>완료</td></tr>
<tr><td>데모 도메인을 가상 통신사 단일 시나리오에서 <strong>실제 확보 데이터 4종</strong>(금융보험·다산콜센터·쇼핑·질병관리본부)으로 전환. 지식베이스·골든셋·DB 스키마 전면 재작성</td><td>완료</td></tr>
<tr><td>팀 <strong>3인 → 4인 개편</strong> — 플러터 앱 중단, 장민석 백엔드·AI 합류, 조서희 프론트엔드 신규 합류</td><td>완료</td></tr>
<tr><td>백엔드 루트 <code>fastapi/</code> 확정 — 허브-스포크 골격, 구조 계약(import-linter) 5종</td><td>완료</td></tr>
<tr><td>평가 하네스 골격 + <strong>CI 3종</strong>(하네스 테스트 · 구조 계약 · 사이트 빌드·링크 검사) 연결</td><td>완료</td></tr>
</tbody>
</table>

## 스프린트 마감 (2026-08-26)

**[1주차 목표 6개 전부 달성](/docs/08/).** 담당자별 티켓은 [칸반 보드](/kanban/), 일자별 상세는 [개발 로그](/progress/)에 있다.

### 계획과 달라진 것

| | 계획 | 실제 |
|---|---|---|
| 도메인 | 가상 통신사 "한별텔레콤" 단일 시나리오 | **실측 데이터 4종**(금융보험·다산콜센터·쇼핑·질병관리본부) |
| 팀 | 3인 (정성윤·류준·장민석) | **4인** — 플러터 중단, 조서희 프론트엔드 합류 |
| 백엔드 구조 | `services/core/` | **`fastapi/`** 허브-스포크 + 구조 계약 5종 |

도메인 전환은 **실제로 확보한 데이터에 통신 도메인이 없다는 사실을 뒤늦게 확인**해서 생긴 변경이다.
이 때문에 지식베이스·골든셋·DB 스키마를 같은 주에 다시 만들었다(`_project/decisions/004`).

### 다음 주로 넘긴 것

- **기준선 게이트** — 측정값이 없는 상태에서 CI 게이트를 넣으면 가짜 기준선을 적게 된다(절대 원칙 2) → [w2-baseline-gate](/backlog/w2-baseline-gate/)
- **도메인 라우팅 분류기** — 방식은 자동 분류로 확정(`decisions/007`), 구현·학습 미착수 → [w1-domain-routing](/backlog/w1-domain-routing/)

### 아직 측정하지 않은 것

Recall@5·MRR·트리거 적절 발동률·마스킹 재현율은 **모두 미측정**이다. 검색·트리거·마스킹 모듈이 아직 없어
하네스가 "측정 불가 — 모듈 미구현"으로 보고한다. 2주차에 가장 단순한 RAG(BM25)로 **잠정 베이스라인**을 만든다.

---

[← 8주 마일스톤으로 돌아가기](/docs/08/)
