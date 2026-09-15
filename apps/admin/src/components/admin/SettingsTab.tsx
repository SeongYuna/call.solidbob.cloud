import { useEffect, useState, type ReactElement } from "react";
import {
  fetchAgentTokens,
  HubApiError,
  issueAgentToken,
  revokeAgentToken,
  type AgentTokenItem,
} from "../../lib/api/hubClient";
import { useAuthStore } from "../../lib/auth/authStore";

/**
 * 설정. Twilio Flex의 "라우팅 설정"류를 본떴다 — 코드에 상수로 굳히지 않고
 * 화면에서 조정하게 뺀 값을 노출한다. J-5 베테랑 배정 기준(근속 연차)은
 * `_project/decisions/204`가 "조직마다 다르고 3년이 옳다는 근거가 없어
 * 설정으로 뺀다"고 정한 값인데, 실제 UI는 지금까지 없었다.
 *
 * ⚠ `server/apps/blacklist/domain/services/routing.py`(J-5 배정 로직)에는
 * 아직 안 꽂혀 있다 — 화면 표시·조정만 먼저 만들고, 서버 연동은 별도다.
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
            min={0}
            max={30}
            value={veteranThresholdYears}
            onChange={(event) => {
              const next = Number(event.target.value);
              if (Number.isFinite(next) && next >= 0) {
                onChangeVeteranThresholdYears(next);
              }
            }}
          />
        </label>
        <p className="admin-help">
          이 화면에서 바꿔도 실제 배정 로직(서버)에는 아직 연결돼 있지 않습니다
          — 값이 어떻게 보일지 먼저 확인하는 화면입니다.
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
    </section>
  );
}

/**
 * `decisions/307` — 상담원 전용 토큰 발급. 상담원 로그인 화면이 없어 관리자가
 * 발급한 값을 `?agent_token=...` 링크로 건넨다. 토큰 원문은 발급 응답에
 * 한 번만 실린다 — 잃어버리면 폐기하고 새로 발급한다.
 */
function AgentTokenIssuer(): ReactElement {
  const accessToken = useAuthStore((s) => s.accessToken);
  const [agentId, setAgentId] = useState("");
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
  }, [accessToken]);

  async function handleIssue(): Promise<void> {
    if (accessToken === null || agentId.trim().length === 0) {
      return;
    }
    setError(null);
    try {
      const { token, item } = await issueAgentToken(accessToken, agentId.trim());
      setIssuedToken(token);
      setCopied(false);
      setTokens((prev) => [item, ...prev]);
      setAgentId("");
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
        한 번만 보이고 서버는 다시 보여주지 않습니다.
      </p>
      {error !== null ? (
        <p className="header-error" role="alert">
          {error}
        </p>
      ) : null}
      <label className="admin-settings-field">
        <span>상담원 ID</span>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            type="text"
            value={agentId}
            onChange={(event) => {
              setAgentId(event.target.value);
            }}
            placeholder="agent.agent_id"
          />
          <button
            type="button"
            className="btn-outline"
            disabled={agentId.trim().length === 0}
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
          {tokens.map((t) => (
            <li key={t.id} className="admin-entry-row">
              <div className="admin-entry-row-main">
                <span className="admin-ref">{t.agent_id}</span>
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
          ))}
        </ul>
      ) : null}
    </div>
  );
}
