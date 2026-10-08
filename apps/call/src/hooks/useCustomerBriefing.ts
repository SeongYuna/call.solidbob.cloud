// Requirement: F-3
/**
 * 「통화받기」 전 고객 브리핑을 통화당 한 번 부른다(`decisions/220`, 티켓 `w8-f3-briefing-card-ui`).
 *
 * 부르는 시점은 콜 미디에이터의 `started`(`{call_id}`)다 — 그게 `callStore.callId` 를 채운다.
 * 새 WS 메시지는 없다. 실패(404·네트워크·형식 어긋남·시간 초과)는 전부 `null` 로 접어
 * 카드를 그리지 않는다 — 브리핑은 보조 정보라 「통화받기」를 막거나 오류 배너를 띄우지 않는다.
 */
import { useEffect, useState } from "react";
import {
  fetchCustomerBriefing,
  isCoreApiConfigured,
  type CustomerBriefing,
} from "../lib/api/coreClient";
import { briefingPreviewValue, type BriefingPreview } from "../mock/customerBriefing";

/** `"loading"` 은 응답 대기, `null` 은 카드 없음. */
export type BriefingState = CustomerBriefing | null | "loading";

/**
 * 서버는 모델 상한 10초를 넘기면 규칙 브리핑으로 답한다. 그보다 넉넉히 기다리고
 * 그래도 안 오면 카드를 접는다 — 「준비 중」이 영원히 남지 않게.
 */
const BRIEFING_TIMEOUT_MS = 15_000;

const UNMOUNT = "unmount";

export function useCustomerBriefing(
  callId: string | null,
  preview: BriefingPreview | null,
): BriefingState {
  const live = preview === null && callId !== null && isCoreApiConfigured();
  const [fetched, setFetched] = useState<{ callId: string; value: BriefingState } | null>(null);

  useEffect(() => {
    if (!live || callId === null) {
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      controller.abort();
    }, BRIEFING_TIMEOUT_MS);
    setFetched({ callId, value: "loading" });
    fetchCustomerBriefing(callId, controller.signal)
      .then((briefing) => {
        setFetched({ callId, value: briefing });
      })
      .catch(() => {
        // 언마운트·통화 바뀜으로 끊긴 요청은 상태를 건드리지 않는다. 시간 초과·실패만 카드를 접는다.
        if (controller.signal.reason !== UNMOUNT) {
          setFetched({ callId, value: null });
        }
      })
      .finally(() => {
        window.clearTimeout(timer);
      });
    return () => {
      window.clearTimeout(timer);
      controller.abort(UNMOUNT);
    };
  }, [live, callId]);

  if (preview !== null) {
    return briefingPreviewValue(preview);
  }
  if (!live || fetched === null || fetched.callId !== callId) {
    return live ? "loading" : null;
  }
  return fetched.value;
}
