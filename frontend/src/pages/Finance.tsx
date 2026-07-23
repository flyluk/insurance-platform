import { useEffect, useState } from "react";
import api from "../api/client";

type Invoice = {
  id: string;
  invoice_number: string;
  invoice_type: string;
  amount: number;
  status: string;
  description: string | null;
};
type Disbursement = {
  id: string;
  claim_number: string;
  amount: number;
  status: string;
};
type Journal = {
  id: string;
  memo: string;
  reference_type: string;
  lines: { account: string; debit: number; credit: number }[];
};

export default function Finance() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [disbursements, setDisbursements] = useState<Disbursement[]>([]);
  const [ledger, setLedger] = useState<Journal[]>([]);

  async function refresh() {
    const [i, d, l] = await Promise.all([
      api.get("/finance/invoices"),
      api.get("/finance/disbursements"),
      api.get("/finance/ledger"),
    ]);
    setInvoices(i.data);
    setDisbursements(d.data);
    setLedger(l.data);
  }

  useEffect(() => {
    refresh().catch(console.error);
  }, []);

  async function pay(inv: Invoice) {
    await api.post(`/finance/invoices/${inv.id}/pay`, { amount: inv.amount, method: "ACH" });
    await refresh();
  }

  return (
    <div className="stack">
      <div className="hero">
        <h1>Finance</h1>
        <p>Premium invoices, credits/refunds, claim disbursements, and GL entries.</p>
      </div>
      <div className="panel">
        <h3>Invoices</h3>
        <table>
          <thead>
            <tr>
              <th>Number</th>
              <th>Type</th>
              <th>Amount</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {invoices.map((inv) => (
              <tr key={inv.id}>
                <td>{inv.invoice_number}</td>
                <td>{inv.invoice_type}</td>
                <td>{inv.amount}</td>
                <td>
                  <span className="badge">{inv.status}</span>
                </td>
                <td>
                  {inv.status === "OPEN" && (
                    <button className="btn" type="button" onClick={() => pay(inv)}>
                      {["CREDIT", "CANCELLATION"].includes(inv.invoice_type) || inv.invoice_number.startsWith("CR-")
                        ? "Record refund"
                        : "Record payment"}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="panel">
        <h3>Claim disbursements</h3>
        <table>
          <thead>
            <tr>
              <th>Claim</th>
              <th>Amount</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {disbursements.map((d) => (
              <tr key={d.id}>
                <td>{d.claim_number}</td>
                <td>{d.amount}</td>
                <td>
                  <span className="badge">{d.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="panel">
        <h3>Ledger</h3>
        <table>
          <thead>
            <tr>
              <th>Memo</th>
              <th>Lines</th>
            </tr>
          </thead>
          <tbody>
            {ledger.map((j) => (
              <tr key={j.id}>
                <td>
                  <div>{j.memo}</div>
                  <div className="muted">{j.reference_type}</div>
                </td>
                <td>
                  {j.lines.map((l, idx) => (
                    <div key={idx}>
                      {l.account}: Dr {l.debit} / Cr {l.credit}
                    </div>
                  ))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
