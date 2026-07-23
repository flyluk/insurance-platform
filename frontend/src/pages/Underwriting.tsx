import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/client";
import PartyDetails, { PartyCell, PartySummary, partyLabel } from "../components/PartyDetails";
import { flattenRiskEntries } from "../utils/formatRisk";

type Case = {
  id: string;
  application_id: string;
  party_id: string;
  insured_party_id?: string | null;
  product_code: string;
  status: string;
  annual_premium: number;
  risk_attributes: Record<string, unknown>;
  auto_decision: string | null;
  final_decision: string | null;
  reason: string | null;
  created_at: string;
  updated_at: string;
  owner?: PartySummary | null;
  insured?: PartySummary | null;
};

type Policy = {
  id: string;
  policy_number: string;
  application_id: string;
  status: string;
};

function formatRisk(attrs: Record<string, unknown> | null | undefined) {
  if (!attrs || !Object.keys(attrs).length) return null;
  return flattenRiskEntries(attrs).map((row) => (
    <div key={row.key} className="detail-row">
      <span className="muted">{row.label}</span>
      <strong className="risk-value">{row.value}</strong>
    </div>
  ));
}

export default function Underwriting() {
  const [queue, setQueue] = useState<Case[]>([]);
  const [all, setAll] = useState<Case[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectionVersion, setSelectionVersion] = useState(0);
  const [selected, setSelected] = useState<Case | null>(null);
  const [linkedPolicy, setLinkedPolicy] = useState<Policy | null>(null);
  const selectionRequest = useRef(0);

  async function refresh() {
    const [q, c] = await Promise.all([api.get("/uw/queue"), api.get("/uw/cases")]);
    setQueue(q.data);
    setAll(c.data);
  }

  useEffect(() => {
    refresh().catch(console.error);
  }, []);

  async function loadSelected(id: string | null) {
    const request = ++selectionRequest.current;
    if (!id) {
      setSelected(null);
      setLinkedPolicy(null);
      return;
    }

    try {
      const { data } = await api.get(`/uw/cases/${id}`);
      let policy: Policy | null = null;
      if (data.final_decision === "ACCEPT") {
        const policies = await api.get("/policies");
        policy = (policies.data as Policy[]).find((p) => p.application_id === data.application_id) || null;
      }
      if (request !== selectionRequest.current) return;
      setSelected(data);
      setLinkedPolicy(policy);
    } catch (error) {
      if (request === selectionRequest.current) console.error(error);
    }
  }

  useEffect(() => {
    loadSelected(selectedId);
    return () => {
      selectionRequest.current += 1;
    };
  }, [selectedId, selectionVersion]);

  async function decide(id: string, decision: "ACCEPT" | "DECLINE") {
    await api.post(`/uw/cases/${id}/decide`, { decision, reason: `Manual ${decision}` });
    await refresh();
    setSelectedId(id);
    setSelectionVersion((version) => version + 1);
  }

  return (
    <div className="stack">
      <div className="hero">
        <h1>Underwriting</h1>
        <p>Referral queue and automated decisions across AUTO, HOME, and LIFE.</p>
      </div>

      <div className="grid-2">
        <div className="panel">
          <h3>Referral queue</h3>
          <table>
            <thead>
              <tr>
                <th>Product</th>
                <th>Owner</th>
                <th>Insured</th>
                <th>Premium</th>
                <th>Reason</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {queue.map((c) => (
                <tr key={c.id} className={selectedId === c.id ? "row-selected" : undefined}>
                  <td>
                    <button type="button" className="linkish" onClick={() => setSelectedId(c.id)}>
                      {c.product_code}
                    </button>
                  </td>
                  <td><PartyCell party={c.owner} /></td>
                  <td><PartyCell party={c.insured} /></td>
                  <td>{c.annual_premium}</td>
                  <td>{c.reason}</td>
                  <td className="row">
                    <button className="btn" type="button" onClick={() => decide(c.id, "ACCEPT")}>
                      Accept
                    </button>
                    <button className="btn danger" type="button" onClick={() => decide(c.id, "DECLINE")}>
                      Decline
                    </button>
                  </td>
                </tr>
              ))}
              {!queue.length && (
                <tr>
                  <td colSpan={6} className="muted">
                    No referrals waiting
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="panel stack">
          <h3>Case details</h3>
          {!selected && <p className="muted">Select a case from the queue or all cases list.</p>}
          {selected && (
            <>
              <div className="detail-grid">
                <div className="detail-row">
                  <span className="muted">Status</span>
                  <span className={`badge ${selected.status === "REFERRED" ? "warn" : selected.status === "DECLINED" ? "bad" : ""}`}>
                    {selected.status}
                  </span>
                </div>
                <div className="detail-row">
                  <span className="muted">Product</span>
                  <strong>{selected.product_code}</strong>
                </div>
                <div className="detail-row">
                  <span className="muted">Premium</span>
                  <strong>${selected.annual_premium.toFixed(2)}</strong>
                </div>
                <div className="detail-row">
                  <span className="muted">Auto decision</span>
                  <strong>{selected.auto_decision || "—"}</strong>
                </div>
                <div className="detail-row">
                  <span className="muted">Final decision</span>
                  <strong>{selected.final_decision || "—"}</strong>
                </div>
                <div className="detail-row">
                  <span className="muted">Reason</span>
                  <strong>{selected.reason || "—"}</strong>
                </div>
                <div className="detail-row">
                  <span className="muted">Application</span>
                  <strong className="mono">{selected.application_id}</strong>
                </div>
              </div>
              <h4>Parties</h4>
              <div className="party-pair">
                <PartyDetails role="Owner" party={selected.owner} />
                <PartyDetails role="Insured" party={selected.insured} />
              </div>
              <h4>Risk attributes</h4>
              <div className="detail-grid">{formatRisk(selected.risk_attributes) || <span className="muted">None</span>}</div>
              {linkedPolicy && (
                <div className="policy-link-box">
                  <div>
                    <div className="muted">Bound policy</div>
                    <strong>{linkedPolicy.policy_number}</strong>
                    <span className={`badge ${linkedPolicy.status !== "ACTIVE" ? "bad" : ""}`} style={{ marginLeft: "0.5rem" }}>
                      {linkedPolicy.status}
                    </span>
                  </div>
                  <Link className="btn" to={`/policies/${linkedPolicy.id}`}>
                    View policy details
                  </Link>
                </div>
              )}
              {selected.final_decision === "ACCEPT" && !linkedPolicy && (
                <p className="muted">Accepted — policy may still be binding. Refresh shortly.</p>
              )}
            </>
          )}
        </div>
      </div>

      <div className="panel">
        <h3>All cases</h3>
        <table>
          <thead>
            <tr>
              <th>Product</th>
              <th>Status</th>
              <th>Auto</th>
              <th>Final</th>
              <th>Reason</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {all.map((c) => (
              <tr key={c.id} className={selectedId === c.id ? "row-selected" : undefined}>
                <td>{c.product_code}</td>
                <td>
                  <span className={`badge ${c.status === "REFERRED" ? "warn" : c.status === "DECLINED" ? "bad" : ""}`}>
                    {c.status}
                  </span>
                </td>
                <td>{c.auto_decision}</td>
                <td>{c.final_decision || "—"}</td>
                <td>{c.reason}</td>
                <td>
                  <button type="button" className="btn ghost" onClick={() => setSelectedId(c.id)}>
                    Details
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
