import { useState, type ReactElement } from "react";
import { useCallStore } from "../store/callStore";
import { ConfirmDialog } from "./ConfirmDialog";

interface BlackConsumerActionProps {
  callId: string;
}

/**
 * Requirement: C-6 확장. 욕설·폭언으로 통화가 길어진 고객을 상담원이 통화 종료 시
 * 직접 판단해 분류한다 — 자동 탐지가 아니다(부록 A-2, 판정은 사람이 한다).
 * 확인 즉시 관리자에게 알림을 보낸다(현재 mock — services/gateway 알림 API 없음).
 */
export function BlackConsumerAction({
  callId,
}: BlackConsumerActionProps): ReactElement {
  const flag = useCallStore((state) => state.blackConsumerFlag);
  const flagBlackConsumer = useCallStore((state) => state.flagBlackConsumer);
  const [confirming, setConfirming] = useState(false);

  return (
    <section className="wrapup-card">
      <div className="wrapup-card-head">
        <h3>고객 분류</h3>
      </div>
      {flag !== null ? (
        <>
          <span className="black-consumer-badge">
            <FlagIcon />
            블랙컨슈머로 분류됨 · 관리자에게 전송됨
          </span>
          <p className="black-consumer-note">
            상담원이 직접 분류했습니다. 자동 탐지가 아닙니다.
          </p>
        </>
      ) : (
        <>
          <p className="black-consumer-note">
            욕설·폭언이 반복되거나 통화가 비정상적으로 길어졌다면 분류할 수
            있습니다. 분류하면 관리자에게 즉시 알림이 전송됩니다.
          </p>
          <button
            type="button"
            className="btn-flag-risk"
            onClick={() => setConfirming(true)}
          >
            <FlagIcon />
            블랙컨슈머로 분류
          </button>
        </>
      )}
      {confirming ? (
        <ConfirmDialog
          title="블랙컨슈머로 분류하시겠습니까?"
          message="확인하면 관리자에게 즉시 알림이 전송됩니다. 이 분류는 상담원의 직접 판단으로 기록됩니다."
          confirmLabel="분류 및 알림 전송"
          cancelLabel="취소"
          onConfirm={() => {
            flagBlackConsumer(callId);
            setConfirming(false);
          }}
          onCancel={() => setConfirming(false)}
        />
      ) : null}
    </section>
  );
}

function FlagIcon(): ReactElement {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M5 21V4" />
      <path d="M5 4h11l-2 4 2 4H5" />
    </svg>
  );
}
