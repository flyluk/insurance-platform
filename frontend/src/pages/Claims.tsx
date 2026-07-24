import { FormEvent, useEffect, useMemo, useState } from "react";
import api from "../api/client";
import Pagination, { usePagination } from "../components/Pagination";
import PartyDetails, { PartySummary } from "../components/PartyDetails";
import Tabs from "../components/Tabs";

type Party = {
  id: string;
  full_name: string;
  email: string;
  phone?: string | null;
  date_of_birth?: string | null;
  address?: string | null;
  id_number?: string | null;
  gender?: string | null;
};

type Policy = {
  id: string;
  policy_number: string;
  party_id: string;
  product_code: string;
  status: string;
  annual_premium?: number;
  effective_date?: string;
  expiry_date?: string;
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
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [idNumber, setIdNumber] = useState("");
  const [dob, setDob] = useState("");
  const [searchHits, setSearchHits] = useState<Party[]>([]);
  const [searched, setSearched] = useState(false);
  const [searchBusy, setSearchBusy] = useState(false);
  const [selectedClient, setSelectedClient] = useState<Party | null>(null);
  const [clientPolicies, setClientPolicies] = useState<Policy[]>([]);
  const [policiesBusy, setPoliciesBusy] = useState(false);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [listTab, setListTab] = useState<"policies" | "claims" | "approvals">("policies");
  const [msg, setMsg] = useState("");
  const [settleAmount, setSettleAmount] = useState("1500");

  const [modalPolicy, setModalPolicy] = useState<Policy | null>(null);
  const [description, setDescription] = useState("Collision damage");
  const [lossDate, setLossDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [selectedClaimId, setSelectedClaimId] = useState<string | null>(null);
  const [docs, setDocs] = useState<ClaimDocument[]>([]);
  const [category, setCategory] = useState("PHOTO");
  const [file, setFile] = useState<File | null>(null);
  const [docError, setDocError] = useState("");
  const [docBusy, setDocBusy] = useState(false);
  const [openBusy, setOpenBusy] = useState(false);

  async function refreshClaims() {
    const { data } = await api.get("/claims");
    setClaims(data);
  }

  async function loadClientPolicies(partyId: string) {
    setPoliciesBusy(true);
    try {
      const { data } = await api.get("/policies", { params: { party_id: partyId } });
      setClientPolicies(Array.isArray(data) ? data : []);
    } finally {
      setPoliciesBusy(false);
    }
  }

  async function loadDocs(claimId: string) {
    const { data } = await api.get(`/claims/${claimId}/documents`);
    setDocs(data);
  }

  useEffect(() => {
    refreshClaims().catch(console.error);
  }, []);

  useEffect(() => {
    if (!selectedClaimId) {
      setDocs([]);
      return;
    }
    loadDocs(selectedClaimId).catch(console.error);
  }, [selectedClaimId]);

  useEffect(() => {
    if (!modalPolicy) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") closeModal();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [modalPolicy]);

  const policyClaims = useMemo(
    () => (modalPolicy ? claims.filter((c) => c.policy_id === modalPolicy.id) : []),
    [claims, modalPolicy]
  );

  const pendingApprovals = useMemo(
    () => claims.filter((c) => c.status === "PENDING_APPROVAL"),
    [claims]
  );

  const policyPage = usePagination(clientPolicies);
  const claimPage = usePagination(claims);
  const approvalPage = usePagination(pendingApprovals);
  const docPage = usePagination(docs);
  const modalClaimPage = usePagination(policyClaims);

  const settleAmountNum = Number(settleAmount);
  const needsApproval = Number.isFinite(settleAmountNum) && settleAmountNum > 10000;

  async function searchClients(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setMsg("Name is required to search clients");
      return;
    }
    setSearchBusy(true);
    setMsg("");
    setSelectedClient(null);
    setClientPolicies([]);
    setListTab("policies");
    try {
      const params: Record<string, string> = { name: name.trim() };
      if (email.trim()) params.email = email.trim();
      if (idNumber.trim()) params.id_number = idNumber.trim();
      if (dob) params.date_of_birth = dob;
      const { data } = await api.get("/nb/clients/search", { params });
      const hits = Array.isArray(data) ? data : [];
      setSearchHits(hits);
      setSearched(true);
      setMsg(hits.length ? `Found ${hits.length} client${hits.length === 1 ? "" : "s"}` : "No matching clients");
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err instanceof Error ? err.message : "Search failed");
      setMsg(String(detail));
    } finally {
      setSearchBusy(false);
    }
  }

  async function selectClient(party: Party) {
    setSelectedClient(party);
    setMsg(`Selected client ${party.full_name}`);
    setListTab("policies");
    await loadClientPolicies(party.id);
  }

  function openPolicyModal(policy: Policy) {
    setModalPolicy(policy);
    setSelectedClaimId(null);
    setDocError("");
    setDescription("Collision damage");
    setLossDate(new Date().toISOString().slice(0, 10));
  }

  function closeModal() {
    setModalPolicy(null);
    setSelectedClaimId(null);
    setDocs([]);
    setFile(null);
    setDocError("");
  }

  async function openClaim(e: FormEvent) {
    e.preventDefault();
    if (!modalPolicy) return;
    setOpenBusy(true);
    try {
      const { data } = await api.post("/claims", {
        policy_id: modalPolicy.id,
        party_id: modalPolicy.party_id,
        product_code: modalPolicy.product_code,
        description,
        loss_date: lossDate,
        reserve_amount: 1000,
      });
      await refreshClaims();
      setSelectedClaimId(data.id);
      setMsg(`Opened claim ${data.claim_number}`);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err instanceof Error ? err.message : "Failed to open claim");
      setMsg(String(detail));
    } finally {
      setOpenBusy(false);
    }
  }

  async function settle(id: string, amount = settleAmountNum) {
    if (!Number.isFinite(amount) || amount <= 0) {
      setMsg("Enter a valid settlement amount");
      return;
    }
    const { data } = await api.post(`/claims/${id}/settle`, { settlement_amount: amount });
    await refreshClaims();
    if (data.status === "PENDING_APPROVAL") {
      setMsg(`Settlement $${amount.toFixed(2)} submitted for approval (over $10,000)`);
      setListTab("approvals");
    } else {
      setMsg(`Settled claim for $${amount.toFixed(2)}`);
    }
  }

  async function approve(id: string) {
    const { data } = await api.post(`/claims/${id}/approve`);
    await refreshClaims();
    setMsg(`Approved settlement for ${data.claim_number}`);
  }

  async function rejectApproval(id: string) {
    await api.post(`/claims/${id}/reject-approval`);
    await refreshClaims();
    setMsg("Settlement approval rejected");
  }

  async function deny(id: string) {
    await api.post(`/claims/${id}/deny`);
    await refreshClaims();
  }

  function claimActions(c: Claim) {
    if (c.status === "PENDING_APPROVAL") {
      return (
        <div className="row">
          <button className="btn" type="button" onClick={() => approve(c.id).catch(console.error)}>
            Approve
          </button>
          <button className="btn ghost" type="button" onClick={() => rejectApproval(c.id).catch(console.error)}>
            Reject
          </button>
          <button className="btn danger" type="button" onClick={() => deny(c.id).catch(console.error)}>
            Deny claim
          </button>
        </div>
      );
    }
    if (["SETTLED", "DENIED"].includes(c.status)) return null;
    return (
      <div className="row">
        <button className="btn" type="button" onClick={() => settle(c.id).catch(console.error)}>
          {needsApproval ? "Submit for approval" : `Settle $${settleAmountNum || 0}`}
        </button>
        <button className="btn danger" type="button" onClick={() => deny(c.id).catch(console.error)}>
          Deny
        </button>
      </div>
    );
  }

  async function uploadDoc(e: FormEvent) {
    e.preventDefault();
    if (!selectedClaimId || !file) return;
    setDocBusy(true);
    setDocError("");
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("category", category);
      await api.post(`/claims/${selectedClaimId}/documents`, form);
      setFile(null);
      await loadDocs(selectedClaimId);
      await refreshClaims();
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
    if (!selectedClaimId) return;
    const res = await api.get(`/claims/${selectedClaimId}/documents/${doc.id}`, { responseType: "blob" });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = doc.filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function deleteDoc(doc: ClaimDocument) {
    if (!selectedClaimId) return;
    await api.delete(`/claims/${selectedClaimId}/documents/${doc.id}`);
    await loadDocs(selectedClaimId);
    await refreshClaims();
  }

  const selectedClaim = claims.find((c) => c.id === selectedClaimId) || null;

  return (
    <div className="stack">
      <div className="hero">
        <h1>Claims</h1>
        <p>Search a client, select their policy, then open and handle the claim.</p>
      </div>
      {msg && <div className="muted">{msg}</div>}

      <form className="panel stack" onSubmit={searchClients}>
        <h3>Client search</h3>
        <p className="muted" style={{ margin: 0 }}>
          Name is required. Email, ID number, and date of birth are optional filters.
        </p>
        <div className="grid-2">
          <label>
            Full name
            <input
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                setSearched(false);
                setSearchHits([]);
              }}
              required
            />
          </label>
          <label>
            Email <span className="muted">(optional)</span>
            <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" />
          </label>
          <label>
            ID number <span className="muted">(optional)</span>
            <input value={idNumber} onChange={(e) => setIdNumber(e.target.value)} />
          </label>
          <label>
            Date of birth <span className="muted">(optional)</span>
            <input value={dob} onChange={(e) => setDob(e.target.value)} type="date" />
          </label>
        </div>
        <button className="btn" type="submit" disabled={searchBusy}>
          {searchBusy ? "Searching…" : "Search clients"}
        </button>

        {searched && (
          <div className="stack">
            <h4 style={{ margin: 0 }}>
              Matches{searchHits.length ? ` (${searchHits.length})` : ""}
            </h4>
            {searchHits.length === 0 && <p className="muted">No matching clients.</p>}
            {searchHits.length > 0 && (
              <div className="client-match-scroll">
                {searchHits.map((p) => (
                  <div
                    key={p.id}
                    className={`party-card${selectedClient?.id === p.id ? " compact" : ""}`}
                    style={
                      selectedClient?.id === p.id
                        ? { outline: "2px solid rgba(15, 106, 86, 0.35)" }
                        : undefined
                    }
                  >
                    <div className="party-name">{p.full_name}</div>
                    <div className="party-fields">
                      <div className="party-field">
                        <span className="party-field-label">Email</span>
                        <span className="party-field-value">{p.email || "—"}</span>
                      </div>
                      <div className="party-field">
                        <span className="party-field-label">DOB</span>
                        <span className="party-field-value">{p.date_of_birth || "—"}</span>
                      </div>
                      <div className="party-field">
                        <span className="party-field-label">ID</span>
                        <span className="party-field-value">{p.id_number || "—"}</span>
                      </div>
                      <div className="party-field">
                        <span className="party-field-label">Address</span>
                        <span className="party-field-value">{p.address || "—"}</span>
                      </div>
                    </div>
                    <div className="row" style={{ marginTop: "0.65rem" }}>
                      <button className="btn" type="button" onClick={() => selectClient(p).catch(console.error)}>
                        {selectedClient?.id === p.id ? "Selected" : "Select client"}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </form>

      <div className="panel">
        <Tabs
          active={listTab}
          onChange={(id) => setListTab(id as "policies" | "claims" | "approvals")}
          tabs={[
            {
              id: "policies",
              label: selectedClient ? `${selectedClient.full_name} policies` : "Client policies",
              count: clientPolicies.length,
            },
            { id: "claims", label: "All claims", count: claims.length },
            { id: "approvals", label: "Approvals", count: pendingApprovals.length },
          ]}
        />

        {(listTab === "claims" || listTab === "approvals" || (listTab === "policies" && selectedClient)) && (
          <label style={{ maxWidth: "14rem" }}>
            Settlement amount
            <input
              type="number"
              min={1}
              step={1}
              value={settleAmount}
              onChange={(e) => setSettleAmount(e.target.value)}
            />
            <span className="muted">
              {needsApproval
                ? "Over $10,000 — settle will request approval"
                : "Amounts over $10,000 require approval"}
            </span>
          </label>
        )}

        {listTab === "policies" && (
          <>
            {!selectedClient && (
              <p className="muted">Select a matched client to list their policies.</p>
            )}
            {selectedClient && policiesBusy && <p className="muted">Loading policies…</p>}
            {selectedClient && !policiesBusy && (
              <>
                <table>
                  <thead>
                    <tr>
                      <th>Policy</th>
                      <th>Product</th>
                      <th>Status</th>
                      <th>Owner</th>
                      <th>Insured</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {policyPage.pageItems.map((p) => (
                      <tr
                        key={p.id}
                        className="clickable-row"
                        onClick={() => openPolicyModal(p)}
                      >
                        <td>
                          <span className="linkish">{p.policy_number}</span>
                        </td>
                        <td>{p.product_code}</td>
                        <td>
                          <span className={`badge ${p.status !== "ACTIVE" ? "bad" : ""}`}>{p.status}</span>
                        </td>
                        <td>{p.owner?.full_name || "—"}</td>
                        <td>{p.insured?.full_name || "—"}</td>
                        <td>
                          <button
                            className="btn ghost"
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              openPolicyModal(p);
                            }}
                          >
                            Open claim
                          </button>
                        </td>
                      </tr>
                    ))}
                    {!clientPolicies.length && (
                      <tr>
                        <td colSpan={6} className="muted">
                          No policies for this client.
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
              </>
            )}
          </>
        )}

        {listTab === "claims" && (
          <>
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
                {claimPage.pageItems.map((c) => (
                  <tr key={c.id}>
                    <td>{c.claim_number}</td>
                    <td>{c.product_code}</td>
                    <td>{c.owner?.full_name || "—"}</td>
                    <td>{c.insured?.full_name || "—"}</td>
                    <td>
                      <span className="badge">{c.status}</span>
                    </td>
                    <td>{c.document_count ?? 0}</td>
                    <td>{c.reserve_amount}</td>
                    <td>{c.settlement_amount ?? "—"}</td>
                    <td onClick={(e) => e.stopPropagation()}>{claimActions(c)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pagination
              page={claimPage.page}
              totalPages={claimPage.totalPages}
              total={claimPage.total}
              pageSize={claimPage.pageSize}
              onPageChange={claimPage.setPage}
              onPageSizeChange={claimPage.setPageSize}
            />
          </>
        )}

        {listTab === "approvals" && (
          <>
            <p className="muted" style={{ marginTop: 0 }}>
              Settlements over $10,000 wait here until approved.
            </p>
            <table>
              <thead>
                <tr>
                  <th>Claim</th>
                  <th>Product</th>
                  <th>Proposed amount</th>
                  <th>Owner</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {approvalPage.pageItems.map((c) => (
                  <tr key={c.id}>
                    <td>{c.claim_number}</td>
                    <td>{c.product_code}</td>
                    <td>${Number(c.settlement_amount || 0).toFixed(2)}</td>
                    <td>{c.owner?.full_name || "—"}</td>
                    <td>{claimActions(c)}</td>
                  </tr>
                ))}
                {!pendingApprovals.length && (
                  <tr>
                    <td colSpan={5} className="muted">
                      No settlements awaiting approval.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
            <Pagination
              page={approvalPage.page}
              totalPages={approvalPage.totalPages}
              total={approvalPage.total}
              pageSize={approvalPage.pageSize}
              onPageChange={approvalPage.setPage}
              onPageSizeChange={approvalPage.setPageSize}
            />
          </>
        )}
      </div>

      {modalPolicy && (
        <div className="modal-backdrop" onClick={closeModal} role="presentation">
          <div
            className="modal-panel stack"
            role="dialog"
            aria-modal="true"
            aria-labelledby="claim-policy-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="row" style={{ justifyContent: "space-between" }}>
              <h3 id="claim-policy-title" style={{ margin: 0 }}>
                {modalPolicy.policy_number}
              </h3>
              <button className="btn ghost" type="button" onClick={closeModal}>
                Close
              </button>
            </div>

            <div className="detail-grid">
              <div className="detail-row">
                <span className="muted">Product</span>
                <strong>{modalPolicy.product_code}</strong>
              </div>
              <div className="detail-row">
                <span className="muted">Status</span>
                <span className={`badge ${modalPolicy.status !== "ACTIVE" ? "bad" : ""}`}>
                  {modalPolicy.status}
                </span>
              </div>
            </div>
            <div className="party-pair">
              <PartyDetails role="Owner" party={modalPolicy.owner} compact />
              <PartyDetails role="Insured" party={modalPolicy.insured} compact />
            </div>

            {modalPolicy.status === "ACTIVE" ? (
              <form className="stack" onSubmit={openClaim}>
                <h4>Open claim (FNOL)</h4>
                <label>
                  Loss date
                  <input value={lossDate} onChange={(e) => setLossDate(e.target.value)} type="date" required />
                </label>
                <label>
                  Description
                  <input value={description} onChange={(e) => setDescription(e.target.value)} required />
                </label>
                <button className="btn" type="submit" disabled={openBusy}>
                  {openBusy ? "Opening…" : "Open claim"}
                </button>
              </form>
            ) : (
              <p className="muted">Only ACTIVE policies accept new claims.</p>
            )}

            <h4>Claims on this policy</h4>
            <table>
              <thead>
                <tr>
                  <th>Claim</th>
                  <th>Status</th>
                  <th>Docs</th>
                  <th>Reserve</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {modalClaimPage.pageItems.map((c) => (
                  <tr
                    key={c.id}
                    className={selectedClaimId === c.id ? "row-selected" : undefined}
                    style={{ cursor: "pointer" }}
                    onClick={() => setSelectedClaimId(c.id)}
                  >
                    <td>{c.claim_number}</td>
                    <td>
                      <span className="badge">{c.status}</span>
                    </td>
                    <td>{c.document_count ?? 0}</td>
                    <td>{c.reserve_amount}</td>
                    <td onClick={(e) => e.stopPropagation()}>{claimActions(c)}</td>
                  </tr>
                ))}
                {!policyClaims.length && (
                  <tr>
                    <td colSpan={5} className="muted">
                      No claims on this policy yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
            <Pagination
              page={modalClaimPage.page}
              totalPages={modalClaimPage.totalPages}
              total={modalClaimPage.total}
              pageSize={modalClaimPage.pageSize}
              onPageChange={modalClaimPage.setPage}
              onPageSizeChange={modalClaimPage.setPageSize}
            />

            {selectedClaim && (
              <div className="stack">
                <h4>Documents · {selectedClaim.claim_number}</h4>
                {!["SETTLED", "DENIED"].includes(selectedClaim.status) && (
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
                    {docPage.pageItems.map((d) => (
                      <tr key={d.id}>
                        <td>{d.filename}</td>
                        <td>
                          <span className="badge">{d.category}</span>
                        </td>
                        <td>{formatBytes(d.size_bytes)}</td>
                        <td className="row">
                          <button className="btn ghost" type="button" onClick={() => downloadDoc(d)}>
                            Download
                          </button>
                          {!["SETTLED", "DENIED"].includes(selectedClaim.status) && (
                            <button className="btn danger" type="button" onClick={() => deleteDoc(d)}>
                              Delete
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                    {!docs.length && (
                      <tr>
                        <td colSpan={4} className="muted">
                          No documents yet.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
                <Pagination
                  page={docPage.page}
                  totalPages={docPage.totalPages}
                  total={docPage.total}
                  pageSize={docPage.pageSize}
                  onPageChange={docPage.setPage}
                  onPageSizeChange={docPage.setPageSize}
                />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
