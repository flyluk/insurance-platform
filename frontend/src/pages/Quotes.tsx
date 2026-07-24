import { FormEvent, useEffect, useMemo, useState } from "react";
import api from "../api/client";
import PartyDetails, { PartyCell, PartySummary } from "../components/PartyDetails";
import { flattenRiskEntries } from "../utils/formatRisk";

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

type Quote = {
  id: string;
  party_id: string;
  insured_party_id?: string | null;
  product_code: string;
  plan_id?: string | null;
  rider_ids?: string[];
  status: string;
  annual_premium: number | null;
  owner?: PartySummary | null;
  insured?: PartySummary | null;
};

type RiskField = {
  key: string;
  label: string;
  type: "number" | "boolean" | "text" | "select";
  required?: boolean;
  default?: unknown;
  min?: number;
  max?: number;
  step?: number;
  options?: { value: string; label: string }[];
};

type ProductRider = {
  id: string;
  code: string;
  name: string;
  premium: number;
  effective_premium?: number;
  status: string;
};

type ProductPlan = {
  id: string;
  code: string;
  name: string;
  base_premium: number;
  effective_premium?: number;
  risk_schema?: RiskField[];
  riders: ProductRider[];
};

type Application = {
  id: string;
  application_number: string;
  quote_id: string;
  product_code: string;
  status: string;
  annual_premium: number;
  uw_decision: string | null;
  uw_reason?: string | null;
  policy_id?: string | null;
  policy_number?: string | null;
  risk_attributes?: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
  owner?: PartySummary | null;
  insured?: PartySummary | null;
};

function defaultsFromSchema(schema: RiskField[]): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const f of schema) {
    out[f.key] = f.default ?? (f.type === "boolean" ? false : f.type === "number" ? 0 : "");
  }
  return out;
}

