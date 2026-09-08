import type { ReactElement } from "react";

export function Hero(): ReactElement {
  return (
    <section
      id="hero"
      className="relative overflow-hidden scroll-mt-[88px] bg-page px-5 pt-12 pb-20 mid:pt-16 mid:pb-24"
    >
      <div
        className="pointer-events-none absolute -top-24 right-0 h-[420px] w-[420px] rounded-full bg-[radial-gradient(circle,rgba(240,164,76,0.16),transparent_68%)]"
        aria-hidden="true"
      />
      <div className="relative mx-auto grid max-w-[1180px] grid-cols-1 items-center gap-12 mid:grid-cols-2">
        <div>
          <p className="mb-6 inline-flex items-center gap-2 rounded-full border border-amber/45 px-3 py-1.5 text-[12.5px] text-fg/90">
            <span
              className="anim-rec h-1.5 w-1.5 rounded-full bg-live"
              aria-hidden="true"
            />
            LIVE · 상담원 옆의 실시간 어시스트
          </p>
          <h1 className="heading m-0 max-w-[14em] text-[clamp(32px,4.6vw,52px)] leading-[1.28] tracking-tight">
            <span className="block font-[300]">사람을 대체하는 AI가 아닌,</span>
            <span className="block font-[500]">
              상담원 <span className="text-amber">옆에서</span> 듣고 돕는 AI
            </span>
          </h1>
          <p className="mt-6 max-w-[38em] text-[16px] leading-relaxed text-muted">
            CallGuard는 서울시 다산콜센터 상담원이 통화하는 순간, 대화 흐름을 함께
            읽어 필요한 서류·근거문서와 대체 표현을 조용히 건네는 현장
            파트너입니다.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <a
              href="#cta"
              className="rounded-full bg-amber-fill px-5 py-2.5 text-[14px] font-semibold text-[#1a1408]"
            >
              도입 문의하기
            </a>
            <a
              href="#realtime-assist"
              className="rounded-full border border-line px-5 py-2.5 text-[14px] font-semibold text-fg"
            >
              상담 데모 보기
            </a>
          </div>
          <p className="mt-10 text-[12.5px] text-muted">
            5개 언어 동시 통번역
            <span className="mx-2 text-line" aria-hidden="true">
              ·
            </span>
            통화 중 실시간
          </p>
        </div>
        <HeroCallCard />
      </div>
    </section>
  );
}

function HeroCallCard(): ReactElement {
  return (
    <article className="rounded-[22px] border border-line bg-card p-5 shadow-[0_24px_60px_rgba(0,0,0,0.28)]">
      <div className="mb-5 flex items-center justify-between gap-3">
        <p className="m-0 flex items-center gap-2 text-[13px] font-semibold">
          <span
            className="anim-rec h-2 w-2 rounded-full bg-live"
            aria-hidden="true"
          />
          02-120 · 통화 중 00:42
        </p>
        <p className="m-0 text-[12.5px] font-semibold text-amber">실시간</p>
      </div>
      <p className="m-0 text-[11.5px] font-semibold tracking-wide text-muted">
        라이브 트랜스크립트
      </p>
      <p className="mt-2 m-0 text-[14.5px] font-semibold leading-relaxed">
        “저희 지역 도서관 연장 이용 가능한지 확인하고 싶은데요.”
      </p>
      <p className="mt-2 m-0 text-[14px] leading-relaxed text-muted">
        “네, 도서를 지참하시면 즉시 연장 처리됩니다. ...”
      </p>
      <hr className="my-4 border-0 border-t border-line" />
      <div className="flex items-center justify-between gap-3">
        <p className="m-0 text-[11.5px] font-semibold tracking-wide text-muted">
          추천 · 민원 유형
        </p>
        <span className="rounded-md border border-line px-2 py-0.5 text-[11px] text-muted">
          도서관_연장
        </span>
      </div>
      <p className="mt-2 m-0 text-[14px] leading-relaxed">
        필요서류: 신분증 · 필요근거: 도서관 자율관리 3조
      </p>
      <hr className="my-4 border-0 border-t border-line" />
      <p className="m-0 text-[11.5px] font-semibold tracking-wide text-live">
        통번역 · EN / 日本語
      </p>
      <p className="mt-2 m-0 text-[14px] leading-relaxed text-amber">
        “Library extensions are available on-site with your ID.”
      </p>
    </article>
  );
}
