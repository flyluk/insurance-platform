import { FormEvent, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../api/client";
import { useAuth } from "../components/AuthContext";
import PartyDetails, { PartySummary } from "../components/PartyDetails";

type Policy = {
  id: string;
  policy_number: string;
  application_id: string;
  party_id: string;
  insured_party_id?: string | null;
  product_code: string;
  status: string;
  annual_premium: number;
  risk_attributes: Record<string, unknown>;
  effective_date: string;
  expiry_date: string;
  cancelled_at?: string | null;
  cancellation_refund?: number | null;
  created_at: string;
  updated_at: string;
  owner?: PartySummary | null;
  insured?: PartySummary | null;
};

type Endorsement = {
  id: string;
  endorsement_type: string;
  description: string | null;
  premium_delta: number;
  billed_amount?: number;
  created_at: string;
};

type RiskField = {
  key: string;
  label: string;
  type: "number" | "boolean" | "text" | "select";
  required?: boolean;
  default?: unknown;
  min?: number;
  max?: number;
  step?: number;
  options?: { value: string; label: string }[];
};

const CHANGE_TYPES = [
  { value: "POLICY_CHANGE", label: "General policy change" },
  { value: "COVERAGE_UPDATE", label: "Coverage update" },
  { value: "VEHICLE_CHANGE", label: "Vehicle change" },
  { value: "DRIVER_CHANGE", label: "Driver change" },
  { value: "PROPERTY_CHANGE", label: "Property change" },
  { value: "ADDRESS_CHANGE", label: "Address / location change" },
];

function formatRisk(attrs: Record<string, unknown> | null | undefined) {
  if (!attrs || !Object.keys(attrs).length) return null;
  return Object.entries(attrs).map(([key, value]) => (
    <div key={key} className="detail-row">
      <span className="muted">{key.replace(/_/g, " ")}</span>
      <strong>{String(value)}</strong>
    </div>
  ));
}

function pickSchema(
  plans: { id: string; risk_schema?: RiskField[] }[],
  attrs: Record<string, unknown>,
): RiskField[] {
  if (!plans.length) return [];
  const selection = attrs.product_selection;
  const planId =
    selection && typeof selection === "object" && "plan_id" in selection
      ? (selection as { plan_id?: unknown }).plan_id
      : null;
  const selected = plans.find((plan) => plan.id === planId);
  if (selected) return selected.risk_schema || [];

  const scored = plans.map((p) => {
    const schema = p.risk_schema || [];
    const hits = schema.filter((f) => f.key in attrs).length;
    return { schema, hits };
  });
  scored.sort((a, b) => b.hits - a.hits);
  return scored[0]?.schema || [];
}

export default function PolicyDetail() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [endorsements, setEndorsements] = useState<Endorsement[]>([]);
  const [riskSchema, setRiskSchema] = useState<RiskField[]>([]);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [changeType, setChangeType] = useState("POLICY_CHANGE");
  const [changeDesc, setChangeDesc] = useState("");
  const [premiumDelta, setPremiumDelta] = useState(0);
  const [reRate, setReRate] = useState(true);
  const [preview, setPreview] = useState<{
    current_annual: number;
    new_annual: number;
    annual_delta: number;
    billed_amount: number;
    remaining_fraction: number;
  } | null>(null);
  const [cancelPreview, setCancelPreview] = useState<{
    unearned_premium: number;
    remaining_days: number;
    remaining_fraction: number;
  } | null>(null);
  const [riskDraft, setRiskDraft] = useState<Record<string, unknown>>({});
  const [showChange, setShowChange] = useState(false);
  const changeFormRef = useRef<HTMLFormElement>(null);
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
    setRiskDraft({ ...(p.data.risk_attributes || {}) });
    setEndorsements(e?.data ?? []);
    setError("");
    try {
      const plans = await api.get("/products/plans", {
        params: { product_code: p.data.product_code, status: "PUBLISHED" },
      });
      if (!isCurrent() || activeId.current !== requestedId) return;
      setRiskSchema(pickSchema(plans.data || [], p.data.risk_attributes || {}));
    } catch (schemaErr) {
      console.error(schemaErr);
      setRiskSchema([]);
    }
  }

  useEffect(() => {
    let current = true;
    setPolicy(null);
    setEndorsements([]);
    setError("");
    setMsg("");
    setShowChange(false);
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
    setMsg("Policy renewed");
    await refresh();
  }

  async function loadCancelPreview() {
    if (!id) return;
    const { data } = await api.get(`/policies/${id}/cancel-preview`);
    setCancelPreview(data);
  }

  async function cancel() {
    if (!id) return;
    let previewText = "";
    try {
      const { data } = await api.get(`/policies/${id}/cancel-preview`);
      previewText = ` Unearned premium refund: $${data.unearned_premium.toFixed(2)} (${data.remaining_days} days remaining).`;
    } catch {
      /* preview optional */
    }
    if (!window.confirm(`Cancel this policy?${previewText}`)) return;
    const { data } = await api.post(`/policies/${id}/cancel`);
    setMsg(
      `Policy cancelled` +
        (data.cancellation_refund != null
          ? ` · refund credit $${Number(data.cancellation_refund).toFixed(2)}`
          : ""),
    );
    setShowChange(false);
    setCancelPreview(null);
    await refresh();
  }

  function openChangeForm() {
    if (policy) setRiskDraft({ ...(policy.risk_attributes || {}) });
    setReRate(true);
    setPremiumDelta(0);
    setPreview(null);
    setShowChange(true);
    setTimeout(() => changeFormRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
  }

  async function calculateEndorse() {
    if (!id) return;
    const { data } = await api.post(`/policies/${id}/endorse-preview`, {
      risk_attributes: riskDraft,
      re_rate: reRate,
      premium_delta: premiumDelta,
    });
    setPreview(data);
  }

  async function submitChange(e: FormEvent) {
    e.preventDefault();
    if (!id || !policy) return;
    await api.post(`/policies/${id}/endorse`, {
      endorsement_type: changeType,
      description: changeDesc || "Policy change",
      re_rate: reRate,
      premium_delta: premiumDelta,
      risk_attributes: riskDraft,
    });
    setMsg("Policy change applied (re-rated / prorated)");
    setChangeDesc("");
    setPremiumDelta(0);
    setPreview(null);
    setShowChange(false);
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

  const isActive = policy.status === "ACTIVE";

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
      {msg && <div className="muted">{msg}</div>}

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
            {policy.cancelled_at && (
              <div className="detail-row">
                <span className="muted">Cancelled</span>
                <strong>
                  {policy.cancelled_at.slice(0, 19).replace("T", " ")}
                  {policy.cancellation_refund != null
                    ? ` · refund $${Number(policy.cancellation_refund).toFixed(2)}`
                    : ""}
                </strong>
              </div>
            )}
          </div>
          <h4>Parties</h4>
          <div className="party-pair">
            <PartyDetails role="Owner" party={policy.owner} />
            <PartyDetails role="Insured" party={policy.insured} />
          </div>
          {isActive && isAdmin && (
            <div className="row">
              <button className="btn" type="button" onClick={openChangeForm}>
                Policy change
              </button>
            </div>
          )}
        </div>

        <div className="panel stack">
          <h3>Risk attributes</h3>
          <div className="detail-grid">{formatRisk(policy.risk_attributes) || <span className="muted">None</span>}</div>
        </div>
      </div>

      {isActive && isAdmin && showChange && (
        <form className="panel stack" id="policy-change" ref={changeFormRef} onSubmit={submitChange}>
          <h3>Policy change</h3>
          <p className="muted" style={{ margin: 0 }}>
            Update coverage or risk details mid-term. Changes are recorded as endorsements.
          </p>
          <label>
            Change type
            <select value={changeType} onChange={(e) => setChangeType(e.target.value)} required>
              {CHANGE_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Description
            <input
              value={changeDesc}
              onChange={(e) => setChangeDesc(e.target.value)}
              placeholder="What is changing?"
            />
          </label>
          <label className="checkbox-row" style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <input type="checkbox" checked={reRate} onChange={(e) => setReRate(e.target.checked)} />
            Re-rate from risk attributes (recommended)
          </label>
          {!reRate && (
            <label>
              Manual annual premium delta ($)
              <input
                type="number"
                step="1"
                value={premiumDelta}
                onChange={(e) => setPremiumDelta(Number(e.target.value))}
              />
            </label>
          )}

          {riskSchema.length > 0 && (
            <>
              <h4>{policy.product_code} risk</h4>
              {riskSchema.map((field) => {
                if (field.type === "boolean") {
                  return (
                    <label key={field.key}>
                      {field.label}
                      <select
                        value={riskDraft[field.key] ? "yes" : "no"}
                        onChange={(e) =>
                          setRiskDraft({ ...riskDraft, [field.key]: e.target.value === "yes" })
                        }
                      >
                        <option value="no">No</option>
                        <option value="yes">Yes</option>
                      </select>
                    </label>
                  );
                }
                if (field.type === "select" && field.options) {
                  return (
                    <label key={field.key}>
                      {field.label}
                      <select
                        value={String(riskDraft[field.key] ?? field.default ?? "")}
                        onChange={(e) => setRiskDraft({ ...riskDraft, [field.key]: e.target.value })}
                      >
                        {field.options.map((o) => (
                          <option key={o.value} value={o.value}>
                            {o.label}
                          </option>
                        ))}
                      </select>
                    </label>
                  );
                }
                return (
                  <label key={field.key}>
                    {field.label}
                    <input
                      type={field.type === "number" ? "number" : "text"}
                      min={field.min}
                      max={field.max}
                      step={field.step}
                      value={
                        (riskDraft[field.key] as string | number | undefined) ??
                        (field.default as string | number | undefined) ??
                        (field.type === "number" ? 0 : "")
                      }
                      onChange={(e) =>
                        setRiskDraft({
                          ...riskDraft,
                          [field.key]:
                            field.type === "number" ? Number(e.target.value) : e.target.value,
                        })
                      }
                    />
                  </label>
                );
              })}
            </>
          )}

          {preview && (
            <div className="panel" style={{ boxShadow: "none" }}>
              <div className="detail-grid">
                <div className="detail-row">
                  <span className="muted">Current annual</span>
                  <strong>${preview.current_annual.toFixed(2)}</strong>
                </div>
                <div className="detail-row">
                  <span className="muted">New annual</span>
                  <strong>${preview.new_annual.toFixed(2)}</strong>
                </div>
                <div className="detail-row">
                  <span className="muted">Annual Δ</span>
                  <strong>
                    {preview.annual_delta >= 0 ? "+" : ""}
                    {preview.annual_delta.toFixed(2)}
                  </strong>
                </div>
                <div className="detail-row">
                  <span className="muted">Mid-term bill / credit</span>
                  <strong>
                    {preview.billed_amount >= 0 ? "+" : ""}
                    {preview.billed_amount.toFixed(2)} ({(preview.remaining_fraction * 100).toFixed(1)}% term left)
                  </strong>
                </div>
              </div>
            </div>
          )}

          <div className="row">
            <button className="btn ghost" type="button" onClick={() => calculateEndorse().catch(console.error)}>
              Calculate premium
            </button>
            <button className="btn" type="submit">
              Apply policy change
            </button>
            <button className="btn ghost" type="button" onClick={() => setShowChange(false)}>
              Cancel
            </button>
          </div>
        </form>
      )}

      {isActive && (
        <div className="panel stack">
          <h3>Actions</h3>
          {cancelPreview && (
            <p className="muted" style={{ margin: 0 }}>
              Cancel preview: unearned refund ${cancelPreview.unearned_premium.toFixed(2)} ·{" "}
              {cancelPreview.remaining_days} days remaining (
              {(cancelPreview.remaining_fraction * 100).toFixed(1)}%)
            </p>
          )}
          <div className="row">
            <button className="btn" type="button" onClick={renew}>
              Renew
            </button>
            <button className="btn ghost" type="button" onClick={() => loadCancelPreview().catch(console.error)}>
              Preview cancel
            </button>
            <button className="btn danger" type="button" onClick={cancel}>
              Cancel policy
            </button>
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
              <th>Annual Δ</th>
              <th>Billed</th>
              <th>Date</th>
            </tr>
          </thead>
          <tbody>
            {endorsements.map((e) => (
              <tr key={e.id}>
                <td>{e.endorsement_type}</td>
                <td>{e.description || "—"}</td>
                <td>{e.premium_delta >= 0 ? `+${e.premium_delta}` : e.premium_delta}</td>
                <td>
                  {e.billed_amount != null
                    ? `${e.billed_amount >= 0 ? "+" : ""}${e.billed_amount}`
                    : "—"}
                </td>
                <td className="muted">{e.created_at.slice(0, 19).replace("T", " ")}</td>
              </tr>
            ))}
            {!endorsements.length && (
              <tr>
                <td colSpan={5} className="muted">
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
