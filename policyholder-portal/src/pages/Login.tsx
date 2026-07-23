import { FormEvent, useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../components/AuthContext";

export default function Login() {
  const { login, token } = useAuth();
  const [email, setEmail] = useState("policyholder@insurance.local");
  const [password, setPassword] = useState("holder123");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (token) return <Navigate to="/" replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={onSubmit}>
        <p className="brand-mark">Meridian</p>
        <h1>My Account</h1>
        <p>View your policies, pay premiums, and file a claim.</p>
        <div className="stack">
          <label>
            Email
            <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
          </label>
          <label>
            Password
            <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required />
          </label>
          {error && <div className="error">{error}</div>}
          <button className="btn" disabled={loading} type="submit">
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </div>
        <div className="hint">
          Demo: policyholder@insurance.local / holder123
        </div>
      </form>
    </div>
  );
}
