import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/client";
import { useAuth } from "../components/AuthContext";

type Policy = { id: string; policy_number: string; product_code: string; status: string; annual_premium: number };
type Invoice = { id: string; invoice_number: string; amount: number; status: string };
type Claim = { id: string; claim_number: string; status: string };

export default function Home() {
  const { user } = useAuth();
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [claims, setClaims] = useState<Claim[]>([]);

  useEffect(() => {
    Promise.all([
      api.get("/policies"),
      api.get("/finance/invoices"),
      api.get("/claims"),
    ])
      .then(([p, i, c]) => {
        setPolicies(p.data);
        setInvoices(i.data);
        setClaims(c.data);
      })
      .catch(console.error);
  }, []);

  const openBalance = invoices
    .filter((inv) => inv.status === "OPEN")
    .reduce((sum, inv) => sum + inv.amount, 0);

  return (
    <div className="stack">
      <div className="hero">
        <h1>Welcome back, {user?.full_name?.split(" ")[0] || "there"}</h1>
        <p>Your Meridian coverage, bills, and claims in one place.</p>
      </div>
      <div className="grid-3">
        <div className="stat">
          <div className="label">Active policies</div>
          <div className="value">{policies.filter((p) => p.status === "ACTIVE").length}</div>
        </div>
        <div className="stat">
          <div className="label">Amount due</div>
          <div className="value">${openBalance.toFixed(2)}</div>
        </div>
        <div className="stat">
          <div className="label">Open claims</div>
          <div className="value">{claims.filter((c) => !["SETTLED", "DENIED"].includes(c.status)).length}</div>
        </div>
      </div>
      <div className="grid-2">
        <div className="panel stack">
          <h3>Quick actions</h3>
          <div className="row">
            <Link className="btn" to="/billing">Pay a bill</Link>
            <Link className="btn ghost" to="/claims">File a claim</Link>
            <Link className="btn ghost" to="/policies">View policies</Link>
          </div>
        </div>
        <div className="panel stack">
          <h3>Recent invoices</h3>
          {invoices.slice(0, 3).map((inv) => (
            <div className="row" key={inv.id}>
              <span>{inv.invoice_number}</span>
              <span>${inv.amount.toFixed(2)}</span>
              <span className={`badge ${inv.status === "OPEN" ? "open" : "paid"}`}>{inv.status}</span>
            </div>
          ))}
          {!invoices.length && <p className="muted">No invoices yet.</p>}
        </div>
      </div>
    </div>
  );
}
