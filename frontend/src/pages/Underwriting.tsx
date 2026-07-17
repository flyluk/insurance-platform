import { useEffect, useState } from "react";
import api from "../api/client";

type Case = {
  id: string;
  application_id: string;
  product_code: string;
  status: string;
  annual_premium: number;
  auto_decision: string | null;
  final_decision: string | null;
  reason: string | null;
};

export default function Underwriting() {
  const [queue, setQueue] = useState<Case[]>([]);
  const [all, setAll] = useState<Case[]>([]);

  async function refresh() {
    const [q, c] = await Promise.all([api.get("/uw/queue"), api.get("/uw/cases")]);
    setQueue(q.data);
    setAll(c.data);
  }

  useEffect(() => {
    refresh().catch(console.error);
  }, []);

  async function decide(id: string, decision: "ACCEPT" | "DECLINE") {
    await api.post(`/uw/cases/${id}/decide`, { decision, reason: `Manual ${decision}` });
    await refresh();
  }

  return (
    <div className="stack">
      <div className="hero">
        <h1>Underwriting</h1>
        <p>Referral queue and automated decisions across AUTO, HOME, and LIFE.</p>
      </div>
      <div className="panel">
        <h3>Referral queue</h3>
        <table>
          <thead>
            <tr>
              <th>Product</th>
              <th>Premium</th>
              <th>Reason</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {queue.map((c) => (
              <tr key={c.id}>
                <td>{c.product_code}</td>
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
                <td colSpan={4} className="muted">
                  No referrals waiting
                </td>
              </tr>
            )}
          </tbody>
        </table>
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
            </tr>
          </thead>
          <tbody>
            {all.map((c) => (
              <tr key={c.id}>
                <td>{c.product_code}</td>
                <td>
                  <span className={`badge ${c.status === "REFERRED" ? "warn" : c.status === "DECLINED" ? "bad" : ""}`}>
                    {c.status}
                  </span>
                </td>
                <td>{c.auto_decision}</td>
                <td>{c.final_decision || "—"}</td>
                <td>{c.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
