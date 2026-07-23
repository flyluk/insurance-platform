import { FormEvent, useEffect, useState } from "react";
import api from "../api/client";
import PartyDetails, { PartyCell, PartySummary, partyLabel } from "../components/PartyDetails";

type Policy = {
  id: string;
  policy_number: string;
  party_id: string;
  product_code: string;
  status: string;
  owner?: PartySummary | null;
  insured?: PartySummary | null;
};
type Claim = {
  id: string;
  claim_number: string;
  policy_id: string;
  product_code: string;
  status: string;
  reserve_amount: number;
  settlement_amount: number | null;
  description: string;
  document_count?: number;
  owner?: PartySummary | null;
  insured?: PartySummary | null;
};
type ClaimDocument = {
  id: string;
  filename: string;
  content_type: string;
  category: string;
  size_bytes: number;
  uploaded_by: string | null;
  created_at: string;
};

const CATEGORIES = ["PHOTO", "POLICE_REPORT", "MEDICAL", "INVOICE", "OTHER"];

function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export default function Claims() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [policyId, setPolicyId] = useState("");
  const [description, setDescription] = useState("Collision damage");
  const [lossDate, setLossDate] = useState("2026-07-01");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [docs, setDocs] = useState<ClaimDocument[]>([]);
  const [category, setCategory] = useState("PHOTO");
  const [file, setFile] = useState<File | null>(null);
  const [docError, setDocError] = useState("");
  const [docBusy, setDocBusy] = useState(false);

  async function refresh() {
    const [p, c] = await Promise.all([api.get("/policies"), api.get("/claims")]);
    setPolicies(p.data.filter((x: Policy) => x.status === "ACTIVE"));
    setClaims(c.data);
    if (!policyId && p.data[0]) setPolicyId(p.data[0].id);
  }

  async function loadDocs(claimId: string) {
    const { data } = await api.get(`/claims/${claimId}/documents`);
    setDocs(data);
  }

  useEffect(() => {
    refresh().catch(console.error);
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setDocs([]);
      return;
    }
    loadDocs(selectedId).catch(console.error);
  }, [selectedId]);

  async function openClaim(e: FormEvent) {
    e.preventDefault();
    const policy = policies.find((p) => p.id === policyId);
    if (!policy) return;
    const { data } = await api.post("/claims", {
      policy_id: policy.id,
      party_id: policy.party_id,
      product_code: policy.product_code,
      description,
      loss_date: lossDate,
      reserve_amount: 1000,
    });
    await refresh();
    setSelectedId(data.id);
  }

  async function settle(id: string) {
    await api.post(`/claims/${id}/settle`, { settlement_amount: 1500 });
    await refresh();
  }

  async function deny(id: string) {
    await api.post(`/claims/${id}/deny`);
    await refresh();
  }

  async function uploadDoc(e: FormEvent) {
    e.preventDefault();
    if (!selectedId || !file) return;
    setDocBusy(true);
    setDocError("");
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("category", category);
      await api.post(`/claims/${selectedId}/documents`, form);
      setFile(null);
      await loadDocs(selectedId);
      await refresh();
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err instanceof Error ? err.message : "Upload failed");
      setDocError(String(detail));
    } finally {
      setDocBusy(false);
    }
  }

  async function downloadDoc(doc: ClaimDocument) {
    if (!selectedId) return;
    const res = await api.get(`/claims/${selectedId}/documents/${doc.id}`, { responseType: "blob" });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = doc.filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function deleteDoc(doc: ClaimDocument) {
    if (!selectedId) return;
    await api.delete(`/claims/${selectedId}/documents/${doc.id}`);
    await loadDocs(selectedId);
    await refresh();
  }

  const selected = claims.find((c) => c.id === selectedId) || null;

  return (
    <div className="stack">
      <div className="hero">
        <h1>Claims</h1>
        <p>FNOL, evidence documents, reserves, settlement, and denial workflows.</p>
      </div>
      <form className="panel stack" onSubmit={openClaim}>
        <h3>Open claim (FNOL)</h3>
        <label>
          Policy
          <select value={policyId} onChange={(e) => setPolicyId(e.target.value)}>
            {policies.map((p) => (
              <option key={p.id} value={p.id}>
                {p.policy_number} ({p.product_code}) · owner {partyLabel(p.owner, p.party_id)}
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
              <th>Owner</th>
              <th>Insured</th>
              <th>Status</th>
              <th>Docs</th>
              <th>Reserve</th>
              <th>Settlement</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {claims.map((c) => (
              <tr
                key={c.id}
                style={{ cursor: "pointer", background: selectedId === c.id ? "rgba(44,74,124,0.06)" : undefined }}
                onClick={() => setSelectedId(c.id)}
              >
                <td>{c.claim_number}</td>
                <td>{c.product_code}</td>
                <td><PartyCell party={c.owner} /></td>
                <td><PartyCell party={c.insured} /></td>
                <td>
                  <span className="badge">{c.status}</span>
                </td>
                <td>{c.document_count ?? 0}</td>
                <td>{c.reserve_amount}</td>
                <td>{c.settlement_amount ?? "—"}</td>
                <td className="row">
                  {!["SETTLED", "DENIED"].includes(c.status) && (
                    <>
                      <button
                        className="btn"
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          settle(c.id);
                        }}
                      >
                        Settle $1500
                      </button>
                      <button
                        className="btn danger"
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          deny(c.id);
                        }}
                      >
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

      {selected && (
        <div className="panel stack">
          <h3>
            Documents · {selected.claim_number}
          </h3>
          <div className="party-pair">
            <PartyDetails role="Owner" party={selected.owner} compact />
            <PartyDetails role="Insured" party={selected.insured} compact />
          </div>
          <form className="row" onSubmit={uploadDoc} style={{ alignItems: "flex-end" }}>
            <label>
              Category
              <select value={category} onChange={(e) => setCategory(e.target.value)}>
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </label>
            <label>
              File
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp,application/pdf,text/plain"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </label>
            <button className="btn" type="submit" disabled={!file || docBusy}>
              {docBusy ? "Uploading…" : "Upload"}
            </button>
          </form>
          {docError && <div className="error">{docError}</div>}
          <table>
            <thead>
              <tr>
                <th>File</th>
                <th>Category</th>
                <th>Size</th>
                <th>Uploaded by</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id}>
                  <td>{d.filename}</td>
                  <td>
                    <span className="badge">{d.category}</span>
                  </td>
                  <td>{formatBytes(d.size_bytes)}</td>
                  <td>{d.uploaded_by || "—"}</td>
                  <td className="row">
                    <button className="btn ghost" type="button" onClick={() => downloadDoc(d)}>
                      Download
                    </button>
                    <button className="btn danger" type="button" onClick={() => deleteDoc(d)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
              {!docs.length && (
                <tr>
                  <td colSpan={5} className="muted">
                    No documents yet. Upload photos, police reports, or invoices.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
