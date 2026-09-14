import { useEffect, useState, type ReactElement } from "react";
import { LiveCallModal } from "./LiveCallModal";
import { captureLiveCallTokenFromUrl } from "../lib/liveCallToken";

export function Hero(): ReactElement {
  const [callOpen, setCallOpen] = useState(false);

  useEffect(() => {
    captureLiveCallTokenFromUrl();
  }, []);

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
        <IncomingCallCard
          onAnswer={() => {
            setCallOpen(true);
          }}
        />
      </div>
      {callOpen ? (
        <LiveCallModal
          onClose={() => {
            setCallOpen(false);
          }}
        />
      ) : null}
    </section>
  );
}

/**
 * 예전엔 "고객 전화가 온다"는 걸 흉내 낸 트리거였다. 2026-09-14 사용자 지시로
 * 방향을 뒤집었다 — 방문자가 상담원에게 직접 전화를 거는 흐름이다. 누르면
 * 실제 마이크·게이트웨이 배선이 붙은 팝업(LiveCallModal)이 뜬다. 팝업 자체는
 * 팀 전용 토큰이 있어야 실제로 연결된다 — 일반 방문자는 눌러도 안내만 본다.
 * 정사각형 박스 — aspect-square + 세로 flex 분배로 내용을 맞춘다(사용자 지시).
 * 글자 양에 맞춰 크기를 고정한다(270px) — 300px 는 폰트를 그대로 두니 속이 비어
 * 보였고, 240px 로 줄이며 폰트까지 같이 줄이니 이번엔 사이트 본문(16px) 대비
 * 상자 글자가 지나치게 작아 보였다(2026-09-14 사용자 지적 2건). 폰트는 원래
 * 크기 근처로 복원하고 박스만 그 사이 크기로 맞춘다.
 */
function IncomingCallCard({ onAnswer }: { onAnswer: () => void }): ReactElement {
  return (
    <article className="mx-auto flex aspect-square w-[270px] flex-col justify-between rounded-[20px] border border-line bg-card p-5 shadow-[0_24px_60px_rgba(0,0,0,0.28)]">
      <div>
        <div className="mb-3.5 flex items-center justify-between gap-2">
          <p className="m-0 flex items-center gap-1.5 text-[12.5px] font-semibold">
            <span className="anim-rec h-2 w-2 rounded-full bg-live" aria-hidden="true" />
            02-120 · 연결 대기
          </p>
          <p className="m-0 text-[12px] font-semibold text-amber">상담원 호출</p>
        </div>
        <p className="m-0 text-[14.5px] font-semibold leading-snug">
          지금 상담원에게 바로 전화를 걸어보세요.
        </p>
        <p className="mt-2 m-0 text-[13.5px] leading-snug text-muted">
          연결되면 상담원 화면에 실시간으로 뜨는 라이브 트랜스크립트·서류
          추천을 직접 확인할 수 있습니다.
        </p>
      </div>
      <button
        type="button"
        onClick={onAnswer}
        className="w-full rounded-full bg-amber-fill px-4 py-2.5 text-[14px] font-semibold text-[#1a1408]"
      >
        상담원에게 전화 걸기
      </button>
    </article>
  );
}
