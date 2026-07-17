import { FormEvent, useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../components/AuthContext";

export default function Login() {
  const { login, token } = useAuth();
  const [email, setEmail] = useState("agent@insurance.local");
  const [password, setPassword] = useState("agent123");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (token) return <Navigate to="/" replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(email, password);
    } catch {
      setError("Login failed. Check credentials.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={onSubmit}>
        <h1>Meridian</h1>
        <p>Staff console for new business through finance.</p>
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
          Demo users: agent / uw / claims / finance / admin @insurance.local
          <br />
          Passwords: agent123, uw123456, claims123, finance123, admin123
        </div>
      </form>
    </div>
  );
}
