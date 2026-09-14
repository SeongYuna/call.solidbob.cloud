import { useEffect, useState, type ReactElement } from "react";
import {
  clearGatewayOverride,
  gatewayOverrideUrl,
  gatewayUrl,
} from "../lib/ws/types";

/**
 * `?gateway=` 런타임 오버라이드가 켜져 있는 동안 화면에 눈에 띄게 알린다
 * (2026-09-11 open-items 지적 — 조용히 다른 서버에 붙으면 상담원이 가짜
 * 자막·가짜 "필요서류" 카드를 실제 응답으로 믿을 수 있다). 어디에 붙었는지
 * 보여주고, 한 번에 해제할 수 있게 한다.
 */
export function GatewayOverrideBanner(): ReactElement | null {
  const [overrideUrl, setOverrideUrl] = useState<string | null>(null);

  useEffect(() => {
    gatewayUrl(); // ?gateway= 쿼리가 있으면 이 시점에 저장소로 반영된다
    setOverrideUrl(gatewayOverrideUrl());
  }, []);

  if (overrideUrl === null) {
    return null;
  }

  return (
    <div className="gateway-override-banner" role="status">
      <span className="gateway-override-text">
        ⚠ 라이브 게이트웨이에 연결됨 — <code>{overrideUrl}</code>
      </span>
      <button
        type="button"
        className="gateway-override-clear"
        onClick={() => {
          clearGatewayOverride();
          window.location.reload();
        }}
      >
        연결 해제
      </button>
    </div>
  );
}
