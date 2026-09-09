import {
  useRef,
  useState,
  type ReactElement,
} from "react";
import {
  DEMO_DOMAIN_LABELS,
  DEMO_DOMAINS,
  cardSourceType,
  type ClosureEvent,
  type DemoDomain,
} from "../types/contract";
import { DOMAIN_COLORS } from "../lib/domainColors";
import { evidenceHint } from "../lib/evidenceHints";
import { cardId, evidenceTally, useCallStore } from "../store/callStore";
import type { PanelCard } from "../store/callStore";
import { SessionControls } from "./AppHeader";
import {
  ArrowSelectChip,
  type ArrowSelectOption,
} from "./ArrowSelectChip";
import { BookmarkDock } from "./BookmarkDock";
import { CallHistoryPanel } from "./CallHistoryPanel";

type TermsContentView = "closure" | "popup";

const VIEW_OPTIONS: readonly ArrowSelectOption<TermsContentView>[] = [
  { value: "closure", label: "충족요건" },
  { value: "popup", label: "팝업창" },
];

const DOMAIN_OPTIONS: readonly ArrowSelectOption<DemoDomain>[] = DEMO_DOMAINS.map(
  (domain) => ({
    value: domain,
    label: DEMO_DOMAIN_LABELS[domain],
    color: DOMAIN_COLORS[domain],
  }),
);

function categoryFromDocId(docId: string): string {
  return docId.split("-")[0] ?? docId;
}

function cardDomId(index: number): string {
  return `term-card-${index}`;
}

function hasClosureType(item: PanelCard): boolean {
  return item.closure !== null && item.closure.closure_type.length > 0;
}

interface TermsPanelProps {
  onReplay: () => void;
  onEndCall: () => void;
}

