import { useState, type ReactElement } from "react";
import { ConfirmDialog } from "./ConfirmDialog";

interface StandbyBackButtonProps {
  liveInProgress: boolean;
  onLeave: () => void;
}

export function StandbyBackButton({
  liveInProgress,
  onLeave,
}: StandbyBackButtonProps): ReactElement {
  const [ask, setAsk] = useState(false);

  return (
    <>
      <button
        type="button"
        className="btn-outline standby-back"
        onClick={() => {
          if (liveInProgress) {
            setAsk(true);
            return;
          }
          onLeave();
        }}
      >
        <BackArrowIcon />
        대기화면
      </button>
      {ask ? (
        <ConfirmDialog
          title="대기화면으로 이동"
          message="통화가 진행 중입니다. 대기화면으로 이동하면 실시간 어시스트가 중단됩니다. 이동하시겠습니까?"
          confirmLabel="이동"
          cancelLabel="취소"
          onCancel={() => {
            setAsk(false);
          }}
          onConfirm={() => {
            setAsk(false);
            onLeave();
          }}
        />
      ) : null}
    </>
  );
}

function BackArrowIcon(): ReactElement {
  return (
    <svg
      className="btn-outline-icon"
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
      <path d="M15 6 9 12l6 6" />
    </svg>
  );
}
