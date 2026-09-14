import { useEffect, useRef, useState, type ReactElement } from "react";
import { BrandLockup } from "./AppHeader";
import { CallHistoryPanel } from "./CallHistoryPanel";
import { CallVolumeChart } from "./CallVolumeChart";
import { KpiCard } from "./KpiCard";
import { ThemeToggle } from "./ThemeToggle";
import {
  MOCK_HOURLY_VOLUME,
  MOCK_STANDBY_KPI,
} from "../mock/standbyKpi";

interface AgentStandbyScreenProps {
  agentName: string;
  onStartCall: () => void;
  onResetPassword: () => void;
}

export function AgentStandbyScreen({
  agentName,
  onStartCall,
  onResetPassword,
}: AgentStandbyScreenProps): ReactElement {
  const [now, setNow] = useState(() => new Date());
  const [menuOpen, setMenuOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const id = window.setInterval(() => {
      setNow(new Date());
    }, 30_000);
    return () => {
      window.clearInterval(id);
    };
  }, []);

  useEffect(() => {
    if (!menuOpen) {
      return;
    }

    function onPointerDown(event: PointerEvent): void {
      const root = profileRef.current;
      if (root === null || !(event.target instanceof Node)) {
        return;
      }
      if (!root.contains(event.target)) {
        setMenuOpen(false);
      }
    }

    function onKeyDown(event: KeyboardEvent): void {
      if (event.key === "Escape") {
        setMenuOpen(false);
      }
    }

    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [menuOpen]);

  const initial = agentName.slice(0, 1);

  return (
    <main className="standby">
      <header className="standby-top">
        <div className="standby-hello">
          <BrandLockup />
          <div>
            <h1 className="standby-greeting">{`안녕하세요, ${agentName}님`}</h1>
            <p className="standby-clock">
              <time dateTime={now.toISOString()}>{formatStandbyNow(now)}</time>
            </p>
          </div>
        </div>
        <div className="standby-aside">
          <div className="standby-profile" ref={profileRef}>
            <button
              type="button"
              className="standby-avatar"
              aria-haspopup="menu"
              aria-expanded={menuOpen}
              aria-label={`${agentName} 계정 메뉴`}
              onClick={() => {
                setMenuOpen((open) => !open);
              }}
            >
              {initial}
            </button>
            <span className="standby-agent">{agentName}</span>
            {menuOpen ? (
              <div className="standby-profile-menu" role="menu">
                <button
                  type="button"
                  role="menuitem"
                  className="standby-reset-pw"
                  onClick={() => {
                    setMenuOpen(false);
                    onResetPassword();
                  }}
                >
                  비밀번호 재설정
                </button>
              </div>
            ) : null}
          </div>
          <ThemeToggle />
          <button
            type="button"
            className="btn-primary btn-start-call"
            onClick={onStartCall}
          >
            통화 시작
          </button>
        </div>
      </header>

      <section className="standby-metrics" aria-label="오늘 현황">
        <p className="wrapup-note standby-kpi-note">
          아래 숫자와 그래프는 디자인 목업입니다. 실측값이 아닙니다.
        </p>
        <div className="standby-kpi">
          {MOCK_STANDBY_KPI.map((item) => (
            <KpiCard
              key={item.label}
              label={item.label}
              value={item.value}
              variant={item.variant}
            />
          ))}
        </div>
        <CallVolumeChart points={MOCK_HOURLY_VOLUME} />
      </section>

      <section className="standby-history wrapup-card">
        <CallHistoryPanel
          onReplay={onStartCall}
          variant="page"
          returnTo="standby"
        />
      </section>
    </main>
  );
}

function formatStandbyNow(date: Date): string {
  const weekdays = ["일", "월", "화", "수", "목", "금", "토"] as const;
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  const hh = String(date.getHours()).padStart(2, "0");
  const mm = String(date.getMinutes()).padStart(2, "0");
  return `${y}.${m}.${d} (${weekdays[date.getDay()]}) ${hh}:${mm}`;
}
