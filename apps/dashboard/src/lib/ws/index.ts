import { MockGatewayClient } from "../../mock/mockGateway";
import { RealGatewayClient } from "./realGatewayClient";
import { gatewayUrl, isLiveGatewayConfigured } from "./types";
import type { GatewayClient } from "./types";

export type { GatewayClient, GatewayListener, GatewayMode, GatewayStatus } from "./types";
export { gatewayUrl, isLiveGatewayConfigured } from "./types";

export function createGatewayClient(): GatewayClient {
  if (isLiveGatewayConfigured()) {
    return new RealGatewayClient(gatewayUrl());
  }
  return new MockGatewayClient();
}
