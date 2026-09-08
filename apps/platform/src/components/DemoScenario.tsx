import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactElement,
  type ReactNode,
} from "react";
import {
  DEMO_DURATION_SEC,
  DEMO_LOOP_HOLD_MS,
  DEMO_PLAYBACK_RATE,
  DEMO_STEPS,
  DEMO_TURNS,
  type DemoSpeaker,
} from "../mock/demoScenario";

const MASK_FIELDS = [
  {
    masked: "봉은사로 **길 **호",
    plain: "봉은사로 12길 34호",
    field: "상세주소",
  },
  {
    masked: "봉은사로 **길 **",
    plain: "봉은사로 12길 34",
    field: "상세주소",
  },
  {
    masked: "010-****-6789",
    plain: "010-1234-6789",
    field: "전화번호",
  },
] as const;

type MaskField = (typeof MASK_FIELDS)[number];

function findNextMask(
  text: string,
): { at: number; field: MaskField } | null {
  let hit: { at: number; field: MaskField } | null = null;
  for (const field of MASK_FIELDS) {
    const at = text.indexOf(field.masked);
    if (at === -1) {
      continue;
    }
    if (hit === null || at < hit.at) {
      hit = { at, field };
    }
  }
  return hit;
}

function maskSpanId(turnAt: number, occurrence: number): string {
  return `${turnAt}:${occurrence}`;
}

function allMaskSpanIds(): string[] {
  const ids: string[] = [];
  for (const turn of DEMO_TURNS) {
    let remaining = turn.body;
    let occurrence = 0;
    while (remaining.length > 0) {
      const hit = findNextMask(remaining);
      if (hit === null) {
        break;
      }
      ids.push(maskSpanId(turn.at, occurrence));
      occurrence += 1;
      remaining = remaining.slice(hit.at + hit.field.masked.length);
    }
  }
  return ids;
}

function logMaskReveal(field: string, turnAt: number): void {
  console.info(
    `[열람 기록] ${field} 필드 열람 - ${formatClock(turnAt)} 시점`,
  );
}

