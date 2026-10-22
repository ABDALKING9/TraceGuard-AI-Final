import { useState, type FormEvent } from "react";
import { AlertTriangle, LoaderCircle, ShieldCheck } from "lucide-react";

export function LoginScreen({
  onSubmit,
  demoEmail,
  demoPassword,
  backendHint,
}: {
  onSubmit: (email: string, password: string) => Promise<void>;
  demoEmail: string;
  demoPassword: string;
  backendHint: string;
}) {
  const [email, setEmail] = useState(demoEmail);
  const [password, setPassword] = useState(demoPassword);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await onSubmit(email.trim(), password);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-screen">
      <div className="login-card">
        <div className="login-brand">
          <div className="brand-mark">
            <ShieldCheck size={23} />
          </div>
          <div>
            <strong>TraceGuard</strong>
            <span>AI ANALYST WORKSPACE</span>
          </div>
        </div>
        <h1>Sign in to the workspace</h1>
        <p className="login-subtitle">
          Local demonstration session. All data is synthetic and stays on this machine.
        </p>

        {error ? (
          <div className="alert error" role="alert" data-testid="login-error">
            <AlertTriangle size={18} />
            <p>{error}</p>
          </div>
        ) : null}

        <form onSubmit={handleSubmit} className="login-form">
          <label className="field-label" htmlFor="login-email">
            Email
          </label>
          <input
            id="login-email"
            className="login-input"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />

          <label className="field-label" htmlFor="login-password">
            Password
          </label>
          <input
            id="login-password"
            className="login-input"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />

          <button className="primary-button full-button" type="submit" disabled={busy}>
            {busy ? <LoaderCircle size={16} className="spin" /> : <ShieldCheck size={16} />}
            {busy ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <div className="login-hint">
          <strong>Demonstration credentials</strong>
          <span>
            {demoEmail} · {demoPassword}
          </span>
          <small>{backendHint}</small>
        </div>
      </div>
    </div>
  );
}
