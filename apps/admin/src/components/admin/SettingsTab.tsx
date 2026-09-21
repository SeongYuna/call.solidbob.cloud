import { useEffect, useState, type ReactElement } from "react";
import {
  fetchAgents,
  fetchAgentTokens,
  HubApiError,
  issueAgentToken,
  purgeBlacklistRetention,
  revokeAgentToken,
  type AgentSummary,
  type AgentTokenItem,
  type RetentionPurgeResult,
} from "../../lib/api/hubClient";
import { useAuthStore } from "../../lib/auth/authStore";

/**
 * 설정. Twilio Flex의 "라우팅 설정"류를 본떴다 — 코드에 상수로 굳히지 않고
 * 화면에서 조정하게 뺀 값을 노출한다. J-5 베테랑 배정 기준(근속 연차)은
 * `_project/decisions/204`가 "조직마다 다르고 3년이 옳다는 근거가 없어
 * 설정으로 뺀다"고 정한 값이다.
 *
 * `decisions/313` — `GET/PUT /hub/routing-settings`에 연결됐다(`adminStore.ts`).
 * 실제 배정 판정(`POST /hub/routing-decisions`)을 누가 부르는지는 별도 문제다 —
 * 여기서 저장한 값은 그 판정이 호출될 때부터 쓰인다.
 */
export function SettingsTab({
  veteranThresholdYears,
  onChangeVeteranThresholdYears,
  blacklistExpiryMonths,
  onChangeBlacklistExpiryMonths,
}: {
  veteranThresholdYears: number;
  onChangeVeteranThresholdYears: (years: number) => void;
  blacklistExpiryMonths: number;
  onChangeBlacklistExpiryMonths: (months: number) => void;
}): ReactElement {
  return (
    <section aria-label="설정">
      <div className="wrapup-card admin-settings-card">
        <div className="wrapup-card-head">
          <h3>J-5 베테랑 배정 기준</h3>
        </div>
        <label className="admin-settings-field">
          <span>근속 연차 (년) 이상이면 베테랑으로 배정</span>
          <input
            type="number"
            min={0.5}
            max={40}
            step={0.5}
            value={veteranThresholdYears}
            onChange={(event) => {
              const next = Number(event.target.value);
              if (Number.isFinite(next) && next >= 0.5) {
                void onChangeVeteranThresholdYears(next);
              }
            }}
          />
        </label>
        <p className="admin-help">
          저장하면 다음 배정 판정부터 이 기준이 쓰입니다(0.5~40년).
        </p>
      </div>

      <div className="wrapup-card admin-settings-card">
        <div className="wrapup-card-head">
          <h3>J-4 블랙리스트 등록 만료 기간 — 기본값</h3>
        </div>
        <label className="admin-settings-field">
          <span>승인 후 (개월) 뒤 자동 만료</span>
          <input
            type="number"
            min={1}
            max={12}
            value={blacklistExpiryMonths}
            onChange={(event) => {
              const next = Number(event.target.value);
              if (Number.isFinite(next) && next >= 1) {
                onChangeBlacklistExpiryMonths(next);
              }
            }}
          />
        </label>
        <p className="admin-help">
          만료가 없으면 영구 표시가 됩니다(`decisions/205` ⑤). 이건 **기본값**일
          뿐입니다 — 사안마다 심각도가 다르므로, 실제 기간은 <strong>승인
          카드에서 건마다 조정</strong>하거나 <strong>블랙리스트 탭에서 등록 후
          연장·단축</strong>합니다. 여기서 바꾼 값은 앞으로 새 승인 카드에
          미리 채워지는 값만 바뀝니다.
        </p>
      </div>

      <AgentTokenIssuer />

      <RetentionPurgeCard />
    </section>
  );
}

/**
 * `decisions/312` — 종결 뒤 180일 지난 블랙리스트 문장(만료 변경 사유·반려 요청 사유·자막)을
 * 비운다(SEC-1). 행은 지우지 않고 문장만 비운다. 몇 번을 눌러도 결과가 같다 — 주기 실행이
 * 생기면 같은 API를 그대로 부를 수 있다(관리자 버튼은 그때도 남겨 둔다).
 */
