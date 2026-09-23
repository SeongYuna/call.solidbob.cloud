import type { ReactElement } from "react";

const CARDS = [
  {
    title: "실시간 자동 마스킹",
    body: "통화 중 트랜스크립트와 통번역 문장에서 전화번호·주민등록번호·주소·이메일을 감지해 즉시 가립니다.",
  },
  {
    title: "권한 기반 원문 열람",
    body: "원문 확인은 권한이 확인된 사용자만 가능하도록 분리하고, 열람 시점을 기록으로 남기는 것을 전제로 설계했습니다.",
  },
  {
    title: "마스킹 기본값 PDF",
    body: "요약 리포트는 마스킹본이 기본이며, 원문 포함본은 별도 선택과 권한 확인을 거쳐야 생성됩니다.",
  },
] as const;

const DEMO_SCOPE = [
  "모든 대화·리포트는 브라우저 안에서만 처리되는 시연 데이터입니다.",
  "통화 내용이 서버로 전송되거나 저장되지 않습니다.",
  "마스킹은 규칙 기반이며, 모든 형태의 개인정보를 보장하지 않습니다.",
  "「권한 확인」 버튼은 실제 인증이 아닌 동작 시연용 전환입니다.",
] as const;

const OPS = [
  "전송 구간(TLS)·저장 구간 암호화와 키 관리 체계 적용",
  "역할 기반 접근 권한과 원문 열람 감사 로그 기록",
  "목적 달성 후 보관 기간에 따른 자동 파기 정책",
  "서버 측 재검증을 포함한 이중 마스킹 및 정기 점검",
] as const;

// 절대 원칙 2 — 측정하지 않은 수치를 기록하지 않는다. 셋 다 ai/ 평가 하네스가 낸
// 값이고 언제·커밋·표본 수를 아래 각주에 남긴다(`w6-platform-unmeasured-numbers`,
// 2026-09-23 — 옛 「38% 처리시간 단축」·「92% 정서위기 감지」·「5개 언어 지원」은
// 실측한 적 없는 값이라 지우고 이걸로 바꿨다. 세 번째(A-5 통번역)처럼 측정
// 자체가 없는 항목은 숫자를 지어내는 대신 실측이 있는 다른 항목으로 채웠다).
const STATS = [
  { value: "0건", label: "개인정보 마스킹 누락 (P1~P7, n=28)" },
  { value: "100%", label: "필요서류 판정 정확도 (n=99, 팀 규정 기준)" },
  { value: "96.9%", label: "필요서류 검색 정확도 Recall@5 (n=96)" },
] as const;

export function PrivacySection(): ReactElement {
  return (
    <section id="privacy" className="scroll-mt-[88px] bg-page px-5 pb-20">
      <div className="mx-auto max-w-[1180px]">
        <p className="mb-3 text-[13px] font-semibold text-amber">
          (c) 개인정보 보호
        </p>
        <h2 className="heading m-0 max-w-[16em] text-[clamp(26px,3.4vw,40px)] leading-snug tracking-tight">
          민감정보는 기본적으로{" "}
          <span className="text-amber">가려진 채 흐릅니다</span>
        </h2>
        <p className="mt-4 max-w-[46em] text-[15px] leading-relaxed text-muted">
          상담 화면·요약·PDF 리포트 어디서든 전화번호·주민등록번호·주소·이메일이
          자동으로 감지되어 마스킹된 상태로 표시됩니다. 원문은 권한이 확인된
          사용자만 열람하도록 설계했습니다.
        </p>
        <ul className="mt-10 grid list-none grid-cols-1 gap-4 p-0 mid:grid-cols-3">
          {CARDS.map((card) => (
            <li
              key={card.title}
              className="rounded-[22px] border border-line bg-card p-6"
            >
              <h3 className="m-0 text-[16px] font-semibold">{card.title}</h3>
              <p className="mt-3 mb-0 text-[14px] leading-relaxed text-muted">
                {card.body}
              </p>
            </li>
          ))}
        </ul>
        <div className="mt-4 grid grid-cols-1 gap-8 rounded-[22px] border border-line bg-card px-6 py-7 mid:grid-cols-2">
          <div>
            <h3 className="m-0 text-[14px] font-semibold text-live">
              지금 이 데모의 범위
            </h3>
            <ul className="mt-4 m-0 flex list-none flex-col gap-2.5 p-0 text-[14px] leading-relaxed text-muted">
              {DEMO_SCOPE.map((line) => (
                <li key={line}>· {line}</li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="m-0 text-[14px] font-semibold text-amber">
              실제 운영에 필요한 원칙
            </h3>
            <ul className="mt-4 m-0 flex list-none flex-col gap-2.5 p-0 text-[14px] leading-relaxed text-muted">
              {OPS.map((line) => (
                <li key={line}>· {line}</li>
              ))}
            </ul>
          </div>
        </div>
        <div
          id="stats"
          className="mt-4 scroll-mt-[88px] rounded-[22px] border border-line bg-card px-6 py-7"
        >
          <dl className="m-0 grid grid-cols-1 gap-8 mid:grid-cols-3">
            {STATS.map((item) => (
              <div key={item.label}>
                <dt className="text-[36px] font-semibold tracking-tight text-amber">
                  {item.value}
                </dt>
                <dd className="m-0 mt-1 text-[13.5px] text-muted">{item.label}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-5 mb-0 text-[12px] text-muted">
            평가 하네스 실측값입니다 — 마스킹·판정은 커밋 e966b62, 검색은
            run_id 7(커밋 cc572b4) 기준이며 전부 로컬 기록 DB에 남아 있습니다.
          </p>
        </div>
      </div>
    </section>
  );
}
