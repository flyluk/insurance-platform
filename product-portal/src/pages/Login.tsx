import { FormEvent, useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../components/AuthContext";

export default function Login() {
  const { login, token } = useAuth();
  const [email, setEmail] = useState("product@insurance.local");
  const [password, setPassword] = useState("product123");
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
        <h1>Product Studio</h1>
        <p>Configure basic plans and riders for AUTO, HOME, and LIFE.</p>
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
          product@insurance.local / product123
          <br />
          admin@insurance.local / admin123 also allowed
        </div>
      </form>
    </div>
  );
}
