// Requirement: F-3
/**
 * 「통화받기」 모달 안의 고객 브리핑 카드(`decisions/220`, 티켓 `w8-f3-briefing-card-ui`).
 *
 * - 목적은 AI 의 **추정**이다 — 「추정 통화 목적」 꼬리표를 지우지 않는다(절대 원칙 9).
 * - 제목은 「같은 번호로 걸려 온 지난 통화」 — 가족이 같은 번호를 쓸 수 있어 「이 고객의」라고 단정하지 않는다.
 * - 서버가 준 문장과 사실만 그린다. 「위험 고객」·「요주의」·퍼센트·신뢰도 숫자를 만들지 않는다(부록 A-1).
 * - 고객 번호·ID 는 서버도 주지 않고 여기서도 만들지 않는다(`decisions/304`·`322`).
 */
import type { ReactElement } from "react";
import type { CustomerBriefing } from "../lib/api/coreClient";
import type { BriefingState } from "../hooks/useCustomerBriefing";

/** 콜 가드 범주 → 지난 통화의 **사실** 문장. 고객을 규정하는 말은 쓰지 않는다. */
const CALL_GUARD_FACTS: Record<string, string> = {
  insult: "지난 통화에서 욕설·모욕 경고가 있었습니다",
  threat: "지난 통화에서 협박성 발언 경고가 있었습니다",
  sexual: "지난 통화에서 성적 표현 경고가 있었습니다",
  distress: "지난 통화에서 위기 신호 안내가 있었습니다",
};

function formatMonthDay(iso: string): string {
  const date = new Date(iso);
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  return `${mm}-${dd}`;
}

function signalLines(briefing: CustomerBriefing): string[] {
  const lines: string[] = [];
  const { openFollowUps, blacklisted, callGuardCategories } = briefing.signals;
  if (openFollowUps > 0) {
    lines.push(`마치지 않은 후속조치 ${openFollowUps}건`);
  }
  if (blacklisted) {
    lines.push("블랙리스트 적용 중");
  }
  for (const category of new Set(callGuardCategories)) {
    const fact = CALL_GUARD_FACTS[category];
    if (fact !== undefined) {
      lines.push(fact);
    }
  }
  return lines;
}

function ReadyCard({ briefing }: { briefing: CustomerBriefing }): ReactElement {
  const { purpose, briefingLines, evidence } = briefing;
  const signals = signalLines(briefing);
  return (
    <>
      <p className="briefing-title">
        같은 번호로 걸려 온 지난 통화
        <span className="briefing-count">{briefing.priorCallCount}건</span>
      </p>

      {purpose !== null ? (
        <div className="briefing-purpose">
          <p className="briefing-purpose-head">
            <span className="briefing-tag">추정 통화 목적</span>
            {purpose.source === "rule" ? <span className="briefing-source">규칙 요약</span> : null}
            {purpose.category !== null ? (
              <span className="briefing-category">{purpose.category}</span>
            ) : null}
          </p>
          <p className="briefing-purpose-text">{purpose.text}</p>
        </div>
      ) : null}

      {briefingLines.length > 0 ? (
        <ul className="briefing-lines">
          {briefingLines.map((line, index) => (
            <li key={index}>{line}</li>
          ))}
        </ul>
      ) : null}

      {evidence.length > 0 ? (
        <p className="briefing-evidence">
          <span className="briefing-label">근거</span>
          {evidence.map((item) => (
            <span key={item.callId} className="briefing-evidence-item">
              {formatMonthDay(item.startedAt)} · {item.inquiryType ?? "유형 미분류"}
              {item.summaryConfirmed ? null : <span className="briefing-draft">초안</span>}
            </span>
          ))}
        </p>
      ) : null}

      {signals.length > 0 ? (
        <ul className="briefing-signals">
          {signals.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      ) : null}
    </>
  );
}

export function CustomerBriefingCard({ state }: { state: BriefingState }): ReactElement | null {
  if (state === null) {
    return null;
  }
  return (
    <section className="briefing-card" aria-label="고객 브리핑" aria-live="polite">
      {state === "loading" ? (
        <p className="briefing-note">브리핑 준비 중…</p>
      ) : state.status === "first_contact" ? (
        <p className="briefing-note">같은 번호로 걸려 온 지난 통화가 없습니다 — 첫 문의로 보입니다</p>
      ) : state.status === "unidentified" ? (
        <p className="briefing-note">발신 번호를 확인할 수 없어 지난 통화를 찾지 않았습니다</p>
      ) : (
        <ReadyCard briefing={state} />
      )}
    </section>
  );
}
