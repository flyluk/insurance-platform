import { FormEvent, useEffect, useState } from "react";
import api from "../api/client";
import { PartyCell, PartySummary } from "../components/PartyDetails";

type Invoice = {
  id: string;
  invoice_number: string;
  invoice_type: string;
  amount: number;
  status: string;
  description: string | null;
  policy_id: string | null;
  party_id?: string;
  owner?: PartySummary | null;
};

type Method = "CARD" | "ACH";

export default function Billing() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [payingId, setPayingId] = useState<string | null>(null);
  const [method, setMethod] = useState<Method>("CARD");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);

  // Card
  const [cardNumber, setCardNumber] = useState("4242424242424242");
  const [expMonth, setExpMonth] = useState("12");
  const [expYear, setExpYear] = useState("2030");
  const [cvv, setCvv] = useState("123");

  // ACH
  const [accountName, setAccountName] = useState("Alex Rivera");
  const [accountNumber, setAccountNumber] = useState("123456789");
  const [routingNumber, setRoutingNumber] = useState("021000021");

  async function refresh() {
    const { data } = await api.get("/finance/invoices");
    setInvoices(data);
  }

  useEffect(() => {
    refresh().catch(console.error);
  }, []);

  async function onPay(e: FormEvent, inv: Invoice) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      const payload =
        method === "CARD"
          ? {
              amount: inv.amount,
              method: "CARD" as const,
              card_number: cardNumber,
              card_exp_month: Number(expMonth),
              card_exp_year: Number(expYear),
              card_cvv: cvv,
            }
          : {
              amount: inv.amount,
              method: "ACH" as const,
              account_name: accountName,
              account_number: accountNumber,
              routing_number: routingNumber,
            };
      const { data } = await api.post(`/finance/invoices/${inv.id}/pay`, payload);
      setSuccess(`Payment received (${data.method}${data.masked_account ? ` · ${data.masked_account}` : ""}).`);
      setPayingId(null);
      await refresh();
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err instanceof Error ? err.message : "Payment failed");
      setError(String(detail));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <div className="hero">
        <h1>Billing</h1>
        <p>Pay open premiums with card or bank account. Demo cards ending in 0000 are declined.</p>
      </div>
      {success && <div className="success">{success}</div>}
      {error && !payingId && <div className="error">{error}</div>}
      <div className="panel">
        <table>
          <thead>
            <tr>
              <th>Invoice</th>
              <th>Owner</th>
              <th>Type</th>
              <th>Amount</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {invoices.map((inv) => (
              <tr key={inv.id}>
                <td>
                  <div>{inv.invoice_number}</div>
                  {inv.description && <div className="muted">{inv.description}</div>}
                </td>
                <td><PartyCell party={inv.owner} /></td>
                <td>{inv.invoice_type}</td>
                <td>${inv.amount.toFixed(2)}</td>
                <td>
                  <span className={`badge ${inv.status === "OPEN" ? "open" : "paid"}`}>{inv.status}</span>
                </td>
                <td>
                  {inv.status === "OPEN" && (
                    <button className="btn" type="button" onClick={() => { setPayingId(inv.id); setError(""); setSuccess(""); }}>
                      Pay
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {!invoices.length && (
              <tr>
                <td colSpan={6} className="muted">
                  No invoices found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {payingId && (
        <div className="panel">
          {(() => {
            const inv = invoices.find((i) => i.id === payingId);
            if (!inv) return null;
            return (
              <form className="pay-form" onSubmit={(e) => onPay(e, inv)}>
                <h3>
                  Pay {inv.invoice_number} · ${inv.amount.toFixed(2)}
                </h3>
                <label>
                  Method
                  <select value={method} onChange={(e) => setMethod(e.target.value as Method)}>
                    <option value="CARD">Card</option>
                    <option value="ACH">Bank account (ACH)</option>
                  </select>
                </label>
                {method === "CARD" ? (
                  <div className="grid-2">
                    <label>
                      Card number
                      <input value={cardNumber} onChange={(e) => setCardNumber(e.target.value)} required />
                    </label>
                    <label>
                      CVV
                      <input value={cvv} onChange={(e) => setCvv(e.target.value)} required />
                    </label>
                    <label>
                      Exp. month
                      <input value={expMonth} onChange={(e) => setExpMonth(e.target.value)} required />
                    </label>
                    <label>
                      Exp. year
                      <input value={expYear} onChange={(e) => setExpYear(e.target.value)} required />
                    </label>
                  </div>
                ) : (
                  <div className="grid-2">
                    <label>
                      Account name
                      <input value={accountName} onChange={(e) => setAccountName(e.target.value)} required />
                    </label>
                    <label>
                      Routing number
                      <input value={routingNumber} onChange={(e) => setRoutingNumber(e.target.value)} required />
                    </label>
                    <label>
                      Account number
                      <input value={accountNumber} onChange={(e) => setAccountNumber(e.target.value)} required />
                    </label>
                  </div>
                )}
                {error && <div className="error">{error}</div>}
                <div className="row">
                  <button className="btn" type="submit" disabled={busy}>
                    {busy ? "Processing…" : `Pay $${inv.amount.toFixed(2)}`}
                  </button>
                  <button className="btn ghost" type="button" onClick={() => setPayingId(null)}>
                    Cancel
                  </button>
                </div>
              </form>
            );
          })()}
        </div>
      )}
    </div>
  );
}
