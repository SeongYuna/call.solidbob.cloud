import { useEffect, useState, type ReactElement } from "react";
import {
  clearCallMediatorOverride,
  callMediatorOverrideUrl,
  callMediatorUrl,
} from "../lib/ws/types";

/**
 * `?call_mediator=` 런타임 오버라이드가 켜져 있는 동안 화면에 눈에 띄게 알린다
 * (2026-09-11 open-items 지적 — 조용히 다른 서버에 붙으면 상담원이 가짜
 * 자막·가짜 "필요서류" 카드를 실제 응답으로 믿을 수 있다). 어디에 붙었는지
 * 보여주고, 한 번에 해제할 수 있게 한다.
 */
export function CallMediatorOverrideBanner(): ReactElement | null {
  const [overrideUrl, setOverrideUrl] = useState<string | null>(null);

  useEffect(() => {
    callMediatorUrl(); // ?call_mediator= 쿼리가 있으면 이 시점에 저장소로 반영된다
    setOverrideUrl(callMediatorOverrideUrl());
  }, []);

  if (overrideUrl === null) {
    return null;
  }

  return (
    <div className="call-mediator-override-banner" role="status">
      <span className="call-mediator-override-text">
        ⚠ 라이브 콜 미디에이터에 연결됨 — <code>{overrideUrl}</code>
      </span>
      <button
        type="button"
        className="call-mediator-override-clear"
        onClick={() => {
          clearCallMediatorOverride();
          window.location.reload();
        }}
      >
        연결 해제
      </button>
    </div>
  );
}
