import type { ReactElement } from "react";

const FEATURES = [
  {
    num: "01",
    title: "실시간 대화 분석",
    body: "말이 흐르는 속도로 핵심 민원·요청·이슈를 분리해 화면에 정리합니다.",
  },
  {
    num: "02",
    title: "서류·근거문서 추천",
    body: "민원 유형에 맞는 필요서류와 근거 조항을 그 자리에서 제시합니다.",
  },
  {
    num: "03",
    title: "컴플라이언스 감지",
    body: "부적절 표현·위반 단어를 감지하고 바로 대체 표현을 제안합니다.",
  },
  {
    num: "04",
    title: "정서 위기 알림",
    body: "욕설·위협·정서 위기 신호를 조기에 포착해 관리자에게 알립니다.",
  },
  {
    num: "05",
    title: "5개 언어 통번역",
    body: "외국인 고객과 5개 언어로 동시 통번역해 장벽 없이 소통합니다.",
  },
  {
    num: "06",
    title: "통화 후 자동 정리",
    body: "요약·유형분류·후속조치·지역자원 연계를 통화 종료 즉시 생성합니다.",
  },
] as const;

export function FeatureGrid(): ReactElement {
  return (
    <section id="features" className="scroll-mt-[88px] bg-page px-5 pb-20">
      <div className="mx-auto max-w-[1180px]">
        <p className="mb-3 text-[13px] font-semibold text-amber">(b) 6가지 기능</p>
        <h2 className="heading m-0 max-w-[14em] text-[clamp(26px,3.4vw,40px)] leading-snug tracking-tight">
          상담원 화면 위로 올라오는{" "}
          <span className="text-amber">조용한 도움</span>
        </h2>
        <ul className="mt-10 grid list-none grid-cols-1 gap-4 p-0 mid:grid-cols-3">
          {FEATURES.map((item) => (
            <li
              key={item.num}
              className="relative rounded-[22px] border border-line bg-card p-6"
            >
              <FeatureIcon index={item.num} />
              <p className="m-0 pr-8 text-[13px] font-semibold text-amber">
                {item.num} · {item.title}
              </p>
              <p className="mt-4 mb-0 text-[14.5px] leading-relaxed text-fg">
                {item.body}
              </p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function FeatureIcon({ index }: { index: string }): ReactElement {
  return (
    <svg
      className="absolute top-5 right-5 text-amber"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      aria-hidden="true"
    >
      {index === "01" ? (
        <path d="M4 6h16v9H8l-4 4V6Z" />
      ) : index === "02" ? (
        <path d="M7 3h8l5 5v13H7V3Z M15 3v5h5" />
      ) : index === "03" ? (
        <path d="M12 3 5 6v6c0 5 3.2 7.8 7 9 3.8-1.2 7-4 7-9V6l-7-3Z" />
      ) : index === "04" ? (
        <path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2 4 4 0 0 1 7 2c0 5.6-7 10-7 10Z" />
      ) : index === "05" ? (
        <>
          <circle cx="12" cy="12" r="9" />
          <path d="M3 12h18M12 3c3 3.2 3 14.8 0 18M12 3c-3 3.2-3 14.8 0 18" />
        </>
      ) : (
        <path d="M8 4h8v16H8zM8 9h8M8 14h8M11 4v16" />
      )}
    </svg>
  );
}
