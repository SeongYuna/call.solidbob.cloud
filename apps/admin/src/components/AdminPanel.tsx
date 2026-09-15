import {
  ClipboardCheck,
  History,
  Inbox,
  LayoutDashboard,
  SearchX,
  Settings as SettingsIcon,
  ShieldBan,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState, type ReactElement } from "react";
import { AuditLogTab } from "./admin/AuditLogTab";
import { EntriesTab } from "./admin/EntriesTab";
import { KnowledgeGapTab } from "./admin/KnowledgeGapTab";
import { NotificationBell } from "./admin/NotificationBell";
import { QaReviewTab } from "./admin/QaReviewTab";
import { RequestsTab } from "./admin/RequestsTab";
import { SettingsTab } from "./admin/SettingsTab";
import { WallboardTab } from "./admin/WallboardTab";
import { ThemeToggle } from "./ThemeToggle";
import { useAdminStore } from "../store/adminStore";

type Tab =
  | "wallboard"
  | "requests"
  | "entries"
  | "qa"
  | "gaps"
  | "audit"
  | "settings";

const TABS: { id: Tab; label: string }[] = [
  { id: "wallboard", label: "현황판" },
  { id: "requests", label: "승인요청" },
  { id: "entries", label: "블랙리스트" },
  { id: "qa", label: "QA 리뷰" },
  { id: "gaps", label: "지식베이스 갭" },
  { id: "audit", label: "감사 로그" },
  { id: "settings", label: "설정" },
];

/** 좌측 사이드바 아이콘 — 2026-09-15 상단 탭 → 좌측 아이콘 사이드바 전환. */
const TAB_ICONS: Record<Tab, LucideIcon> = {
  wallboard: LayoutDashboard,
  requests: Inbox,
  entries: ShieldBan,
  qa: ClipboardCheck,
  gaps: SearchX,
  audit: History,
  settings: SettingsIcon,
};

/**
 * 관리자 화면. J-3(승인요청창·블랙리스트 관리창, `_project/decisions/204`)에서
 * 출발했지만, 그 둘만으로는 "관리자가 볼 화면"이 아니라는 지적을 반영해
 * 다섯 개를 더했다 — 현황판·QA 리뷰 큐·지식베이스 갭·감사 로그·설정.
 *
 * ⚠ 다섯 개는 plan.md·decisions 어디에도 없는 **화면 설계 재량**이다(요구 ID
 * 없음). 전부 이미 있는 데이터를 다른 방식으로 보여줄 뿐, 새 판정·새 지표를
 * 만들지 않는다.
 *
 * 2026-09-10 — `apps/admin`으로 완전히 독립된 앱이다(포트 5174). 상담원
 * 대시보드(`apps/call`)와 번들·상태를 공유하지 않는다 — 지금은
 * `store/adminStore.ts`의 mock 시드로 시작하고, 실제 백엔드가 붙으면 그
 * 안쪽만 API 호출로 바꾼다.
 *
 * 2026-09-14 — `adminName`은 더 이상 mock(`mock/adminAuth.ts`)이 아니라 구글 로그인으로
 * 확인된 실제 관리자다(`App.tsx`가 `admin_auth` 세션에서 받아 내려준다).
 */