export default function Quotes() {
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [apps, setApps] = useState<Application[]>([]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [dob, setDob] = useState("");
  const [address, setAddress] = useState("");
  const [idNumber, setIdNumber] = useState("");
  const [gender, setGender] = useState("");
  const [phone, setPhone] = useState("");
  const [searchHits, setSearchHits] = useState<Party[]>([]);
  const [searched, setSearched] = useState(false);
  const [searchBusy, setSearchBusy] = useState(false);
  const [selectedClient, setSelectedClient] = useState<Party | null>(null);
  const [product, setProduct] = useState("AUTO");
  const [plans, setPlans] = useState<ProductPlan[]>([]);
  const [planId, setPlanId] = useState("");
  const [selectedRiders, setSelectedRiders] = useState<string[]>([]);
  const [risk, setRisk] = useState<Record<string, unknown>>({});
  const [msg, setMsg] = useState("");
  const [selectedApp, setSelectedApp] = useState<Application | null>(null);

  async function refresh() {
    const [q, a] = await Promise.all([
      api.get("/nb/quotes"),
      api.get("/nb/applications"),
    ]);
    setQuotes(q.data);
    setApps(a.data);
  }

  useEffect(() => {
    refresh().catch(console.error);
  }, []);

  useEffect(() => {
    if (!selectedApp) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setSelectedApp(null);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedApp]);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    api
      .get("/products/plans", {
        params: { product_code: product, status: "PUBLISHED" },
        signal: controller.signal,
      })
      .then((r) => {
        // Abort alone does not stop .then for a request that already completed;
        // ignore stale responses after the user switches product.
        if (cancelled) return;
        setPlans(r.data);
        const first = r.data[0] as ProductPlan | undefined;
        setPlanId(first ? first.id : "");
        setSelectedRiders([]);
        setRisk(defaultsFromSchema(first?.risk_schema || []));
      })
      .catch((error) => {
        if (!cancelled && !controller.signal.aborted) console.error(error);
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [product]);

  const selectedPlan = useMemo(() => plans.find((p) => p.id === planId) || null, [plans, planId]);

  useEffect(() => {
    if (selectedPlan) {
      setRisk(defaultsFromSchema(selectedPlan.risk_schema || []));
      setSelectedRiders([]);
    }
  }, [planId]);

  function selectExisting(party: Party) {
    setSelectedClient(party);
    setMsg(`Using existing client ${party.full_name}`);
  }

  async function searchClients(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setMsg("Name is required to search");
      return;
    }
    setSearchBusy(true);
    setMsg("");
    try {
      const { data } = await api.get("/nb/clients/search", {
        params: { name: name.trim() },
      });
      const hits = Array.isArray(data) ? data : [];
      setSearchHits(hits);
      setSearched(true);
      if (!hits.length) {
        setMsg("No matching clients — create a new one below");
      } else {
        setMsg(`Found ${hits.length} client${hits.length === 1 ? "" : "s"}`);
      }
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err instanceof Error ? err.message : "Search failed");
      setMsg(String(detail));
    } finally {
      setSearchBusy(false);
    }
  }

  async function createNewClient(e: FormEvent) {
    e.preventDefault();
    const missing = [
      !name.trim() && "full name",
      !email.trim() && "email",
      !dob && "date of birth",
      !address.trim() && "address",
      !idNumber.trim() && "ID number",
      !gender && "gender",
      !phone.trim() && "contact number",
    ].filter(Boolean);
    if (missing.length) {
      setMsg(`Create new client requires: ${missing.join(", ")}`);
      return;
    }
    const { data } = await api.post("/nb/parties", {
      full_name: name.trim(),
      email: email.trim(),
      date_of_birth: dob,
      address: address.trim(),
      id_number: idNumber.trim(),
      gender,
      phone: phone.trim(),
    });
    setSelectedClient(data);
    setMsg(`Created client ${data.full_name}`);
    setSearchHits([]);
    setSearched(false);
    setName("");
    setEmail("");
    setDob("");
    setAddress("");
    setIdNumber("");
    setGender("");
    setPhone("");
    await refresh();
  }

  async function createQuote(e: FormEvent) {
    e.preventDefault();
    if (!selectedClient) {
      setMsg("Select a matched client or create a new client first");
      return;
    }
    if (!planId) {
      setMsg("Select a published basic plan");
      return;
    }
    await api.post("/nb/quotes", {
      party_id: selectedClient.id,
      insured_party_id: selectedClient.id,
      product_code: product,
      plan_id: planId,
      rider_ids: selectedRiders,
      risk_attributes: risk,
    });
    setMsg("Quote created");
    await refresh();
  }

  function toggleRider(id: string) {
    setSelectedRiders((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  function setRiskField(key: string, value: unknown) {
    setRisk((prev) => ({ ...prev, [key]: value }));
  }

  async function rate(id: string) {
    await api.post(`/nb/quotes/${id}/rate`);
    await refresh();
  }

  async function submit(id: string) {
    await api.post(`/nb/quotes/${id}/submit`);
    setMsg("Submitted to underwriting");
    await refresh();
  }

  const schema = selectedPlan?.risk_schema || [];

  return (
    <div className="stack">
      <div className="hero">
        <h1>New Business</h1>
        <p>Search or create clients, rate multi-product quotes, and submit applications.</p>
      </div>
      {msg && <div className="muted">{msg}</div>}
      <div className="grid-2">
        <div className="panel stack">
          <form className="stack" onSubmit={searchClients}>
            <h3>Client search</h3>
            <p className="muted" style={{ margin: 0 }}>
              Search existing clients by full name only.
            </p>
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
            <button className="btn" type="submit" disabled={searchBusy}>
              {searchBusy ? "Searching…" : "Search clients"}
            </button>
          </form>

          {searched && (
            <div className="stack">
              <h4 style={{ margin: 0 }}>
                Matches{searchHits.length ? ` (${searchHits.length})` : ""}
              </h4>
              {searchHits.length === 0 && <p className="muted">No existing clients matched.</p>}
              {searchHits.length > 0 && (
                <div className="client-match-scroll">
                  {searchHits.map((p) => (
                    <div key={p.id} className="party-card">
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
                          <span className="party-field-label">Address</span>
                          <span className="party-field-value">{p.address || "—"}</span>
                        </div>
                        {p.phone && (
                          <div className="party-field">
                            <span className="party-field-label">Phone</span>
                            <span className="party-field-value">{p.phone}</span>
                          </div>
                        )}
                      </div>
                      <div className="row" style={{ marginTop: "0.65rem" }}>
                        <button className="btn" type="button" onClick={() => selectExisting(p)}>
                          Use existing client
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <form className="stack" onSubmit={(e) => createNewClient(e).catch(console.error)}>
            <h4>Create new client</h4>
            <p className="muted" style={{ margin: 0 }}>
              Uses the full name from search. Email and all other details are required.
            </p>
            <label>
              Email
              <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
            </label>
            <label>
              Date of birth
              <input value={dob} onChange={(e) => setDob(e.target.value)} type="date" required />
            </label>
            <label>
              Address
              <textarea
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                rows={2}
                placeholder="Street, city, postal code"
                required
              />
            </label>
            <label>
              ID number
              <input
                value={idNumber}
                onChange={(e) => setIdNumber(e.target.value)}
                placeholder="National ID / passport"
                required
              />
            </label>
            <label>
              Gender
              <select value={gender} onChange={(e) => setGender(e.target.value)} required>
                <option value="">Select…</option>
                <option value="female">Female</option>
                <option value="male">Male</option>
              </select>
            </label>
            <label>
              Contact number
              <input
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                type="tel"
                placeholder="+1 555 0100"
                required
              />
            </label>
            <button className="btn warn" type="submit">
              Create new client
            </button>
          </form>
        </div>
        <form className="panel stack" onSubmit={createQuote}>
          <h3>New quote</h3>
          {selectedClient ? (
            <div className="party-card compact">
              <div className="party-name">{selectedClient.full_name}</div>
              <div className="party-fields">
                <div className="party-field">
                  <span className="party-field-label">Email</span>
                  <span className="party-field-value">{selectedClient.email || "—"}</span>
                </div>
                <div className="party-field">
                  <span className="party-field-label">DOB</span>
                  <span className="party-field-value">{selectedClient.date_of_birth || "—"}</span>
                </div>
                <div className="party-field">
                  <span className="party-field-label">Address</span>
                  <span className="party-field-value">{selectedClient.address || "—"}</span>
                </div>
              </div>
              <div className="row" style={{ marginTop: "0.5rem" }}>
                <button className="btn ghost" type="button" onClick={() => setSelectedClient(null)}>
                  Clear client
                </button>
              </div>
            </div>
          ) : (
            <p className="muted" style={{ margin: 0 }}>
              Choose a matched client or create a new client first.
            </p>
          )}
          <label>
            Product
            <select value={product} onChange={(e) => setProduct(e.target.value)}>
              <option value="AUTO">AUTO</option>
              <option value="HOME">HOME</option>
              <option value="LIFE">LIFE</option>
            </select>
          </label>
          <label>
            Basic plan
            <select
              value={planId}
              onChange={(e) => setPlanId(e.target.value)}
              required
            >
              {plans.length === 0 && <option value="">No published plans</option>}
              {plans.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} (${(p.effective_premium ?? p.base_premium).toFixed(0)})
                </option>
              ))}
            </select>
          </label>
          {selectedPlan && selectedPlan.riders.filter((r) => r.status === "PUBLISHED").length > 0 && (
            <div className="stack">
              <span className="muted">Optional riders</span>
              {selectedPlan.riders
                .filter((r) => r.status === "PUBLISHED")
                .map((r) => (
                  <label key={r.id} style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <input
                      type="checkbox"
                      checked={selectedRiders.includes(r.id)}
                      onChange={() => toggleRider(r.id)}
                      style={{ width: "auto" }}
                    />
                    {r.name} (+${(r.effective_premium ?? r.premium).toFixed(0)})
                  </label>
                ))}
            </div>
          )}

          {schema.map((field) => {
            if (field.type === "boolean") {
              return (
                <label key={field.key}>
                  {field.label}
                  <select
                    value={risk[field.key] ? "yes" : "no"}
                    onChange={(e) => setRiskField(field.key, e.target.value === "yes")}
                    required={field.required}
                  >
                    <option value="no">No</option>
                    <option value="yes">Yes</option>
                  </select>
                </label>
              );
            }
            if (field.type === "select" && field.options) {
              return (
                <label key={field.key}>
                  {field.label}
                  <select
                    value={String(risk[field.key] ?? "")}
                    onChange={(e) => setRiskField(field.key, e.target.value)}
                    required={field.required}
                  >
                    {field.options.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                </label>
              );
            }
            return (
              <label key={field.key}>
                {field.label}
                <input
                  type={field.type === "number" ? "number" : "text"}
                  min={field.min}
                  max={field.max}
                  step={field.step}
                  value={risk[field.key] as string | number | undefined}
                  onChange={(e) =>
                    setRiskField(
                      field.key,
                      field.type === "number" ? Number(e.target.value) : e.target.value
                    )
                  }
                  required={field.required}
                />
              </label>
            );
          })}

          <button className="btn" type="submit" disabled={!selectedClient}>
            Create quote
          </button>
        </form>
      </div>
      <div className="panel">
        <h3>Quotes</h3>
        <table>
          <thead>
            <tr>
              <th>Product</th>
              <th>Owner</th>
              <th>Insured</th>
              <th>Status</th>
              <th>Premium</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {quotes.map((q) => (
              <tr key={q.id}>
                <td>{q.product_code}</td>
                <td><PartyCell party={q.owner} /></td>
                <td><PartyCell party={q.insured} /></td>
                <td>
                  <span className="badge">{q.status}</span>
                </td>
                <td>{q.annual_premium ?? "—"}</td>
                <td className="row">
                  {q.status === "DRAFT" && (
                    <button className="btn ghost" type="button" onClick={() => rate(q.id)}>
                      Rate
                    </button>
                  )}
                  {q.status === "RATED" && (
                    <button className="btn" type="button" onClick={() => submit(q.id)}>
                      Submit
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="panel">
        <h3>Applications</h3>
        <table>
          <thead>
            <tr>
              <th>Application</th>
              <th>Product</th>
              <th>Owner</th>
              <th>Insured</th>
              <th>Status</th>
              <th>UW</th>
              <th>Premium</th>
              <th>Policy</th>
            </tr>
          </thead>
          <tbody>
            {apps.map((a) => (
              <tr
                key={a.id}
                className="clickable-row"
                onClick={() => setSelectedApp(a)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setSelectedApp(a);
                  }
                }}
                tabIndex={0}
                role="button"
                aria-label={`View application ${a.application_number}`}
              >
                <td>
                  <span className="linkish">{a.application_number}</span>
                </td>
                <td>{a.product_code}</td>
                <td><PartyCell party={a.owner} /></td>
                <td><PartyCell party={a.insured} /></td>
                <td>
                  <span className="badge">{a.status}</span>
                </td>
                <td>{a.uw_decision || "—"}</td>
                <td>{a.annual_premium}</td>
                <td>{a.policy_number || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selectedApp && (
        <div
          className="modal-backdrop"
          onClick={() => setSelectedApp(null)}
          role="presentation"
        >
          <div
            className="modal-panel stack"
            role="dialog"
            aria-modal="true"
            aria-labelledby="app-detail-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="row" style={{ justifyContent: "space-between" }}>
              <h3 id="app-detail-title" style={{ margin: 0 }}>
                {selectedApp.application_number}
              </h3>
              <button className="btn ghost" type="button" onClick={() => setSelectedApp(null)}>
                Close
              </button>
            </div>
            <div className="detail-grid">
              <div className="detail-row">
                <span className="muted">Product</span>
                <strong>{selectedApp.product_code}</strong>
              </div>
              <div className="detail-row">
                <span className="muted">Status</span>
                <span className="badge">{selectedApp.status}</span>
              </div>
              <div className="detail-row">
                <span className="muted">UW decision</span>
                <strong>{selectedApp.uw_decision || "—"}</strong>
              </div>
              <div className="detail-row">
                <span className="muted">UW reason</span>
                <strong>{selectedApp.uw_reason || "—"}</strong>
              </div>
              <div className="detail-row">
                <span className="muted">Annual premium</span>
                <strong>${Number(selectedApp.annual_premium).toFixed(2)}</strong>
              </div>
              <div className="detail-row">
                <span className="muted">Policy</span>
                <strong className="mono">{selectedApp.policy_number || "—"}</strong>
              </div>
              {selectedApp.created_at && (
                <div className="detail-row">
                  <span className="muted">Submitted</span>
                  <strong>{selectedApp.created_at.slice(0, 19).replace("T", " ")}</strong>
                </div>
              )}
            </div>
            <h4>Parties</h4>
            <div className="party-pair">
              <PartyDetails role="Owner" party={selectedApp.owner} />
              <PartyDetails role="Insured" party={selectedApp.insured} />
            </div>
            <h4>Risk attributes</h4>
            <div className="detail-grid">
              {selectedApp.risk_attributes && Object.keys(selectedApp.risk_attributes).length
                ? flattenRiskEntries(selectedApp.risk_attributes).map((row) => (
                    <div key={row.key} className="detail-row">
                      <span className="muted">{row.label}</span>
                      <strong className="risk-value">{row.value}</strong>
                    </div>
                  ))
                : (
                  <span className="muted">None</span>
                )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
