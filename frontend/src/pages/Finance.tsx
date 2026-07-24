import { useEffect, useState } from "react";
import api from "../api/client";
import Pagination, { usePagination } from "../components/Pagination";
import { PartyCell, PartySummary } from "../components/PartyDetails";
import Tabs from "../components/Tabs";

type Invoice = {
  id: string;
  invoice_number: string;
  invoice_type: string;
  amount: number;
  status: string;
  description: string | null;
  owner?: PartySummary | null;
  party_id?: string;
};
type Disbursement = {
  id: string;
  claim_number: string;
  amount: number;
  status: string;
  owner?: PartySummary | null;
  party_id?: string;
};
type Journal = {
  id: string;
  memo: string;
  reference_type: string;
  lines: { account: string; debit: number; credit: number }[];
};

type FinanceTab = "invoices" | "disbursements" | "ledger";

export default function Finance() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [disbursements, setDisbursements] = useState<Disbursement[]>([]);
  const [ledger, setLedger] = useState<Journal[]>([]);
  const [tab, setTab] = useState<FinanceTab>("invoices");

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

  const invoicePage = usePagination(invoices);
  const disbursementPage = usePagination(disbursements);
  const ledgerPage = usePagination(ledger);

  return (
    <div className="stack">
      <div className="hero">
        <h1>Finance</h1>
        <p>Premium invoices, credits/refunds, claim disbursements, and GL entries.</p>
      </div>
      <div className="panel">
        <Tabs
          active={tab}
          onChange={(id) => setTab(id as FinanceTab)}
          tabs={[
            { id: "invoices", label: "Invoices", count: invoices.length },
            { id: "disbursements", label: "Disbursements", count: disbursements.length },
            { id: "ledger", label: "Ledger", count: ledger.length },
          ]}
        />

        {tab === "invoices" && (
          <>
            <table>
              <thead>
                <tr>
                  <th>Number</th>
                  <th>Owner</th>
                  <th>Type</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {invoicePage.pageItems.map((inv) => (
                  <tr key={inv.id}>
                    <td>{inv.invoice_number}</td>
                    <td><PartyCell party={inv.owner} /></td>
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
            <Pagination
              page={invoicePage.page}
              totalPages={invoicePage.totalPages}
              total={invoicePage.total}
              pageSize={invoicePage.pageSize}
              onPageChange={invoicePage.setPage}
              onPageSizeChange={invoicePage.setPageSize}
            />
          </>
        )}

        {tab === "disbursements" && (
          <>
            <table>
              <thead>
                <tr>
                  <th>Claim</th>
                  <th>Owner</th>
                  <th>Amount</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {disbursementPage.pageItems.map((d) => (
                  <tr key={d.id}>
                    <td>{d.claim_number}</td>
                    <td><PartyCell party={d.owner} /></td>
                    <td>{d.amount}</td>
                    <td>
                      <span className="badge">{d.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pagination
              page={disbursementPage.page}
              totalPages={disbursementPage.totalPages}
              total={disbursementPage.total}
              pageSize={disbursementPage.pageSize}
              onPageChange={disbursementPage.setPage}
              onPageSizeChange={disbursementPage.setPageSize}
            />
          </>
        )}

        {tab === "ledger" && (
          <>
            <table>
              <thead>
                <tr>
                  <th>Memo</th>
                  <th>Lines</th>
                </tr>
              </thead>
              <tbody>
                {ledgerPage.pageItems.map((j) => (
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
            <Pagination
              page={ledgerPage.page}
              totalPages={ledgerPage.totalPages}
              total={ledgerPage.total}
              pageSize={ledgerPage.pageSize}
              onPageChange={ledgerPage.setPage}
              onPageSizeChange={ledgerPage.setPageSize}
            />
          </>
        )}
      </div>
    </div>
  );
}