export function AdminPanel({
  adminName,
  onLogout,
}: {
  adminName: string;
  onLogout: () => void;
}): ReactElement {
  const status = useAdminStore((s) => s.status);
  const loadError = useAdminStore((s) => s.error);
  const loadAll = useAdminStore((s) => s.loadAll);
  const requests = useAdminStore((s) => s.requests);
  const entries = useAdminStore((s) => s.entries);
  const decide = useAdminStore((s) => s.decideRequest);
  const release = useAdminStore((s) => s.releaseEntry);
  const extend = useAdminStore((s) => s.extendEntry);
  const knowledgeGapLog = useAdminStore((s) => s.knowledgeGapLog);
  const callGuardTotal = useAdminStore((s) => s.callGuardTotal);
  const completedCallsTotal = useAdminStore((s) => s.completedCallsTotal);
  const veteranThresholdYears = useAdminStore((s) => s.veteranThresholdYears);
  const setVeteranThresholdYears = useAdminStore((s) => s.setVeteranThresholdYears);
  const blacklistExpiryMonths = useAdminStore((s) => s.blacklistExpiryMonths);
  const setBlacklistExpiryMonths = useAdminStore((s) => s.setBlacklistExpiryMonths);
  const [tab, setTab] = useState<Tab>("wallboard");
  const admin = adminName;

  useEffect(() => {
    void loadAll();
    // 로그인 직후 한 번만 — adminName이 바뀌는 것은 재로그인뿐이라 그때 다시 받는다.
  }, [loadAll, adminName]);

  const pendingRequests = requests.filter((r) => r.status === "pending");
  const pendingCount = pendingRequests.length;
  const activeEntryCount = entries.filter((e) => e.released_at === null).length;

  return (
    <main className="admin-page">
      <header className="admin-page-header">
        <div>
          <h2>관리자 화면</h2>
          {status === "error" ? (
            <p className="header-error" role="alert">
              데이터를 불러오지 못했습니다: {loadError}
              <button
                type="button"
                className="btn-outline"
                style={{ marginLeft: 8 }}
                onClick={() => {
                  void loadAll();
                }}
              >
                다시 시도
              </button>
            </p>
          ) : null}
        </div>
        <div className="wrapup-actions">
          <NotificationBell
            pendingRequests={pendingRequests}
            onOpenRequest={() => {
              setTab("requests");
            }}
          />
          <ThemeToggle />
          <button type="button" className="btn-outline" onClick={onLogout}>
            {admin} 로그아웃
          </button>
        </div>
      </header>

      <div className="admin-body">
        <nav className="admin-sidebar" aria-label="관리자 화면 전환">
          {TABS.map(({ id, label }) => {
            const Icon = TAB_ICONS[id];
            const count =
              id === "requests" ? pendingCount : id === "entries" ? activeEntryCount : 0;
            return (
              <button
                key={id}
                type="button"
                className={tab === id ? "admin-sidebar-item is-active" : "admin-sidebar-item"}
                onClick={() => {
                  setTab(id);
                }}
              >
                <span className="admin-sidebar-icon">
                  <Icon size={20} strokeWidth={2} aria-hidden="true" />
                  {count > 0 ? <span className="admin-sidebar-badge">{count}</span> : null}
                </span>
                <span className="admin-sidebar-label">{label}</span>
              </button>
            );
          })}
        </nav>

        <div className="admin-scroll">
          <div className="admin-content">
            {tab === "wallboard" ? (
              <WallboardTab
                completedCallsTotal={completedCallsTotal}
                callGuardTotal={callGuardTotal}
                pendingRequestCount={pendingCount}
                activeEntryCount={activeEntryCount}
              />
            ) : null}
            {tab === "requests" ? (
              <RequestsTab
                requests={requests}
                defaultExpiryMonths={blacklistExpiryMonths}
                onApprove={(requestId, expiryMonths) => {
                  void decide(requestId, true, admin, expiryMonths);
                }}
                onReject={(requestId) => {
                  void decide(requestId, false, admin);
                }}
              />
            ) : null}
            {tab === "entries" ? (
              <EntriesTab
                entries={entries}
                requests={requests}
                defaultExpiryMonths={blacklistExpiryMonths}
                onRelease={(entryId, reason) => {
                  void release(entryId, admin, reason);
                }}
                onExtend={(entryId, months, reason) => {
                  void extend(entryId, months, reason);
                }}
              />
            ) : null}
            {tab === "qa" ? <QaReviewTab /> : null}
            {tab === "gaps" ? <KnowledgeGapTab log={knowledgeGapLog} /> : null}
            {tab === "audit" ? (
              <AuditLogTab requests={requests} entries={entries} />
            ) : null}
            {tab === "settings" ? (
              <SettingsTab
                veteranThresholdYears={veteranThresholdYears}
                onChangeVeteranThresholdYears={setVeteranThresholdYears}
                blacklistExpiryMonths={blacklistExpiryMonths}
                onChangeBlacklistExpiryMonths={setBlacklistExpiryMonths}
              />
            ) : null}
          </div>
        </div>
      </div>
    </main>
  );
}
