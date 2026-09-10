import { useState, type ReactElement } from "react";
import { AuditLogTab } from "./admin/AuditLogTab";
import { EntriesTab } from "./admin/EntriesTab";
import { KnowledgeGapTab } from "./admin/KnowledgeGapTab";
import { NotificationBell } from "./admin/NotificationBell";
import { QaReviewTab } from "./admin/QaReviewTab";
import { RequestsTab } from "./admin/RequestsTab";
import { SettingsTab } from "./admin/SettingsTab";
import { WallboardTab } from "./admin/WallboardTab";
import { getMockAdminAccount } from "../mock/adminAuth";
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
 * 대시보드(`apps/dashboard`)와 번들·상태를 공유하지 않는다 — 지금은
 * `store/adminStore.ts`의 mock 시드로 시작하고, 실제 백엔드가 붙으면 그
 * 안쪽만 API 호출로 바꾼다.
 */
export function AdminPanel({
  onExit,
}: {
  onExit: () => void;
}): ReactElement {
  const requests = useAdminStore((s) => s.requests);
  const entries = useAdminStore((s) => s.entries);
  const decide = useAdminStore((s) => s.decideRequest);
  const release = useAdminStore((s) => s.releaseEntry);
  const extend = useAdminStore((s) => s.extendEntry);
  const knowledgeGapLog = useAdminStore((s) => s.knowledgeGapLog);
  const callGuardLog = useAdminStore((s) => s.callGuardLog);
  const completedCallsTotal = useAdminStore((s) => s.completedCallsTotal);
  const veteranThresholdYears = useAdminStore((s) => s.veteranThresholdYears);
  const setVeteranThresholdYears = useAdminStore((s) => s.setVeteranThresholdYears);
  const blacklistExpiryMonths = useAdminStore((s) => s.blacklistExpiryMonths);
  const setBlacklistExpiryMonths = useAdminStore((s) => s.setBlacklistExpiryMonths);
  const [tab, setTab] = useState<Tab>("wallboard");
  const admin = getMockAdminAccount().name;

  const pendingRequests = requests.filter((r) => r.status === "pending");
  const pendingCount = pendingRequests.length;
  const activeEntryCount = entries.filter((e) => e.released_at === null).length;

  return (
    <main className="admin-page">
      <header className="admin-page-header">
        <div>
          <h2>관리자 화면</h2>
        </div>
        <div className="wrapup-actions">
          <NotificationBell
            pendingRequests={pendingRequests}
            onOpenRequest={() => {
              setTab("requests");
            }}
          />
          <button type="button" className="btn-outline" onClick={onExit}>
            상담 화면으로
          </button>
        </div>
      </header>

      <nav className="admin-tabs-row admin-tabs" aria-label="관리자 화면 전환">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            className={tab === id ? "admin-tab is-active" : "admin-tab"}
            onClick={() => {
              setTab(id);
            }}
          >
            {label}
            {id === "requests" && pendingCount > 0 ? (
              <span className="admin-count">{pendingCount}</span>
            ) : null}
            {id === "entries" && activeEntryCount > 0 ? (
              <span className="admin-count">{activeEntryCount}</span>
            ) : null}
          </button>
        ))}
      </nav>

      <div className="admin-scroll">
        <div className="admin-content">
          {tab === "wallboard" ? (
            <WallboardTab
              completedCallsTotal={completedCallsTotal}
              callGuardTotal={callGuardLog.length}
              pendingRequestCount={pendingCount}
              activeEntryCount={activeEntryCount}
            />
          ) : null}
          {tab === "requests" ? (
            <RequestsTab
              requests={requests}
              defaultExpiryMonths={blacklistExpiryMonths}
              onApprove={(requestId, expiryMonths) => {
                decide(requestId, true, admin, expiryMonths);
              }}
              onReject={(requestId) => {
                decide(requestId, false, admin);
              }}
            />
          ) : null}
          {tab === "entries" ? (
            <EntriesTab
              entries={entries}
              requests={requests}
              defaultExpiryMonths={blacklistExpiryMonths}
              onRelease={(entryId) => {
                release(entryId, admin, "관리자 해제");
              }}
              onExtend={(entryId, months) => {
                extend(entryId, months);
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
    </main>
  );
}
