import { MockCallMediatorClient } from "../../mock/mockCallMediator";
import { RealCallMediatorClient } from "./realCallMediatorClient";
import { callMediatorUrl, isLiveCallMediatorConfigured } from "./types";
import type { CallMediatorClient } from "./types";

export type { CallMediatorClient, CallMediatorListener, CallMediatorMode, CallMediatorStatus } from "./types";
export { callMediatorUrl, isLiveCallMediatorConfigured } from "./types";

export function createCallMediatorClient(): CallMediatorClient {
  if (isLiveCallMediatorConfigured()) {
    return new RealCallMediatorClient(callMediatorUrl());
  }
  return new MockCallMediatorClient();
}
