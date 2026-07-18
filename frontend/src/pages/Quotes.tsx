import { FormEvent, useEffect, useMemo, useState } from "react";
import api from "../api/client";

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
  product_code: string;
  plan_id?: string | null;
  rider_ids?: string[];
  status: string;
  annual_premium: number | null;
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
  quote_id: string;
  product_code: string;
  status: string;
  annual_premium: number;
  uw_decision: string | null;
};

function defaultsFromSchema(schema: RiskField[]): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const f of schema) {
    out[f.key] = f.default ?? (f.type === "boolean" ? false : f.type === "number" ? 0 : "");
  }
  return out;
}

export default function Quotes() {
  const [parties, setParties] = useState<Party[]>([]);
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [apps, setApps] = useState<Application[]>([]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [dob, setDob] = useState("");
  const [address, setAddress] = useState("");
  const [idNumber, setIdNumber] = useState("");
  const [gender, setGender] = useState("");
  const [phone, setPhone] = useState("");
  const [partyId, setPartyId] = useState("");
  const [product, setProduct] = useState("AUTO");
  const [plans, setPlans] = useState<ProductPlan[]>([]);
  const [planId, setPlanId] = useState("");
  const [selectedRiders, setSelectedRiders] = useState<string[]>([]);
  const [risk, setRisk] = useState<Record<string, unknown>>({});
  const [msg, setMsg] = useState("");

  async function refresh() {
    const [p, q, a] = await Promise.all([
      api.get("/nb/parties"),
      api.get("/nb/quotes"),
      api.get("/nb/applications"),
    ]);
    setParties(p.data);
    setQuotes(q.data);
    setApps(a.data);
    if (!partyId && p.data[0]) setPartyId(p.data[0].id);
  }

  useEffect(() => {
    refresh().catch(console.error);
  }, []);

  useEffect(() => {
    api
      .get("/products/plans", { params: { product_code: product, status: "PUBLISHED" } })
      .then((r) => {
        setPlans(r.data);
        const first = r.data[0] as ProductPlan | undefined;
        setPlanId(first ? first.id : "");
        setSelectedRiders([]);
        setRisk(defaultsFromSchema(first?.risk_schema || []));
      })
      .catch(console.error);
  }, [product]);

  const selectedPlan = useMemo(() => plans.find((p) => p.id === planId) || null, [plans, planId]);

  useEffect(() => {
    if (selectedPlan) {
      setRisk(defaultsFromSchema(selectedPlan.risk_schema || []));
      setSelectedRiders([]);
    }
  }, [planId]);

  async function createParty(e: FormEvent) {
    e.preventDefault();
    await api.post("/nb/parties", {
      full_name: name,
      email,
      date_of_birth: dob || null,
      address: address || null,
      id_number: idNumber || null,
      gender: gender || null,
      phone: phone || null,
    });
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
    if (!planId) {
      setMsg("Select a published basic plan");
      return;
    }
    await api.post("/nb/quotes", {
      party_id: partyId,
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
        <p>Create parties, rate multi-product quotes, and submit applications.</p>
      </div>
      {msg && <div className="muted">{msg}</div>}
      <div className="grid-2">
        <form className="panel stack" onSubmit={createParty}>
          <h3>New party</h3>
          <label>
            Full name
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <label>
            Email
            <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
          </label>
          <label>
            Date of birth
            <input value={dob} onChange={(e) => setDob(e.target.value)} type="date" />
          </label>
          <label>
            Address
            <textarea
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              rows={2}
              placeholder="Street, city, postal code"
            />
          </label>
          <label>
            ID number
            <input value={idNumber} onChange={(e) => setIdNumber(e.target.value)} placeholder="National ID / passport" />
          </label>
          <label>
            Gender
            <select value={gender} onChange={(e) => setGender(e.target.value)}>
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
            />
          </label>
          <button className="btn" type="submit">
            Save party
          </button>
        </form>
        <form className="panel stack" onSubmit={createQuote}>
          <h3>New quote</h3>
          <label>
            Party
            <select value={partyId} onChange={(e) => setPartyId(e.target.value)} required>
              {parties.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.full_name}
                </option>
              ))}
            </select>
          </label>
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

          <button className="btn" type="submit">
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
              <th>Status</th>
              <th>Premium</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {quotes.map((q) => (
              <tr key={q.id}>
                <td>{q.product_code}</td>
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
              <th>Product</th>
              <th>Status</th>
              <th>UW</th>
              <th>Premium</th>
            </tr>
          </thead>
          <tbody>
            {apps.map((a) => (
              <tr key={a.id}>
                <td>{a.product_code}</td>
                <td>
                  <span className="badge">{a.status}</span>
                </td>
                <td>{a.uw_decision || "—"}</td>
                <td>{a.annual_premium}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
