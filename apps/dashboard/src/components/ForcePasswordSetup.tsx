import { useState, type FormEvent, type ReactElement } from "react";

interface ForcePasswordSetupProps {
  mode: "forced" | "voluntary";
  tempPasswordUsed?: boolean;
  onComplete: () => void;
  onCancel?: () => void;
}

function passwordError(value: string, confirm: string): string | null {
  if (value.length < 8) {
    return "8자 이상이어야 합니다.";
  }
  if (!/[A-Za-z]/.test(value) || !/\d/.test(value)) {
    return "영문과 숫자를 함께 사용해 주세요.";
  }
  if (value !== confirm) {
    return "비밀번호가 서로 다릅니다.";
  }
  return null;
}

export function ForcePasswordSetup({
  mode,
  tempPasswordUsed = false,
  onComplete,
  onCancel,
}: ForcePasswordSetupProps): ReactElement {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const error = passwordError(password, confirm);
  const voluntary = mode === "voluntary";

  function onSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    setSubmitted(true);
    if (error !== null) {
      return;
    }
    onComplete();
  }

  return (
    <main className="force-password">
      <section className="wrapup-card force-password-card">
        {voluntary && onCancel !== undefined ? (
          <button type="button" className="btn-outline force-password-back" onClick={onCancel}>
            ← 취소
          </button>
        ) : null}
        <p className="wrapup-eyebrow">
          {voluntary ? "비밀번호 변경" : "최초 로그인"}
        </p>
        <h1 className="force-password-title">
          {voluntary ? "비밀번호를 변경해주세요" : "비밀번호를 설정해주세요"}
        </h1>
        <p className="force-password-lead">
          {voluntary
            ? "비밀번호를 변경합니다. 본인만 아는 비밀번호로 설정해주세요."
            : tempPasswordUsed
              ? "관리자가 발급한 임시 비밀번호로 로그인했습니다. 본인만 아는 비밀번호로 바꾼 뒤에 대기화면으로 들어갑니다."
              : "이 계정은 비밀번호를 한 번 설정해야 사용할 수 있습니다."}
        </p>
        <form className="force-password-form" onSubmit={onSubmit} noValidate>
          <label className="force-password-field">
            <span>새 비밀번호</span>
            <input
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(event) => {
                setPassword(event.target.value);
              }}
            />
          </label>
          <label className="force-password-field">
            <span>새 비밀번호 확인</span>
            <input
              type="password"
              autoComplete="new-password"
              value={confirm}
              onChange={(event) => {
                setConfirm(event.target.value);
              }}
            />
          </label>
          <p className="force-password-hint">
            8자 이상, 영문과 숫자를 함께 사용하세요.
          </p>
          {submitted && error !== null ? (
            <p className="force-password-error" role="alert">
              {error}
            </p>
          ) : null}
          <button type="submit" className="btn-primary btn-start-call">
            설정 완료
          </button>
        </form>
      </section>
    </main>
  );
}
