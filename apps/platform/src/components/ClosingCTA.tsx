import type { ReactElement } from "react";

export function ClosingCTA(): ReactElement {
  return (
    <section id="cta" className="scroll-mt-[88px] bg-page px-5 pt-16 pb-8">
      <div className="mx-auto flex max-w-[760px] flex-col items-center text-center">
        <PhoneIcon />
        <h2 className="heading mt-4 m-0 text-[clamp(24px,3.2vw,36px)] leading-snug tracking-tight">
          상담원 한 분 한 분의{" "}
          <span className="text-amber">조용한 파트너로</span> 함께합니다
        </h2>
        <p className="mt-4 max-w-[36em] text-[15px] leading-relaxed text-muted">
          서울시 다산콜센터 현장에 꼭 맞는 도입 시나리오를 함께 설계합니다.
          데이터에 맞게 전용 AICC를 만들어 드릴 수 있습니다.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <a
            href="#cta"
            className="rounded-full bg-amber-fill px-5 py-2.5 text-[14px] font-semibold text-[#1a1408]"
          >
            도입 문의하기
          </a>
          <a
            href="#cta"
            className="rounded-full border border-line px-5 py-2.5 text-[14px] font-semibold text-fg"
          >
            운영팀에게 문의
          </a>
        </div>
      </div>
      <footer className="mx-auto mt-20 flex max-w-[1180px] flex-col gap-2 border-t border-line pt-6 text-[12.5px] text-muted mid:flex-row mid:items-center mid:justify-between">
        <p className="m-0">
          CallGuard · 서울시 다산콜센터 실시간 AI 어시스트
        </p>
        <p className="m-0">상담원을 돕는 조수 — 대체가 아닌 동반</p>
      </footer>
    </section>
  );
}

function PhoneIcon(): ReactElement {
  return (
    <span className="grid aspect-square h-6 w-6 shrink-0 place-items-center text-[#c9a576]">
      <svg
        viewBox="0 0 24 24"
        width={24}
        height={24}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="h-6 w-6 shrink-0"
        preserveAspectRatio="xMidYMid meet"
        aria-hidden="true"
      >
        <path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2" />
      </svg>
    </span>
  );
}
