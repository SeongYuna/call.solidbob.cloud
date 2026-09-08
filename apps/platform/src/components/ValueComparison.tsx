import type { ReactElement } from "react";

const LEGACY = [
  "통화가 끝난 뒤 녹취를 분석합니다.",
  "다음 날 요약 리포트로 결과를 제공합니다.",
  "놓친 민원·위반은 이미 지나간 이후입니다.",
] as const;

const LIVE = [
  "대화되는 즉시 흐름을 함께 읽습니다.",
  "필요한 서류·근거문서를 그 자리에서 건넵니다.",
  "정서 위기·위반 신호를 관리자에게 즉시 알립니다.",
] as const;

export function ValueComparison(): ReactElement {
  return (
    <section id="value" className="bg-page px-5 pb-20">
      <div className="mx-auto max-w-[1180px]">
        <p className="mb-3 text-[13px] font-semibold text-amber">(a) 핵심 가치</p>
        <h2 className="heading m-0 max-w-[16em] text-[clamp(26px,3.4vw,40px)] leading-snug tracking-tight">
          사후 처리가 아닌,{" "}
          <span className="text-amber">통화 중의 실시간 지원</span>
        </h2>
        <div className="mt-10 grid grid-cols-1 gap-4 mid:grid-cols-2">
          <article className="rounded-[22px] border border-line bg-card p-7">
            <h3 className="m-0 flex items-center gap-2 text-[15px] font-semibold text-muted">
              <span className="h-1.5 w-1.5 rounded-full bg-muted" aria-hidden="true" />
              기존 사후 처리 AI
            </h3>
            <ol className="mt-6 m-0 flex list-none flex-col gap-4 p-0">
              {LEGACY.map((line, index) => (
                <li key={line} className="flex gap-3 text-[15px] leading-relaxed text-muted">
                  <span className="font-semibold">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <span>{line}</span>
                </li>
              ))}
            </ol>
          </article>
          <article className="relative overflow-hidden rounded-[22px] border border-line bg-card p-7">
            <span
              className="absolute inset-x-0 top-0 h-[2px] bg-linear-to-r from-amber to-amber-fill"
              aria-hidden="true"
            />
            <h3 className="m-0 flex items-center gap-2 text-[15px] font-semibold text-amber">
              <span className="h-1.5 w-1.5 rounded-full bg-amber" aria-hidden="true" />
              CallGuard 실시간 어시스트
            </h3>
            <ol className="mt-6 m-0 flex list-none flex-col gap-4 p-0">
              {LIVE.map((line, index) => (
                <li key={line} className="flex gap-3 text-[15px] leading-relaxed">
                  <span className="font-semibold text-amber">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <span>{line}</span>
                </li>
              ))}
            </ol>
          </article>
        </div>
      </div>
    </section>
  );
}
