import { FormEvent, useEffect, useState } from "react";
import api from "../api/client";
import { useAuth } from "../components/AuthContext";
import PartyDetails, { PartySummary, partyLabel } from "../components/PartyDetails";

type Policy = {
  id: string;
  policy_number: string;
  product_code: string;
  status: string;
  party_id: string;
  owner?: PartySummary | null;
  insured?: PartySummary | null;
};

type Claim = {
  id: string;
  claim_number: string;
  policy_id: string;
  product_code: string;
  status: string;
  description: string;
  loss_date: string;
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
  const { user } = useAuth();
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [policyId, setPolicyId] = useState("");
  const [description, setDescription] = useState("");
  const [lossDate, setLossDate] = useState(new Date().toISOString().slice(0, 10));
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [docs, setDocs] = useState<ClaimDocument[]>([]);
  const [category, setCategory] = useState("PHOTO");
  const [file, setFile] = useState<File | null>(null);
  const [docError, setDocError] = useState("");
  const [docBusy, setDocBusy] = useState(false);

  async function refresh() {
    const [p, c] = await Promise.all([api.get("/policies"), api.get("/claims")]);
    setPolicies(p.data);
    setClaims(c.data);
    const active = (p.data as Policy[]).find((x) => x.status === "ACTIVE");
    if (active && !policyId) setPolicyId(active.id);
  }

  async function loadDocs(claimId: string) {
    const { data } = await api.get(`/claims/${claimId}/documents`);
    setDocs(data);
  }

  useEffect(() => {
    refresh().catch(console.error);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setDocs([]);
      return;
    }
    loadDocs(selectedId).catch(console.error);
  }, [selectedId]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setSuccess("");
    const policy = policies.find((p) => p.id === policyId);
    if (!policy) {
      setError("Select a policy");
      setBusy(false);
      return;
    }
    try {
      const { data } = await api.post("/claims", {
        policy_id: policy.id,
        party_id: user?.party_id || policy.party_id,
        product_code: policy.product_code,
        description,
        loss_date: lossDate,
        reserve_amount: 0,
      });
      setSuccess(`Claim ${data.claim_number} submitted. You can attach photos or reports below.`);
      setDescription("");
      setSelectedId(data.id);
      await refresh();
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err instanceof Error ? err.message : "Unable to file claim");
      setError(String(detail));
    } finally {
      setBusy(false);
    }
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
      setSuccess("Document uploaded.");
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

  const activePolicies = policies.filter((p) => p.status === "ACTIVE");
  const selected = claims.find((c) => c.id === selectedId) || null;
  const canUpload = selected && !["SETTLED", "DENIED"].includes(selected.status);

  return (
    <div className="stack">
      <div className="hero">
        <h1>Claims</h1>
        <p>File a first notice of loss, attach evidence, and track open claims.</p>
      </div>
      <div className="grid-2">
        <form className="panel stack" onSubmit={onSubmit}>
          <h3>Report a loss</h3>
          <label>
            Policy
            <select value={policyId} onChange={(e) => setPolicyId(e.target.value)} required>
              <option value="">Select…</option>
              {activePolicies.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.policy_number} ({p.product_code}) · insured {partyLabel(p.insured)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Loss date
            <input type="date" value={lossDate} onChange={(e) => setLossDate(e.target.value)} required />
          </label>
          <label>
            What happened
            <textarea
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
              placeholder="Brief description of the loss"
            />
          </label>
          {error && <div className="error">{error}</div>}
          {success && <div className="success">{success}</div>}
          <button className="btn" type="submit" disabled={busy || !activePolicies.length}>
            {busy ? "Submitting…" : "Submit claim"}
          </button>
          {!activePolicies.length && <p className="muted">You need an active policy to file a claim.</p>}
        </form>
        <div className="panel">
          <h3>Your claims</h3>
          <table>
            <thead>
              <tr>
                <th>Number</th>
                <th>Line</th>
                <th>Status</th>
                <th>Docs</th>
              </tr>
            </thead>
            <tbody>
              {claims.map((c) => (
                <tr
                  key={c.id}
                  style={{ cursor: "pointer", background: selectedId === c.id ? "rgba(31,107,79,0.08)" : undefined }}
                  onClick={() => setSelectedId(c.id)}
                >
                  <td>
                    <div>{c.claim_number}</div>
                    <div className="muted">{c.description}</div>
                  </td>
                  <td>{c.product_code}</td>
                  <td>
                    <span className="badge">{c.status}</span>
                  </td>
                  <td>{c.document_count ?? 0}</td>
                </tr>
              ))}
              {!claims.length && (
                <tr>
                  <td colSpan={4} className="muted">
                    No claims filed yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {selected && (
        <div className="panel stack">
          <h3>Evidence · {selected.claim_number}</h3>
          <div className="party-pair">
            <PartyDetails role="Owner" party={selected.owner} compact />
            <PartyDetails role="Insured" party={selected.insured} compact />
          </div>
          <p className="muted">Upload photos, police reports, medical notes, or repair invoices (max 5 MB).</p>
          {canUpload ? (
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
          ) : (
            <p className="muted">This claim is closed; documents are view-only.</p>
          )}
          {docError && <div className="error">{docError}</div>}
          <table>
            <thead>
              <tr>
                <th>File</th>
                <th>Category</th>
                <th>Size</th>
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
                  <td>
                    <button className="btn ghost" type="button" onClick={() => downloadDoc(d)}>
                      Download
                    </button>
                  </td>
                </tr>
              ))}
              {!docs.length && (
                <tr>
                  <td colSpan={4} className="muted">
                    No evidence attached yet.
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
