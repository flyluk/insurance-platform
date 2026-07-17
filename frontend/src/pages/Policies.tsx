import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
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
                <td>
                  <Link className="linkish" to={`/policies/${p.id}`}>
                    {p.policy_number}
                  </Link>
                </td>
                <td>{p.product_code}</td>
                <td>
                  <span className={`badge ${p.status !== "ACTIVE" ? "bad" : ""}`}>{p.status}</span>
                </td>
                <td>{p.annual_premium}</td>
                <td className="muted">
                  {p.effective_date.slice(0, 10)} → {p.expiry_date.slice(0, 10)}
                </td>
                <td>
                  <Link className="btn ghost" to={`/policies/${p.id}`}>
                    View
                  </Link>
                </td>
              </tr>
            ))}
            {!policies.length && (
              <tr>
                <td colSpan={6} className="muted">
                  No policies yet
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