function RetentionPurgeCard(): ReactElement {
  const accessToken = useAuthStore((s) => s.accessToken);
  const [result, setResult] = useState<RetentionPurgeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  async function handlePurge(): Promise<void> {
    if (accessToken === null) {
      return;
    }
    if (!window.confirm("종결 뒤 보존 기간이 지난 블랙리스트 사유·자막을 비웁니다. 되돌릴 수 없습니다. 계속할까요?")) {
      return;
    }
    setError(null);
    setRunning(true);
    try {
      setResult(await purgeBlacklistRetention(accessToken));
    } catch (err) {
      setError(err instanceof HubApiError || err instanceof Error ? err.message : "알 수 없는 오류");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="wrapup-card admin-settings-card">
      <div className="wrapup-card-head">
        <h3>블랙리스트 보존 정리</h3>
      </div>
      <p className="admin-help">
        종결된 지 오래된 만료 변경 사유·반려 요청 사유를 비웁니다. 등록·이력 행 자체는
        지우지 않습니다 — 문장만 비웁니다.
      </p>
      {error !== null ? (
        <p className="header-error" role="alert">
          {error}
        </p>
      ) : null}
      <button
        type="button"
        className="btn-outline"
        disabled={running}
        onClick={() => {
          void handlePurge();
        }}
      >
        {running ? "정리 중..." : "지금 정리하기"}
      </button>
      {result !== null ? (
        <p className="admin-help" style={{ marginTop: 8 }}>
          보존 기간 {result.retentionDays}일 — {new Date(result.cutoff).toLocaleString("ko-KR")} 이전 종결분 정리.
          만료 변경 사유 {result.expiryChangeReasonsPurged}건 · 반려 요청 사유 {result.rejectedRequestsPurged}건 비움.
        </p>
      ) : null}
    </div>
  );
}

/**
 * `decisions/307` — 상담원 전용 토큰 발급. 상담원 로그인 화면이 없어 관리자가
 * 발급한 값을 `?agent_token=...` 링크로 건넨다. 토큰 원문은 발급 응답에
 * 한 번만 실린다 — 잃어버리면 폐기하고 새로 발급한다.
 *
 * `decisions/406` — 상담원 목록 관리 화면이 아직 없다(테스트 단계). 이름을 치면 서버가
 * 같은 이름의 상담원을 찾아 쓰거나, 없으면 그 자리에서 새로 만든다 — 관리자가 미리
 * `agent.agent_id`를 알아야 할 필요가 없다.
 */
function AgentTokenIssuer(): ReactElement {
  const accessToken = useAuthStore((s) => s.accessToken);
  const [agentName, setAgentName] = useState("");
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [tokens, setTokens] = useState<AgentTokenItem[]>([]);
  const [issuedToken, setIssuedToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (accessToken === null) {
      return;
    }
    fetchAgentTokens(accessToken)
      .then(setTokens)
      .catch((err: unknown) => {
        setError(err instanceof HubApiError || err instanceof Error ? err.message : "알 수 없는 오류");
      });
    // 이미 등록된 상담원이 있으면 드롭다운으로 고르게 한다. 아직 하나도 없으면(테스트
    // 단계 기본값) 아래 입력창에 이름을 직접 친다 — 서버가 찾아 쓰거나 새로 만든다.
    fetchAgents(accessToken)
      .then((list) => {
        setAgents(list);
        if (list.length > 0) {
          setAgentName((current) => (current.length > 0 ? current : list[0].displayName));
        }
      })
      .catch(() => {
        // 목록 실패는 조용히 넘어간다 — 아래 입력창이 이름 직접 입력으로 대신한다
      });
  }, [accessToken]);

  const agentNameById = new Map(agents.map((a) => [a.agentId, a.displayName]));

  async function handleIssue(): Promise<void> {
    const name = agentName.trim();
    if (accessToken === null || name.length === 0) {
      return;
    }
    setError(null);
    try {
      const { token, item } = await issueAgentToken(accessToken, name);
      setIssuedToken(token);
      setCopied(false);
      setTokens((prev) => [item, ...prev]);
      // 방금 발급한 상담원을 목록에 반영해 둔다 — 처음 등록됐다면 서버가 여기서 만든 것이다.
      setAgents((prev) => (prev.some((a) => a.agentId === item.agent_id) ? prev : [...prev, { agentId: item.agent_id, displayName: name }]));
      setAgentName(agents.length > 0 ? agents[0].displayName : "");
    } catch (err) {
      setError(err instanceof HubApiError || err instanceof Error ? err.message : "알 수 없는 오류");
    }
  }

  async function handleRevoke(tokenId: string): Promise<void> {
    if (accessToken === null) {
      return;
    }
    setError(null);
    try {
      const revoked = await revokeAgentToken(accessToken, tokenId);
      setTokens((prev) => prev.map((t) => (t.id === tokenId ? revoked : t)));
    } catch (err) {
      setError(err instanceof HubApiError || err instanceof Error ? err.message : "알 수 없는 오류");
    }
  }

  return (
    <div className="wrapup-card admin-settings-card">
      <div className="wrapup-card-head">
        <h3>상담원 토큰 발급</h3>
      </div>
      <p className="admin-help">
        블랙리스트 요청(<code>POST /hub/blacklist-requests</code>)은 이제 상담원 토큰이
        있어야 보낼 수 있습니다(`decisions/307`). 발급한 토큰을{" "}
        <code>?agent_token=...</code> 링크로 상담원에게 전달하세요 — 원문은 지금
        한 번만 보이고 서버는 다시 보여주지 않습니다. 상담원 목록 관리 화면이 아직 없어
        <strong> 이름을 치면 그 이름의 상담원을 찾아 쓰거나 없으면 새로 만듭니다</strong>
        (`decisions/406`) — 같은 이름을 다시 치면 같은 상담원의 토큰이 추가로 발급됩니다.
      </p>
      {error !== null ? (
        <p className="header-error" role="alert">
          {error}
        </p>
      ) : null}
      <label className="admin-settings-field">
        <span>상담원 이름</span>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            type="text"
            list="known-agent-names"
            value={agentName}
            onChange={(event) => {
              setAgentName(event.target.value);
            }}
            placeholder="상담원 이름 (없으면 새로 등록됩니다)"
          />
          {agents.length > 0 ? (
            <datalist id="known-agent-names">
              {agents.map((a) => (
                <option key={a.agentId} value={a.displayName} />
              ))}
            </datalist>
          ) : null}
          <button
            type="button"
            className="btn-outline"
            disabled={agentName.trim().length === 0}
            onClick={() => {
              void handleIssue();
            }}
          >
            발급
          </button>
        </div>
      </label>

      {issuedToken !== null ? (
        <div className="admin-entry-row" style={{ marginTop: 12 }}>
          <div className="admin-entry-row-main">
            <span className="admin-ref">{issuedToken}</span>
          </div>
          <button
            type="button"
            className="btn-outline"
            onClick={() => {
              void navigator.clipboard.writeText(issuedToken).then(() => {
                setCopied(true);
              });
            }}
          >
            {copied ? "복사됨" : "복사"}
          </button>
        </div>
      ) : null}

      {tokens.length > 0 ? (
        <ul className="admin-list" style={{ marginTop: 12 }}>
          {tokens.map((t) => {
            const displayName = agentNameById.get(t.agent_id) ?? t.agent_id;
            // agent_id 는 이름을 그대로 쓰므로(`decisions/406`) 대개 같다 — 다르면(20자 초과 등
            // 무작위로 대신한 경우) 괄호로 실제 agent_id 를 덧붙인다.
            return (
            <li key={t.id} className="admin-entry-row">
              <div className="admin-entry-row-main">
                <span className="admin-ref">
                  {displayName}
                  {displayName !== t.agent_id ? ` (${t.agent_id})` : ""}
                </span>
                <span className="admin-meta">
                  {new Date(t.issued_at).toLocaleDateString("ko-KR")} 발급
                </span>
                {t.revoked_at !== null ? (
                  <span className="admin-meta">폐기됨</span>
                ) : null}
              </div>
              {t.revoked_at === null ? (
                <button
                  type="button"
                  className="btn-outline admin-release"
                  onClick={() => {
                    void handleRevoke(t.id);
                  }}
                >
                  폐기
                </button>
              ) : null}
            </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}
