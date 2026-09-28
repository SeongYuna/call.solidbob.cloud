import { useEffect, useState, type ReactElement } from "react";
import {
  clearCallMediatorOverride,
  callMediatorOverrideUrl,
  callMediatorUrl,
} from "../lib/ws/types";

/**
 * 주소에 실린 토큰 값을 `***` 로 가린다 — 이름에 `token` 이 든 쿼리 전부(`token`·
 * `agent_token`·`call_token` …). 배너는 시연 녹화 화면에 그대로 찍힌다. 다른 쿼리와
 * 호스트는 어디에 붙었는지 알아야 하므로 그대로 둔다.
 */
export function redactTokenInUrl(url: string): string {
  return url.replace(/([?&][^=&#]*token[^=&#]*=)[^&#]*/gi, "$1***");
}

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
    <CallMediatorOverrideBannerView
      url={overrideUrl}
      onClear={() => {
        clearCallMediatorOverride();
        window.location.reload();
      }}
    />
  );
}

/** 배너 표시부. 주소는 여기서 가려서 그린다 — 호출부가 가리는 것을 잊어도 새지 않게. */
export function CallMediatorOverrideBannerView({
  url,
  onClear,
}: {
  url: string;
  onClear: () => void;
}): ReactElement {
  return (
    <div className="call-mediator-override-banner" role="status">
      <span className="call-mediator-override-text">
        ⚠ 라이브 콜 미디에이터에 연결됨 — <code>{redactTokenInUrl(url)}</code>
      </span>
      <button
        type="button"
        className="call-mediator-override-clear"
        onClick={onClear}
      >
        연결 해제
      </button>
    </div>
  );
}
