import { FormEvent, useEffect, useState } from "react";
import api from "../api/client";
import { useAuth } from "../components/AuthContext";

type Policy = {
  id: string;
  policy_number: string;
  product_code: string;
  status: string;
  party_id: string;
};

type Claim = {
  id: string;
  claim_number: string;
  policy_id: string;
  product_code: string;
  status: string;
  description: string;
  loss_date: string;
};

export default function Claims() {
  const { user } = useAuth();
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [policyId, setPolicyId] = useState("");
  const [description, setDescription] = useState("");
  const [lossDate, setLossDate] = useState(new Date().toISOString().slice(0, 10));
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);

  async function refresh() {
    const [p, c] = await Promise.all([api.get("/policies"), api.get("/claims")]);
    setPolicies(p.data);
    setClaims(c.data);
    const active = (p.data as Policy[]).find((x) => x.status === "ACTIVE");
    if (active && !policyId) setPolicyId(active.id);
  }

  useEffect(() => {
    refresh().catch(console.error);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setSuccess("");
    const policy = policies.find((p) => p.id === policyId);
    if (!policy) {
      setError("Select a policy");
      setBusy(false);
      return;
    }
    try {
      const { data } = await api.post("/claims", {
        policy_id: policy.id,
        party_id: user?.party_id || policy.party_id,
        product_code: policy.product_code,
        description,
        loss_date: lossDate,
        reserve_amount: 0,
      });
      setSuccess(`Claim ${data.claim_number} submitted.`);
      setDescription("");
      await refresh();
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err instanceof Error ? err.message : "Unable to file claim");
      setError(String(detail));
    } finally {
      setBusy(false);
    }
  }

  const activePolicies = policies.filter((p) => p.status === "ACTIVE");

  return (
    <div className="stack">
      <div className="hero">
        <h1>Claims</h1>
        <p>File a first notice of loss and track open claims on your policies.</p>
      </div>
      <div className="grid-2">
        <form className="panel stack" onSubmit={onSubmit}>
          <h3>Report a loss</h3>
          <label>
            Policy
            <select value={policyId} onChange={(e) => setPolicyId(e.target.value)} required>
              <option value="">Select…</option>
              {activePolicies.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.policy_number} ({p.product_code})
                </option>
              ))}
            </select>
          </label>
          <label>
            Loss date
            <input type="date" value={lossDate} onChange={(e) => setLossDate(e.target.value)} required />
          </label>
          <label>
            What happened
            <textarea
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
              placeholder="Brief description of the loss"
            />
          </label>
          {error && <div className="error">{error}</div>}
          {success && <div className="success">{success}</div>}
          <button className="btn" type="submit" disabled={busy || !activePolicies.length}>
            {busy ? "Submitting…" : "Submit claim"}
          </button>
          {!activePolicies.length && <p className="muted">You need an active policy to file a claim.</p>}
        </form>
        <div className="panel">
          <h3>Your claims</h3>
          <table>
            <thead>
              <tr>
                <th>Number</th>
                <th>Line</th>
                <th>Status</th>
                <th>Loss date</th>
              </tr>
            </thead>
            <tbody>
              {claims.map((c) => (
                <tr key={c.id}>
                  <td>
                    <div>{c.claim_number}</div>
                    <div className="muted">{c.description}</div>
                  </td>
                  <td>{c.product_code}</td>
                  <td>
                    <span className="badge">{c.status}</span>
                  </td>
                  <td>{c.loss_date}</td>
                </tr>
              ))}
              {!claims.length && (
                <tr>
                  <td colSpan={4} className="muted">
                    No claims filed yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
