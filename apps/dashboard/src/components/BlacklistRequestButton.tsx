import { useMemo, useState, type ReactElement } from "react";
import {
  abuseTotal,
  collectEvidence,
  hasDistress,
} from "../lib/blacklist/collectEvidence";
import { getMockAgentAccount } from "../mock/agentAuth";
import { useCallStore } from "../store/callStore";
import type { CallGuardFlag } from "../types/contract";

/**
 * J-1 — 통화 종료 화면의 「블랙리스트 전환 요청」 버튼.
 *
 * `_project/decisions/204`. **요청까지만 한다** — 상담원이 바로 등록할 수 없다.
 * 기분 상한 통화 한 건으로 고객이 영구히 표시되고, 그 판단을 검토한 사람이
 * 아무도 없게 되기 때문이다. 관리자 승인(J-4)을 반드시 거친다.
 */
export function BlacklistRequestButton({
  callId,
  customerRef,
  displayHint,
  callDurationS,
  contextExcerpt,
}: {
  callId: string;
  /** ⚠ **전화번호의 HMAC.** 평문이 아니다(`_project/decisions/205` ③). */
  customerRef: string;
  /** 화면 표시용(뒤 4자리 등). */
  displayHint: string;
  callDurationS: number;
  /** ⚠ **마스킹된 자막**이어야 한다. 원문을 넘기지 않는다 — DASAN-MANUAL-5.5 · C-5. */
  contextExcerpt: string;
}): ReactElement | null {
  const callGuard = useCallStore((s) => s.callGuard);
  const requests = useCallStore((s) => s.blacklistRequests);
  const submit = useCallStore((s) => s.submitBlacklistRequest);
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");

  const evidence = useMemo(
    () =>
      collectEvidence(Object.values(callGuard) as CallGuardFlag[], {
        callDurationS,
      }),
    [callGuard, callDurationS],
  );

  const alreadyRequested = requests.some(
    (r) => r.call_id === callId && r.status === "pending",
  );

  const abuse = abuseTotal(evidence);
  const distress = hasDistress(evidence);
  const minutes = Math.round(callDurationS / 60);

  if (alreadyRequested) {
    return (
      <p className="blacklist-note" role="status">
        이 통화의 전환 요청이 접수됐습니다 — 관리자 승인 대기 중입니다.
      </p>
    );
  }

  return (
    <div className="blacklist-request">
      {!open ? (
        <button
          type="button"
          className="btn-outline blacklist-open"
          onClick={() => {
            setOpen(true);
          }}
        >
          블랙리스트 전환 요청
        </button>
      ) : (
        <div className="wrapup-card blacklist-form">
          <h3>블랙리스트 전환 요청</h3>
          <p className="blacklist-help">
            요청은 <strong>관리자 승인</strong>을 거쳐야 적용됩니다. 승인되어도 전화는
            정상적으로 받으며, 바뀌는 것은 <strong>누구에게 배정되는가</strong> 하나입니다.
          </p>

          {/* ⚠ 위기 신호는 폭언과 다르게 다룬다 — DASAN-MANUAL-5.4.
              도움이 필요한 사람을 차단 대상으로 올리는 것은 정반대 방향이라
              요청을 막지는 않되 안내를 먼저 띄운다. */}
          {distress ? (
            <p className="blacklist-distress" role="alert">
              이 통화에는 <strong>위기 신호</strong>가 {evidence.distress_count}건
              감지됐습니다. 폭언과 다른 상황일 수 있습니다 — 전문 상담 기관 연결을
              먼저 검토해 주세요. 위기 신호는 전환 근거에 포함되지 않습니다.
            </p>
          ) : null}

          <dl className="blacklist-evidence">
            <div>
              <dt>통화 시간</dt>
              <dd>{minutes}분</dd>
            </div>
            <div>
              <dt>폭언·위협 탐지</dt>
              <dd>{abuse}건</dd>
            </div>
            <div>
              <dt>통화 온도 이상 구간</dt>
              <dd>{evidence.temperature_outliers}건</dd>
            </div>
          </dl>

          <label className="blacklist-reason">
            <span>요청 사유</span>
            <textarea
              value={reason}
              rows={3}
              placeholder="관리자가 통화를 다시 듣지 않고 판단할 수 있게 적어주세요"
              onChange={(event) => {
                setReason(event.target.value);
              }}
            />
          </label>

          <div className="blacklist-actions">
            <button
              type="button"
              className="btn-outline"
              onClick={() => {
                setOpen(false);
                setReason("");
              }}
            >
              취소
            </button>
            <button
              type="button"
              className="btn-replay"
              disabled={reason.trim().length === 0}
              onClick={() => {
                submit({
                  callId,
                  customerRef,
                  displayHint,
                  requestedBy: getMockAgentAccount().name,
                  reason: reason.trim(),
                  contextExcerpt,
                  evidence,
                });
                setOpen(false);
                setReason("");
              }}
            >
              요청 보내기
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
