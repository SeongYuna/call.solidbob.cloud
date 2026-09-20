import { MockCallMediatorClient } from "../../mock/mockCallMediator";
import { readSharedCallId } from "../sharedCallId";
import { RealCallMediatorClient } from "./realCallMediatorClient";
import { callMediatorUrl, isLiveCallMediatorConfigured } from "./types";
import type { CallMediatorClient } from "./types";

export type { CallMediatorClient, CallMediatorListener, CallMediatorMode, CallMediatorStatus } from "./types";
export { callMediatorUrl, isLiveCallMediatorConfigured } from "./types";

export function createCallMediatorClient(): CallMediatorClient {
  if (isLiveCallMediatorConfigured()) {
    return new RealCallMediatorClient(subscriptionUrl(callMediatorUrl(), readSharedCallId()));
  }
  return new MockCallMediatorClient();
}

/**
 * `?call_id=` 로 열린 화면은 **그 통화만** 구독한다 — 콜 미디에이터의 `WS /ws?call_id=` 가 서버 쪽에서 걸러 준다.
 *
 * 전에는 통화를 가리지 않고 구독해 동시에 도는 두 통화의 자막이 한 화면에 섞였고, `segment_id` 가 통화마다 1 부터라
 * 서로의 줄을 덮어썼다(2026-09-17 왕복 테스트). 쿼리가 없으면 예전처럼 전부 받는다.
 * 주소를 못 읽으면 그대로 돌려준다 — 구독 자체를 깨뜨리지 않는다.
 */
export function subscriptionUrl(base: string, callId: string | null): string {
  if (callId === null || base.length === 0) {
    return base;
  }
  try {
    const url = new URL(base);
    url.searchParams.set("call_id", callId);
    return url.toString();
  } catch {
    return base;
  }
}