export function TermsPanel({
  onReplay,
  onEndCall,
}: TermsPanelProps): ReactElement {
  const cards = useCallStore((state) => state.cards);
  const mode = useCallStore((state) => state.mode);
  const demoDomain = useCallStore((state) => state.demoDomain);
  const setDemoDomain = useCallStore((state) => state.setDemoDomain);
  const error = useCallStore((state) => state.error);
  const [view, setView] = useState<TermsContentView>("closure");
  const pending = cards.find((item) => item.closure !== null && !item.settled);
  const tally =
    pending?.closure !== undefined && pending.closure !== null
      ? evidenceTally(pending.closure)
      : null;

  const bodyRef = useRef<HTMLDivElement>(null);

  function jumpTo(index: number): void {
    const node = bodyRef.current?.querySelector(`#${cardDomId(index)}`);
    node?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  return (
    <section className="panel terms-panel" aria-labelledby="terms-heading">
      <header className="pane-header right-pane-header">
        <SessionControls onReplay={onReplay} onEndCall={onEndCall} />
        {error !== null ? <p className="header-error">{error}</p> : null}
      </header>
      <header className="panel-head terms-head">
        <h2 id="terms-heading" className="sr-only">
          이용약관 · 충족요건
        </h2>
        <div className="terms-chips">
          <ArrowSelectChip
            options={VIEW_OPTIONS}
            value={view}
            onChange={setView}
            aria-label="콘텐츠 보기"
          />
          {mode === "mock" ? (
            <ArrowSelectChip
              options={DOMAIN_OPTIONS}
              value={demoDomain}
              onChange={setDemoDomain}
              aria-label="도메인"
            />
          ) : null}
          <ArrowSelectChip label="상담기록" aria-label="상담기록">
            <CallHistoryPanel />
          </ArrowSelectChip>
        </div>
        {view === "closure" && tally !== null ? (
          <div className="tally-chip">
            <ProgressRing met={tally.met} total={tally.total} />
            <span>{`근거 ${tally.met}/${tally.total} 충족`}</span>
          </div>
        ) : null}
      </header>
      <div className="panel-body terms-body" ref={bodyRef}>
        {view === "popup" ? (
          cards.length === 0 ? (
            <p className="empty">관련 문서가 아직 없습니다.</p>
          ) : (
            <ul className="term-card-list">
              {cards.map((item, index) => (
                <li key={`${item.card.source.doc_id}-${item.card.title}`}>
                  <TermCard item={item} index={index} view="popup" />
                </li>
              ))}
            </ul>
          )
        ) : (
          <ClosureCardList cards={cards} />
        )}
      </div>
      <BookmarkDock onJump={jumpTo} />
    </section>
  );
}

/**
 * 충족요건 탭: closure_type 있는 카드만 그린다. 없는 카드는 「충족요건 없음」을
 * 개별 표시하지 않고 목록에서 뺀다. 여러 건이면 전부 보여 준다 — 「하나만」은
 * 빈 목록일 때 안내 문구를 하나로 합친다는 뜻이지, 카드를 1장으로 제한하는 게 아니다.
 */
function ClosureCardList({ cards }: { cards: PanelCard[] }): ReactElement {
  const linked = cards
    .map((item, index) => ({ item, index }))
    .filter(({ item }) => hasClosureType(item));

  if (linked.length === 0) {
    return (
      <p className="empty closure-panel-empty">
        충족요건이 필요한 처리가 아직 없습니다
      </p>
    );
  }

  return (
    <ul className="term-card-list">
      {linked.map(({ item, index }) => (
        <li key={`${item.card.source.doc_id}-${item.card.title}`}>
          <TermCard item={item} index={index} view="closure" />
        </li>
      ))}
    </ul>
  );
}

function TermCard({
  item,
  index,
  view,
}: {
  item: PanelCard;
  index: number;
  view: TermsContentView;
}): ReactElement | null {
  const settleClosure = useCallStore((state) => state.settleClosure);
  const toggleAdoption = useCallStore((state) => state.toggleAdoption);
  const adopted = useCallStore(
    (state) => state.adoptions[cardId(item.card)]?.adopted === true,
  );
  const category = categoryFromDocId(item.card.source.doc_id);
  const closure = item.closure;
  const manual = cardSourceType(item.card) === "manual";
  const canSettle =
    closure !== null && closure.missing.length === 0 && !item.settled;

  if (view === "closure" && !hasClosureType(item)) {
    return null;
  }

  function onAdopt(): void {
    toggleAdoption(item.card);
  }

  return (
    <article
      id={cardDomId(index)}
      className={`term-card${manual ? " manual" : ""}${adopted ? " adopted" : ""}`}
      data-category={category}
    >
      <div className="term-card-body">
        {view === "popup" || closure === null ? (
          <>
            <div className="card-head">
              <p className={`card-category cat-${category.toLowerCase()}`}>
                {category}
              </p>
              {manual ? <span className="card-flag">수동 검색</span> : null}
              <AdoptToggle adopted={adopted} onToggle={onAdopt} />
            </div>
            <h3>{item.card.title}</h3>
            <p className="card-summary">{item.card.summary}</p>
            <p className="card-source">
              <FileTextIcon />
              <span>{item.card.source.title}</span>
            </p>
          </>
        ) : (
          <>
            <h3>{item.card.title}</h3>
            <ClosureBlock
              closure={closure}
              canSettle={canSettle}
              category={category}
              onSettle={() => {
                settleClosure(closure.closure_type);
              }}
            />
          </>
        )}
      </div>
    </article>
  );
}

/**
 * 어떤 문서가 실제로 쓰였는지 남기는 기록. 지식베이스 보강용이지 상담원 평가가 아니라서
 * 누르지 않은 것을 문제처럼 보이게 하지 않는다 — 기본 상태는 조용한 회색이다.
 */
function AdoptToggle({
  adopted,
  onToggle,
}: {
  adopted: boolean;
  onToggle: () => void;
}): ReactElement {
  return (
    <button
      type="button"
      className={`adopt-toggle${adopted ? " on" : ""}`}
      aria-pressed={adopted}
      aria-label="사용 표시"
      title="사용 표시"
      onClick={onToggle}
    >
      <span className="adopt-box" aria-hidden="true">
        {adopted ? <CircleCheckIcon /> : null}
      </span>
      <span>사용 표시</span>
    </button>
  );
}

function ClosureBlock({
  closure,
  canSettle,
  category,
  onSettle,
}: {
  closure: ClosureEvent;
  canSettle: boolean;
  category: string;
  onSettle: () => void;
}): ReactElement {
  const keys = Object.keys(closure.evidence);
  const tally = evidenceTally(closure);

  return (
    <div className="closure-block">
      <h4 className="closure-subhead">종결 충족요건</h4>
      <div className={`tally-row cat-${category.toLowerCase()}`}>
        <ProgressRing met={tally.met} total={tally.total} />
        <p className="evidence-tally">{`근거 ${tally.total}건 중 ${tally.met}건 충족`}</p>
      </div>
      <ul className="evidence-list">
        {keys.map((key) => {
          const met = closure.evidence[key] === true;
          const hint = evidenceHint(key);
          const label = key.replace(/_/g, " ");
          return (
            <li key={key} className={met ? "met" : "missing"}>
              {met ? <CheckIcon /> : <CrossIcon />}
              <div className="evidence-copy">
                <p className="evidence-label">
                  <span>{label}</span>
                  {hint.clause !== null ? (
                    <span className="evidence-clause">{` — ${hint.clause}`}</span>
                  ) : null}
                </p>
                {met ? null : (
                  <p className="evidence-say">{`→ ${hint.say}`}</p>
                )}
              </div>
            </li>
          );
        })}
      </ul>
      {canSettle ? (
        <button type="button" className="btn-primary" onClick={onSettle}>
          종결 처리
        </button>
      ) : null}
    </div>
  );
}

function ProgressRing({
  met,
  total,
}: {
  met: number;
  total: number;
}): ReactElement {
  const size = 38;
  const stroke = 2.2;
  const radius = (size - stroke) / 2;
  const center = size / 2;
  const circumference = 2 * Math.PI * radius;
  const ratio = total === 0 ? 0 : met / total;
  const offset = circumference * (1 - ratio);

  return (
    <svg
      className={`progress-ring${met === total && total > 0 ? " is-complete" : ""}`}
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      aria-hidden="true"
    >
      <circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke="var(--line)"
        strokeWidth={stroke}
      />
      <circle
        className="progress-ring-arc"
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={stroke}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        transform={`rotate(-90 ${center} ${center})`}
      />
      <text
        x={center}
        y={center}
        textAnchor="middle"
        dominantBaseline="central"
        className="progress-ring-label"
      >
        {`${met}/${total}`}
      </text>
    </svg>
  );
}

function CircleCheckIcon(): ReactElement {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      aria-hidden="true"
    >
      <circle cx="8" cy="8" r="8" fill="currentColor" />
      <path
        d="M4.4 8.15 6.85 10.5 11.6 5.5"
        fill="none"
        stroke="#fff"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function FileTextIcon(): ReactElement {
  return (
    <svg
      className="source-icon"
      viewBox="0 0 16 16"
      width="14"
      height="14"
      aria-hidden="true"
    >
      <path
        d="M4.2 1.75h5.1L12.3 4.8v9.45H4.2V1.75Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
      <path
        d="M9.2 1.75V4.9h3.1M6 8.2h4.2M6 10.6h4.2"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function CheckIcon(): ReactElement {
  return (
    <svg
      className="evidence-icon"
      viewBox="0 0 16 16"
      width="14"
      height="14"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M3.4 8.2 6.5 11.1 12.6 4.8"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function CrossIcon(): ReactElement {
  return (
    <svg
      className="evidence-icon"
      viewBox="0 0 16 16"
      width="14"
      height="14"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M4.6 4.6l6.8 6.8M11.4 4.6l-6.8 6.8"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}
