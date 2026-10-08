// Requirement: C-6
/**
 * C-6 베타 — 폭언 대응 단계 표시(`decisions/221`, 티켓 `w8-c6-intervention-overlay-ui`).
 *
 * - `warning`·`final_warning`: `pause_ms` 동안 상담 영역 위에 「일시정지 — 고객 안내 중」 덮개 +
 *   고객 안내 문구 + 브라우저 음성 읽기(`ko-KR`). 끝나면 걷고 「상담을 이어가세요」.
 * - `end_suggested`: 덮개 없이 권고 배너만. **종료 버튼·자동 동작을 만들지 않는다** — 종료는 상담원이 정한다(5.2).
 *
 * 지켜야 할 것:
 * - 모든 표시에 「베타」 — 탐지 성능은 측정 불가다(`221` 5절).
 * - 덮개는 화면만 가린다. 자막·추천은 그 아래에서 계속 쌓이고, 상담원이 언제든 닫을 수 있다.
 * - 안내 음성은 **상담원 PC 에서만** 나온다(고객 송출은 교환기 연동 — `w8-c6-intervention-telephony`).
 *   그래서 「고객에게 안내했습니다」라고 쓰지 않는다.
 * - 위험 고객·점수·퍼센트 표현 없음(부록 A-1). 안내 문구는 미디에이터 고정 문안을 그대로 쓴다.
 */
import { useEffect, useState, type ReactElement } from "react";
import { useCallStore } from "../store/callStore";
import type { CallGuardIntervention } from "../types/contract";

/** 「상담을 이어가세요」를 띄워 두는 시간. 실측 값이 아니라 읽을 틈을 주는 표시용 값이다. */
const RESUME_NOTICE_MS = 4000;
const TICK_MS = 250;

const STAGE_ORDINAL: Record<"warning" | "final_warning", string> = {
  warning: "1차",
  final_warning: "2차",
};

function BetaTag(): ReactElement {
  return <span className="c6-beta-tag">베타</span>;
}

export function CallGuardPauseOverlayView({
  intervention,
  remainingSeconds,
  onDismiss,
}: {
  intervention: CallGuardIntervention;
  remainingSeconds: number;
  onDismiss: () => void;
}): ReactElement | null {
  if (intervention.stage === "end_suggested" || intervention.announcement === null) {
    return null;
  }
  return (
    <div className="c6-pause-overlay" role="dialog" aria-modal="false" aria-label="일시정지 — 고객 안내 중">
      <div className="c6-pause-box">
        <p className="c6-pause-title">
          <BetaTag />
          일시정지 — 고객 안내 중 ({STAGE_ORDINAL[intervention.stage]})
        </p>
        <p className="c6-pause-label">고객 안내 문구</p>
        <p className="c6-pause-announcement">{intervention.announcement}</p>
        <p className="c6-pause-meta">
          안내 음성은 이 PC 에서만 재생됩니다 · 근거 {intervention.source_doc_id} · {remainingSeconds}초 뒤 걷힙니다
        </p>
        <p className="c6-pause-meta">자막은 이 덮개 아래에서 계속 쌓이고 있습니다.</p>
        <button type="button" className="c6-pause-dismiss" onClick={onDismiss}>
          덮개 닫기
        </button>
      </div>
    </div>
  );
}

export function CallGuardEndSuggestionBannerView({
  intervention,
  onDismiss,
}: {
  intervention: CallGuardIntervention;
  onDismiss: () => void;
}): ReactElement {
  return (
    <p className="c6-end-banner" role="alert">
      <BetaTag />
      <span>
        매뉴얼 5.1·5.2 — 통화 종료를 판단할 수 있습니다. 종료 여부는 상담원이 정합니다
        <span className="c6-end-source">{` (${intervention.source_doc_id})`}</span>
      </span>
      <button type="button" className="agent-call-dismiss" aria-label="권고 닫기" onClick={onDismiss}>
        ✕
      </button>
    </p>
  );
}

function speak(text: string): void {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) {
    return;
  }
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "ko-KR";
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

function stopSpeaking(): void {
  if (typeof window !== "undefined" && "speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
}

export function CallGuardInterventionLayer(): ReactElement | null {
  const pause = useCallStore((state) => state.callGuardPause);
  const endSuggestion = useCallStore((state) => state.callGuardEndSuggestion);
  const dismissPause = useCallStore((state) => state.dismissCallGuardPause);
  const dismissEndSuggestion = useCallStore((state) => state.dismissCallGuardEndSuggestion);
  const [now, setNow] = useState(() => Date.now());
  const [resumeVisible, setResumeVisible] = useState(false);

  // 새 덮개마다 안내 문구를 한 번 읽는다. 덮개가 걷히면(닫기·시간 끝·새 통화) 읽기도 멈춘다.
  const announcement = pause?.intervention.announcement ?? null;
  const pauseKey = pause === null ? null : `${pause.intervention.segment_id}:${pause.intervention.stage}`;
  useEffect(() => {
    if (pauseKey === null || announcement === null) {
      return;
    }
    setResumeVisible(false);
    speak(announcement);
    return stopSpeaking;
  }, [pauseKey, announcement]);

  // 남은 시간을 세다가 끝나면 걷고 「상담을 이어가세요」.
  const endsAt = pause?.endsAt ?? null;
  useEffect(() => {
    if (endsAt === null) {
      return;
    }
    setNow(Date.now());
    const timer = window.setInterval(() => {
      const current = Date.now();
      setNow(current);
      if (current >= endsAt) {
        window.clearInterval(timer);
        dismissPause();
        setResumeVisible(true);
      }
    }, TICK_MS);
    return () => {
      window.clearInterval(timer);
    };
  }, [endsAt, dismissPause]);

  useEffect(() => {
    if (!resumeVisible) {
      return;
    }
    const timer = window.setTimeout(() => {
      setResumeVisible(false);
    }, RESUME_NOTICE_MS);
    return () => {
      window.clearTimeout(timer);
    };
  }, [resumeVisible]);

  // 종료 권고가 오면 「이어가세요」는 맞지 않는다 — 걷는다.
  const showResume = resumeVisible && endSuggestion === null && pause === null;

  return (
    <>
      {pause !== null ? (
        <CallGuardPauseOverlayView
          intervention={pause.intervention}
          remainingSeconds={Math.max(0, Math.ceil((pause.endsAt - now) / 1000))}
          onDismiss={() => {
            dismissPause();
            setResumeVisible(true);
          }}
        />
      ) : null}
      {endSuggestion !== null ? (
        <CallGuardEndSuggestionBannerView intervention={endSuggestion} onDismiss={dismissEndSuggestion} />
      ) : null}
      {showResume ? (
        <p className="c6-resume-notice" role="status">
          <BetaTag />
          상담을 이어가세요
        </p>
      ) : null}
    </>
  );
}
