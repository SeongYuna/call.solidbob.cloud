// Requirement: A-3 (브라우저 실시간 전달)
// apps/dashboard(realGatewayClient.ts)가 붙는 WebSocket. hub에서 받은
// TranscriptEventSchema JSON을 그대로 중계한다 — 여기서 모양을 바꾸지 않는다.
const clients = new Set();

export function registerDashboardClient(ws) {
  clients.add(ws);
  ws.on("close", () => {
    clients.delete(ws);
  });
  console.log(`[dashboardHub] 대시보드 연결 (${clients.size}개 접속 중)`);
}

export function broadcastToDashboard(payload) {
  const message = JSON.stringify(payload);
  for (const ws of clients) {
    if (ws.readyState === ws.OPEN) {
      ws.send(message);
    }
  }
}

export function dashboardClientCount() {
  return clients.size;
}