function formatClock(seconds: number): string {
  const total = Math.max(0, Math.min(DEMO_DURATION_SEC, Math.floor(seconds)));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function stepIndexAt(seconds: number): number {
  let index = -1;
  for (let i = 0; i < DEMO_STEPS.length; i += 1) {
    if (DEMO_STEPS[i].at <= seconds) {
      index = i;
    }
  }
  return index;
}

function prefersReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function MaskedDemoText({
  body,
  turnAt,
  authorized,
  revealAll,
  openedIds,
  onToggle,
}: {
  body: string;
  turnAt: number;
  authorized: boolean;
  revealAll: boolean;
  openedIds: ReadonlySet<string>;
  onToggle: (
    id: string,
    field: string,
    currentlyOpen: boolean,
    turnAt: number,
  ) => void;
}): ReactNode {
  let remaining = body;
  const nodes: ReactNode[] = [];
  let occurrence = 0;
  while (remaining.length > 0) {
    const hit = findNextMask(remaining);
    if (hit === null) {
      nodes.push(remaining);
      break;
    }
    if (hit.at > 0) {
      nodes.push(remaining.slice(0, hit.at));
    }
    const id = maskSpanId(turnAt, occurrence);
    const open = authorized && (revealAll || openedIds.has(id));
    const className = open
      ? "rounded-sm bg-amber/30 px-1 py-0.5 font-medium text-fg ring-1 ring-amber/50"
      : "rounded-sm bg-mask px-1 py-0.5 font-medium";
    const label = `${hit.field.field}${open ? " 원문" : " 마스킹"}`;
    if (!authorized) {
      nodes.push(
        <span
          key={id}
          className={`${className} cursor-default`}
          data-mask-span={id}
          data-mask-open="false"
          data-mask-clickable="false"
        >
          {hit.field.masked}
        </span>,
      );
    } else {
      nodes.push(
        <button
          key={id}
          type="button"
          className={`${className} m-0 inline cursor-pointer border-0 p-0 align-baseline underline decoration-dotted decoration-amber/80 underline-offset-2 hover:bg-amber/20`}
          data-mask-span={id}
          data-mask-open={open ? "true" : "false"}
          data-mask-clickable="true"
          aria-pressed={open}
          aria-label={`${label} 열람 전환`}
          onClick={() => {
            onToggle(id, hit.field.field, open, turnAt);
          }}
        >
          {open ? hit.field.plain : hit.field.masked}
        </button>,
      );
    }
    occurrence += 1;
    remaining = remaining.slice(hit.at + hit.field.masked.length);
  }
  return nodes;
}

export function DemoScenario(): ReactElement {
  const rootRef = useRef<HTMLElement>(null);
  const timeRef = useRef(0);
  const playingRef = useRef(false);
  const rafRef = useRef(0);
  const lastTsRef = useRef(0);
  const holdUntilRef = useRef(0);
  const [time, setTime] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [authorized, setAuthorized] = useState(false);
  const [revealAll, setRevealAll] = useState(false);
  const [openedIds, setOpenedIds] = useState<ReadonlySet<string>>(
    () => new Set(),
  );
  const [includeOriginal, setIncludeOriginal] = useState(false);

  const toggleSpan = useCallback(
    (id: string, field: string, currentlyOpen: boolean, turnAt: number) => {
      if (!authorized) {
        return;
      }
      if (currentlyOpen) {
        if (revealAll) {
          setRevealAll(false);
          setOpenedIds(new Set(allMaskSpanIds().filter((key) => key !== id)));
        } else {
          setOpenedIds((current) => {
            const next = new Set(current);
            next.delete(id);
            return next;
          });
        }
        return;
      }
      setOpenedIds((current) => {
        const next = new Set(current);
        next.add(id);
        return next;
      });
      logMaskReveal(field, turnAt);
    },
    [authorized, revealAll],
  );

  const setClock = useCallback((next: number) => {
    const clipped = Math.max(0, Math.min(DEMO_DURATION_SEC, next));
    timeRef.current = clipped;
    setTime(clipped);
  }, []);

  const tick = useCallback(
    (ts: number) => {
      if (!playingRef.current) {
        return;
      }
      if (holdUntilRef.current > 0) {
        if (ts < holdUntilRef.current) {
          rafRef.current = window.requestAnimationFrame(tick);
          return;
        }
        holdUntilRef.current = 0;
        lastTsRef.current = ts;
        setClock(0);
        rafRef.current = window.requestAnimationFrame(tick);
        return;
      }
      if (lastTsRef.current === 0) {
        lastTsRef.current = ts;
      }
      const delta = ((ts - lastTsRef.current) / 1000) * DEMO_PLAYBACK_RATE;
      lastTsRef.current = ts;
      const next = timeRef.current + delta;
      if (next >= DEMO_DURATION_SEC) {
        setClock(DEMO_DURATION_SEC);
        holdUntilRef.current = ts + DEMO_LOOP_HOLD_MS;
        rafRef.current = window.requestAnimationFrame(tick);
        return;
      }
      setClock(next);
      rafRef.current = window.requestAnimationFrame(tick);
    },
    [setClock],
  );

  const play = useCallback(() => {
    if (playingRef.current) {
      return;
    }
    if (timeRef.current >= DEMO_DURATION_SEC) {
      setClock(0);
    }
    holdUntilRef.current = 0;
    playingRef.current = true;
    setPlaying(true);
    lastTsRef.current = 0;
    rafRef.current = window.requestAnimationFrame(tick);
  }, [setClock, tick]);

  const pause = useCallback(() => {
    playingRef.current = false;
    setPlaying(false);
    lastTsRef.current = 0;
    holdUntilRef.current = 0;
    if (rafRef.current !== 0) {
      window.cancelAnimationFrame(rafRef.current);
      rafRef.current = 0;
    }
  }, []);

  const jumpToStep = useCallback(
    (index: number) => {
      const clamped = Math.max(0, Math.min(DEMO_STEPS.length - 1, index));
      holdUntilRef.current = 0;
      setClock(DEMO_STEPS[clamped].at);
    },
    [setClock],
  );

  useEffect(() => {
    const node = rootRef.current;
    if (node === null) {
      return;
    }
    const reduced = prefersReducedMotion();
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry === undefined || !entry.isIntersecting) {
          pause();
          return;
        }
        if (!reduced) {
          play();
        }
      },
      { threshold: 0.35 },
    );
    observer.observe(node);
    return () => {
      observer.disconnect();
      pause();
    };
  }, [pause, play]);

  const activeIndex = stepIndexAt(time);
  const activeStep = activeIndex >= 0 ? DEMO_STEPS[activeIndex] : null;
  const visibleTurns = DEMO_TURNS.filter((turn) => turn.at <= time);

  return (
    <section id="realtime-assist" ref={rootRef} className="scroll-mt-[88px] bg-page px-5 pb-20">
      <div className="mx-auto max-w-[1180px]">
        <p className="mb-3 text-[13px] font-semibold text-amber">
          (a-2) 데모 시나리오
        </p>
        <h2 className="heading m-0 max-w-[18em] text-[clamp(26px,3.4vw,40px)] leading-snug tracking-tight">
          한 통의 전화에서,{" "}
          <span className="text-amber">AI는 이렇게 개입합니다</span>
        </h2>
        <p className="mt-4 max-w-[42em] text-[15px] leading-relaxed text-muted">
          도로 침수 민원 통화를 따라가 보세요. 대화가 진행될수록 AI가 각 순간에
          어떻게 돕는지 확인할 수 있습니다.
        </p>
        <div className="mt-10 grid grid-cols-1 gap-4 lg:grid-cols-[1.15fr_0.85fr] lg:items-stretch">
          <article className="flex min-h-0 flex-col rounded-[22px] border border-line bg-card p-5 lg:h-full">
            <div className="mb-4 flex items-center justify-between gap-3">
              <p className="m-0 flex items-center gap-2 text-[13px] font-semibold">
                <span
                  className={`h-2 w-2 rounded-full bg-live ${playing ? "anim-rec" : ""}`}
                  aria-hidden="true"
                />
                02-120 · 시연 통화 {formatClock(time)}
              </p>
              <div className="flex items-center gap-1">
                <ControlButton
                  label="이전 시점"
                  onClick={() => {
                    if (activeIndex <= 0) {
                      holdUntilRef.current = 0;
                      setClock(0);
                      return;
                    }
                    jumpToStep(activeIndex - 1);
                  }}
                >
                  ◀
                </ControlButton>
                <ControlButton
                  label={playing ? "일시정지" : "재생"}
                  onClick={() => {
                    if (playing) {
                      pause();
                    } else {
                      play();
                    }
                  }}
                >
                  {playing ? "⏸" : "▶"}
                </ControlButton>
                <ControlButton
                  label="다음 시점"
                  onClick={() => {
                    jumpToStep(
                      Math.min(DEMO_STEPS.length - 1, activeIndex + 1),
                    );
                  }}
                >
                  ▶
                </ControlButton>
              </div>
            </div>
            <div className="rounded-[14px] border border-line bg-page/50 px-4 py-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <p className="m-0 text-[13px] font-semibold">
                  개인정보 자동 감지 · 마스킹 적용 중
                </p>
                <p className="m-0 text-[12px] text-muted">
                  전화번호 2건 · 상세주소 2건
                </p>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  className="rounded-full border border-line px-3 py-1 text-[12px] text-fg"
                  aria-pressed={authorized}
                  onClick={() => {
                    setAuthorized(true);
                  }}
                >
                  권한 확인 (데모)
                </button>
                <button
                  type="button"
                  className="rounded-full border border-line px-3 py-1 text-[12px] text-fg disabled:opacity-40"
                  disabled={!authorized}
                  aria-pressed={revealAll}
                  onClick={() => {
                    if (revealAll) {
                      setRevealAll(false);
                      setOpenedIds(new Set());
                      return;
                    }
                    setRevealAll(true);
                  }}
                >
                  원문 보기
                </button>
              </div>
              <p className="mt-3 m-0 text-[12px] leading-relaxed text-muted">
                대화는 브라우저 안에서만 처리되는 시연 데이터이며 서버에
                저장·전송되지 않습니다. 실제 운영에서는 원문 열람이 역할 기반
                권한과 열람 기록으로 통제되어야 합니다.
              </p>
            </div>
            <ol className="mt-5 mb-0 flex flex-1 list-none flex-col gap-4 p-0">
              {visibleTurns.length === 0 ? (
                <li className="text-[13.5px] text-muted">
                  통화 연결을 기다리는 중…
                </li>
              ) : (
                visibleTurns.map((turn) => {
                  return (
                    <li
                      key={turn.at}
                      className="grid grid-cols-[auto_auto_1fr] items-start gap-x-2.5 text-[14px] leading-relaxed"
                    >
                      <span className="font-mono text-[12px] text-muted">
                        {formatClock(turn.at)}
                      </span>
                      <SpeakerAvatar speaker={turn.speaker} />
                      <p className="m-0">
                        <span className="mr-2 text-[12px] font-semibold text-muted">
                          {turn.speaker}
                        </span>
                        <MaskedDemoText
                          body={turn.body}
                          turnAt={turn.at}
                          authorized={authorized}
                          revealAll={revealAll}
                          openedIds={openedIds}
                          onToggle={toggleSpan}
                        />
                        {turn.translation !== undefined ? (
                          <span className="mt-2 block border-l-2 border-live pl-3 text-[13.5px] text-muted">
                            {turn.translation}
                          </span>
                        ) : null}
                      </p>
                    </li>
                  );
                })
              )}
            </ol>
          </article>
          <div className="flex min-h-0 flex-col justify-between gap-4 lg:h-full">
            <article className="rounded-[22px] border border-line bg-card p-5">
              {activeStep === null ? (
                <p className="m-0 text-[14px] text-muted">
                  발화가 시작되면 AI 개입이 이 자리에 나타납니다.
                </p>
              ) : (
                <>
                  <div className="flex items-center justify-between gap-3 text-[12.5px]">
                    <p className="m-0 font-semibold text-live">
                      {activeStep.label}
                    </p>
                    <p className="m-0 text-muted">
                      AI 개입 · {activeStep.clock}
                    </p>
                  </div>
                  <h3 className="mt-4 mb-3 text-[17px] font-semibold leading-snug">
                    {activeStep.title}
                  </h3>
                  <ul className="m-0 flex list-none flex-col gap-2 p-0 text-[13.5px] leading-relaxed text-muted">
                    {activeStep.points.map((point) => (
                      <li key={point}>{point}</li>
                    ))}
                  </ul>
                  {activeStep.footer !== null ? (
                    <p className="mt-4 mb-0 text-[12.5px] text-amber">
                      {activeStep.footer}
                    </p>
                  ) : null}
                  {activeStep.reportBox === true ? (
                    <ReportBox
                      authorized={authorized}
                      includeOriginal={includeOriginal}
                      onIncludeOriginal={setIncludeOriginal}
                    />
                  ) : null}
                </>
              )}
            </article>
            <article className="rounded-[22px] border border-line bg-card p-5">
              <h3 className="m-0 text-[14px] font-semibold">타임라인</h3>
              <ol className="mt-4 m-0 flex list-none flex-col gap-2 p-0">
                {DEMO_STEPS.map((step, index) => {
                  const current = index === activeIndex;
                  const done = index < activeIndex;
                  return (
                    <li key={step.clock}>
                      <button
                        type="button"
                        className={`flex w-full items-center justify-between rounded-[12px] px-3 py-2.5 text-left text-[13.5px] ${
                          current
                            ? "border border-amber/50 bg-amber/10 font-semibold text-fg"
                            : done
                              ? "text-fg"
                              : "text-muted"
                        }`}
                        onClick={() => {
                          jumpToStep(index);
                        }}
                      >
                        <span>
                          {step.clock} {step.label}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ol>
            </article>
          </div>
        </div>
      </div>
    </section>
  );
}

function ReportBox({
  authorized,
  includeOriginal,
  onIncludeOriginal,
}: {
  authorized: boolean;
  includeOriginal: boolean;
  onIncludeOriginal: (value: boolean) => void;
}): ReactElement {
  return (
    <div className="mt-4 rounded-[14px] border border-line bg-page/50 px-4 py-3">
      <p className="m-0 text-[13px] font-semibold">리포트 개인정보 보호</p>
      <p className="mt-2 mb-0 text-[13px] leading-relaxed text-muted">
        PDF는 기본적으로 전화번호·주소 등 식별 정보가 마스킹된 상태로
        생성됩니다.
      </p>
      <label className="mt-3 flex items-start gap-2 text-[12.5px] leading-relaxed text-muted">
        <input
          type="checkbox"
          className="mt-0.5"
          checked={includeOriginal}
          disabled={!authorized}
          onChange={(event) => {
            onIncludeOriginal(event.target.checked);
          }}
        />
        원문 포함해 생성 (권한이 확인된 사용자 전용, 위에서 권한 확인 필요)
      </label>
      <button
        type="button"
        className="mt-3 rounded-full bg-amber-fill px-4 py-2 text-[13px] font-semibold text-[#1a1408]"
      >
        PDF 리포트 다운로드
      </button>
    </div>
  );
}

function SpeakerAvatar({ speaker }: { speaker: DemoSpeaker }): ReactElement {
  return (
    <span
      className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full border border-line text-muted"
      aria-hidden="true"
    >
      {speaker === "시민" ? (
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <circle cx="12" cy="8" r="3.2" />
          <path d="M5.5 19c.8-3.2 3.2-5 6.5-5s5.7 1.8 6.5 5" />
        </svg>
      ) : (
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path d="M5 12v-1a7 7 0 0 1 14 0v1" />
          <path d="M5 12h2v5H5zM17 12h2v5h-2z" />
          <path d="M19 17H5" />
        </svg>
      )}
    </span>
  );
}

function ControlButton({
  label,
  onClick,
  children,
}: {
  label: string;
  onClick: () => void;
  children: ReactNode;
}): ReactElement {
  return (
    <button
      type="button"
      className="grid h-8 w-8 place-items-center rounded-full border border-line text-[12px] text-muted hover:text-fg"
      aria-label={label}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
