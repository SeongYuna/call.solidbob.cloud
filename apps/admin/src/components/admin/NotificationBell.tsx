import { useEffect, useRef, useState, type ReactElement } from "react";
import type { BlacklistRequestItem } from "../../types/blacklist";

/**
 * 알림 벨. 승인 대기 요청을 관리자가 놓치지 않게 헤더에 상시 노출한다.
 *
 * ⚠ 2026-09-10 — **실시간 푸시가 아니다.** 상담원 앱과 완전히 분리돼 있어
 * "상담원이 지금 막 보낸 요청"을 즉시 알 방법이 없다(웹소켓·백엔드 없음).
 * 지금은 이 페이지가 이미 갖고 있는 요청 목록(mock 시드 + 이 세션에서 처리한
 * 것)을 셀 뿐이다 — 백엔드가 붙으면 이 자리에 실시간 구독을 얹는다.
 */
export function NotificationBell({
  pendingRequests,
  onOpenRequest,
}: {
  pendingRequests: BlacklistRequestItem[];
  onOpenRequest: () => void;
}): ReactElement {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) {
      return;
    }

    function onPointerDown(event: PointerEvent): void {
      const root = rootRef.current;
      if (root === null || !(event.target instanceof Node)) {
        return;
      }
      if (!root.contains(event.target)) {
        setOpen(false);
      }
    }

    function onKeyDown(event: KeyboardEvent): void {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div className="notif-bell" ref={rootRef}>
      <button
        type="button"
        className="notif-bell-btn"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`알림 ${pendingRequests.length}건`}
        onClick={() => {
          setOpen((v) => !v);
        }}
      >
        <BellIcon />
        {pendingRequests.length > 0 ? (
          <span className="notif-bell-badge">{pendingRequests.length}</span>
        ) : null}
      </button>

      {open ? (
        <div className="notif-bell-menu" role="menu">
          <p className="notif-bell-title">승인 대기 요청</p>
          {pendingRequests.length === 0 ? (
            <p className="admin-empty notif-bell-empty">대기 중인 요청이 없습니다.</p>
          ) : (
            <ul className="notif-bell-list">
              {pendingRequests.map((request) => (
                <li key={request.request_id}>
                  <button
                    type="button"
                    role="menuitem"
                    className="notif-bell-item"
                    onClick={() => {
                      setOpen(false);
                      onOpenRequest();
                    }}
                  >
                    <span className="admin-ref">{request.display_hint}</span>
                    <span className="admin-meta">
                      {request.requested_by} · {relativeTime(request.requested_at)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  );
}

function relativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 1) {
    return "방금";
  }
  if (minutes < 60) {
    return `${minutes}분 전`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours}시간 전`;
  }
  return `${Math.floor(hours / 24)}일 전`;
}

function BellIcon(): ReactElement {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
      <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
    </svg>
  );
}
