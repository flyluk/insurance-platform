import { FormEvent, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../api/client";

type Policy = {
  id: string;
  policy_number: string;
  application_id: string;
  party_id: string;
  product_code: string;
  status: string;
  annual_premium: number;
  risk_attributes: Record<string, unknown>;
  effective_date: string;
  expiry_date: string;
  created_at: string;
  updated_at: string;
};

type Endorsement = {
  id: string;
  endorsement_type: string;
  description: string | null;
  premium_delta: number;
  created_at: string;
};

function formatRisk(attrs: Record<string, unknown> | null | undefined) {
  if (!attrs || !Object.keys(attrs).length) return null;
  return Object.entries(attrs).map(([key, value]) => (
    <div key={key} className="detail-row">
      <span className="muted">{key.replace(/_/g, " ")}</span>
      <strong>{String(value)}</strong>
    </div>
  ));
}

export default function PolicyDetail() {
  const { id } = useParams<{ id: string }>();
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [endorsements, setEndorsements] = useState<Endorsement[]>([]);
  const [error, setError] = useState("");
  const [endorseType, setEndorseType] = useState("COVERAGE_UPDATE");
  const [endorseDesc, setEndorseDesc] = useState("Increase coverage");
  const [premiumDelta, setPremiumDelta] = useState(50);
  const activeId = useRef(id);
  activeId.current = id;

  async function refresh(isCurrent: () => boolean = () => true) {
    if (!id || activeId.current !== id) return;
    const requestedId = id;
    const [p, e] = await Promise.all([
      api.get(`/policies/${requestedId}`),
      api.get(`/policies/${requestedId}/endorsements`).catch((endorsementsError) => {
        console.error(endorsementsError);
        return null;
      }),
    ]);
    if (!isCurrent() || activeId.current !== requestedId) return;
    setPolicy(p.data);
    setEndorsements(e?.data ?? []);
    setError("");
  }

  useEffect(() => {
    let current = true;
    setPolicy(null);
    setEndorsements([]);
    setError("");
    refresh(() => current).catch(() => {
      if (current) setError("Policy not found");
    });
    return () => {
      current = false;
    };
  }, [id]);

  async function renew() {
    if (!id) return;
    await api.post(`/policies/${id}/renew`);
    await refresh();
  }

  async function cancel() {
    if (!id) return;
    await api.post(`/policies/${id}/cancel`);
    await refresh();
  }

  async function endorse(e: FormEvent) {
    e.preventDefault();
    if (!id) return;
    await api.post(`/policies/${id}/endorse`, {
      endorsement_type: endorseType,
      description: endorseDesc,
      premium_delta: premiumDelta,
    });
    await refresh();
  }

  if (error) {
    return (
      <div className="stack">
        <Link className="btn ghost" to="/policies">
          ← Policies
        </Link>
        <div className="error">{error}</div>
      </div>
    );
  }

  if (!policy) {
    return <div className="muted">Loading policy…</div>;
  }

  return (
    <div className="stack">
      <div className="row">
        <Link className="btn ghost" to="/policies">
          ← Policies
        </Link>
      </div>
      <div className="hero">
        <h1>{policy.policy_number}</h1>
        <p>
          {policy.product_code} policy ·{" "}
          <span className={`badge ${policy.status !== "ACTIVE" ? "bad" : ""}`}>{policy.status}</span>
        </p>
      </div>

      <div className="grid-2">
        <div className="panel stack">
          <h3>Policy details</h3>
          <div className="detail-grid">
            <div className="detail-row">
              <span className="muted">Policy ID</span>
              <strong className="mono">{policy.id}</strong>
            </div>
            <div className="detail-row">
              <span className="muted">Application</span>
              <strong className="mono">{policy.application_id}</strong>
            </div>
            <div className="detail-row">
              <span className="muted">Party</span>
              <strong className="mono">{policy.party_id}</strong>
            </div>
            <div className="detail-row">
              <span className="muted">Product</span>
              <strong>{policy.product_code}</strong>
            </div>
            <div className="detail-row">
              <span className="muted">Annual premium</span>
              <strong>${policy.annual_premium.toFixed(2)}</strong>
            </div>
            <div className="detail-row">
              <span className="muted">Term</span>
              <strong>
                {policy.effective_date.slice(0, 10)} → {policy.expiry_date.slice(0, 10)}
              </strong>
            </div>
            <div className="detail-row">
              <span className="muted">Created</span>
              <strong>{policy.created_at.slice(0, 19).replace("T", " ")}</strong>
            </div>
            <div className="detail-row">
              <span className="muted">Updated</span>
              <strong>{policy.updated_at.slice(0, 19).replace("T", " ")}</strong>
            </div>
          </div>
        </div>

        <div className="panel stack">
          <h3>Risk attributes</h3>
          <div className="detail-grid">{formatRisk(policy.risk_attributes) || <span className="muted">None</span>}</div>
        </div>
      </div>

      {policy.status === "ACTIVE" && (
        <div className="grid-2">
          <form className="panel stack" onSubmit={endorse}>
            <h3>Endorse</h3>
            <label>
              Type
              <input value={endorseType} onChange={(e) => setEndorseType(e.target.value)} required />
            </label>
            <label>
              Description
              <input value={endorseDesc} onChange={(e) => setEndorseDesc(e.target.value)} />
            </label>
            <label>
              Premium delta
              <input
                type="number"
                step="1"
                value={premiumDelta}
                onChange={(e) => setPremiumDelta(Number(e.target.value))}
              />
            </label>
            <button className="btn" type="submit">
              Apply endorsement
            </button>
          </form>
          <div className="panel stack">
            <h3>Actions</h3>
            <div className="row">
              <button className="btn" type="button" onClick={renew}>
                Renew
              </button>
              <button className="btn danger" type="button" onClick={cancel}>
                Cancel policy
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="panel">
        <h3>Endorsements</h3>
        <table>
          <thead>
            <tr>
              <th>Type</th>
              <th>Description</th>
              <th>Premium Δ</th>
              <th>Date</th>
            </tr>
          </thead>
          <tbody>
            {endorsements.map((e) => (
              <tr key={e.id}>
                <td>{e.endorsement_type}</td>
                <td>{e.description || "—"}</td>
                <td>{e.premium_delta >= 0 ? `+${e.premium_delta}` : e.premium_delta}</td>
                <td className="muted">{e.created_at.slice(0, 19).replace("T", " ")}</td>
              </tr>
            ))}
            {!endorsements.length && (
              <tr>
                <td colSpan={4} className="muted">
                  No endorsements yet
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
