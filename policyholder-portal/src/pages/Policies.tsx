import { useEffect, useState } from "react";
import api from "../api/client";
import Pagination, { usePagination } from "../components/Pagination";
import PartyDetails, { PartySummary } from "../components/PartyDetails";

type Policy = {
  id: string;
  policy_number: string;
  product_code: string;
  status: string;
  annual_premium: number;
  effective_date: string;
  expiry_date: string;
  risk_attributes: Record<string, unknown>;
  owner?: PartySummary | null;
  insured?: PartySummary | null;
};

export default function Policies() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [selected, setSelected] = useState<Policy | null>(null);

  useEffect(() => {
    api
      .get("/policies")
      .then((r) => {
        setPolicies(r.data);
        if (r.data[0]) setSelected(r.data[0]);
      })
      .catch(console.error);
  }, []);

  const policyPage = usePagination(policies);

  return (
    <div className="stack">
      <div className="hero">
        <h1>Your policies</h1>
        <p>Coverage details for Auto, Home, and Life products on your account.</p>
      </div>
      <div className="grid-2">
        <div className="panel">
          <table>
            <thead>
              <tr>
                <th>Number</th>
                <th>Line</th>
                <th>Status</th>
                <th>Premium</th>
              </tr>
            </thead>
            <tbody>
              {policyPage.pageItems.map((p) => (
                <tr
                  key={p.id}
                  style={{ cursor: "pointer", background: selected?.id === p.id ? "rgba(31,107,79,0.06)" : undefined }}
                  onClick={() => setSelected(p)}
                >
                  <td>{p.policy_number}</td>
                  <td>{p.product_code}</td>
                  <td>
                    <span className={`badge ${p.status === "ACTIVE" ? "active" : ""}`}>{p.status}</span>
                  </td>
                  <td>${p.annual_premium.toFixed(2)}</td>
                </tr>
              ))}
              {!policies.length && (
                <tr>
                  <td colSpan={4} className="muted">
                    No policies on this account yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          <Pagination
            page={policyPage.page}
            totalPages={policyPage.totalPages}
            total={policyPage.total}
            pageSize={policyPage.pageSize}
            onPageChange={policyPage.setPage}
            onPageSizeChange={policyPage.setPageSize}
          />
        </div>
        <div className="panel stack">
          <h3>Policy details</h3>
          {selected ? (
            <>
              <div className="row">
                <strong>{selected.policy_number}</strong>
                <span className="badge active">{selected.product_code}</span>
              </div>
              <p className="muted">
                Effective {new Date(selected.effective_date).toLocaleDateString()} · Expires{" "}
                {new Date(selected.expiry_date).toLocaleDateString()}
              </p>
              <p>
                Annual premium <strong>${selected.annual_premium.toFixed(2)}</strong>
              </p>
              <div className="party-pair">
                <PartyDetails role="Owner" party={selected.owner} />
                <PartyDetails role="Insured" party={selected.insured} />
              </div>
              <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: "0.85rem", color: "var(--muted)" }}>
                {JSON.stringify(selected.risk_attributes, null, 2)}
              </pre>
            </>
          ) : (
            <p className="muted">Select a policy to view details.</p>
          )}
        </div>
      </div>
    </div>
  );
}
