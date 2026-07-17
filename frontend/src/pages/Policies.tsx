import { useEffect, useState } from "react";
import api from "../api/client";

type Policy = {
  id: string;
  policy_number: string;
  product_code: string;
  status: string;
  annual_premium: number;
  party_id: string;
  effective_date: string;
  expiry_date: string;
};

export default function Policies() {
  const [policies, setPolicies] = useState<Policy[]>([]);

  async function refresh() {
    const { data } = await api.get("/policies");
    setPolicies(data);
  }

  useEffect(() => {
    refresh().catch(console.error);
  }, []);

  async function renew(id: string) {
    await api.post(`/policies/${id}/renew`);
    await refresh();
  }

  async function cancel(id: string) {
    await api.post(`/policies/${id}/cancel`);
    await refresh();
  }

  async function endorse(id: string) {
    await api.post(`/policies/${id}/endorse`, {
      endorsement_type: "COVERAGE_UPDATE",
      description: "Increase coverage",
      premium_delta: 50,
    });
    await refresh();
  }

  return (
    <div className="stack">
      <div className="hero">
        <h1>Policy Admin</h1>
        <p>Bound policies, endorsements, renewals, and cancellations.</p>
      </div>
      <div className="panel">
        <table>
          <thead>
            <tr>
              <th>Number</th>
              <th>Product</th>
              <th>Status</th>
              <th>Premium</th>
              <th>Term</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {policies.map((p) => (
              <tr key={p.id}>
                <td>{p.policy_number}</td>
                <td>{p.product_code}</td>
                <td>
                  <span className={`badge ${p.status !== "ACTIVE" ? "bad" : ""}`}>{p.status}</span>
                </td>
                <td>{p.annual_premium}</td>
                <td className="muted">
                  {p.effective_date.slice(0, 10)} → {p.expiry_date.slice(0, 10)}
                </td>
                <td className="row">
                  {p.status === "ACTIVE" && (
                    <>
                      <button className="btn ghost" type="button" onClick={() => endorse(p.id)}>
                        Endorse +$50
                      </button>
                      <button className="btn" type="button" onClick={() => renew(p.id)}>
                        Renew
                      </button>
                      <button className="btn danger" type="button" onClick={() => cancel(p.id)}>
                        Cancel
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
