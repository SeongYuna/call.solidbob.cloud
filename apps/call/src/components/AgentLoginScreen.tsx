import { useState, type FormEvent, type ReactElement } from "react";

interface AgentLoginScreenProps {
  error: string | null;
  onLogin: (token: string) => Promise<boolean>;
}

/**
 * 상담원 로그인 — 계정(아이디·비밀번호)이 아니라 관리자가 발급한 토큰을 붙여넣는
 * 방식이다(`decisions/307`, `/admin/agent-tokens`). `?agent_token=` 링크로 들어오면
 * `useAgentAuth`가 이 화면을 아예 건너뛴다 — 여기는 링크를 잃어버렸을 때 쓴다.
 */
export function AgentLoginScreen({ error, onLogin }: AgentLoginScreenProps): ReactElement {
  const [token, setToken] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (submitting) {
      return;
    }
    setSubmitting(true);
    await onLogin(token);
    setSubmitting(false);
  }

  return (
    <main className="force-password">
      <section className="wrapup-card force-password-card">
        <p className="wrapup-eyebrow">상담원 로그인</p>
        <h1 className="force-password-title">토큰으로 로그인해주세요</h1>
        <p className="force-password-lead">
          관리자에게 받은 상담원 토큰을 붙여넣으세요. 토큰이 없으면 관리자에게 발급을 요청해야 합니다.
        </p>
        <form className="force-password-form" onSubmit={onSubmit} noValidate>
          <label className="force-password-field">
            <span>상담원 토큰</span>
            <input
              type="password"
              autoComplete="off"
              autoFocus
              placeholder="cga_ 로 시작하는 토큰"
              value={token}
              onChange={(event) => {
                setToken(event.target.value);
              }}
            />
          </label>
          {error !== null ? (
            <p className="force-password-error" role="alert">
              {error}
            </p>
          ) : null}
          <button type="submit" className="btn-primary btn-start-call" disabled={submitting}>
            {submitting ? "확인 중…" : "로그인"}
          </button>
        </form>
      </section>
    </main>
  );
}
