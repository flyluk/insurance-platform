import { FormEvent, useEffect, useState } from "react";
import api from "../api/client";

type Policy = { id: string; policy_number: string; party_id: string; product_code: string; status: string };
type Claim = {
  id: string;
  claim_number: string;
  policy_id: string;
  product_code: string;
  status: string;
  reserve_amount: number;
  settlement_amount: number | null;
  description: string;
};

export default function Claims() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [policyId, setPolicyId] = useState("");
  const [description, setDescription] = useState("Collision damage");
  const [lossDate, setLossDate] = useState("2026-07-01");

  async function refresh() {
    const [p, c] = await Promise.all([api.get("/policies"), api.get("/claims")]);
    setPolicies(p.data.filter((x: Policy) => x.status === "ACTIVE"));
    setClaims(c.data);
    if (!policyId && p.data[0]) setPolicyId(p.data[0].id);
  }

  useEffect(() => {
    refresh().catch(console.error);
  }, []);

  async function openClaim(e: FormEvent) {
    e.preventDefault();
    const policy = policies.find((p) => p.id === policyId);
    if (!policy) return;
    await api.post("/claims", {
      policy_id: policy.id,
      party_id: policy.party_id,
      product_code: policy.product_code,
      description,
      loss_date: lossDate,
      reserve_amount: 1000,
    });
    await refresh();
  }

  async function settle(id: string) {
    await api.post(`/claims/${id}/settle`, { settlement_amount: 1500 });
    await refresh();
  }

  async function deny(id: string) {
    await api.post(`/claims/${id}/deny`);
    await refresh();
  }

  return (
    <div className="stack">
      <div className="hero">
        <h1>Claims</h1>
        <p>FNOL, reserves, settlement, and denial workflows.</p>
      </div>
      <form className="panel stack" onSubmit={openClaim}>
        <h3>Open claim (FNOL)</h3>
        <label>
          Policy
          <select value={policyId} onChange={(e) => setPolicyId(e.target.value)}>
            {policies.map((p) => (
              <option key={p.id} value={p.id}>
                {p.policy_number} ({p.product_code})
              </option>
            ))}
          </select>
        </label>
        <label>
          Loss date
          <input value={lossDate} onChange={(e) => setLossDate(e.target.value)} />
        </label>
        <label>
          Description
          <input value={description} onChange={(e) => setDescription(e.target.value)} />
        </label>
        <button className="btn" type="submit">
          Open claim
        </button>
      </form>
      <div className="panel">
        <table>
          <thead>
            <tr>
              <th>Claim</th>
              <th>Product</th>
              <th>Status</th>
              <th>Reserve</th>
              <th>Settlement</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {claims.map((c) => (
              <tr key={c.id}>
                <td>{c.claim_number}</td>
                <td>{c.product_code}</td>
                <td>
                  <span className="badge">{c.status}</span>
                </td>
                <td>{c.reserve_amount}</td>
                <td>{c.settlement_amount ?? "—"}</td>
                <td className="row">
                  {!["SETTLED", "DENIED"].includes(c.status) && (
                    <>
                      <button className="btn" type="button" onClick={() => settle(c.id)}>
                        Settle $1500
                      </button>
                      <button className="btn danger" type="button" onClick={() => deny(c.id)}>
                        Deny
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
