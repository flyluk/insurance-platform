import { FormEvent, useEffect, useState } from "react";
import api from "../api/client";

type Party = { id: string; full_name: string; email: string };
type Quote = {
  id: string;
  party_id: string;
  product_code: string;
  status: string;
  annual_premium: number | null;
};
type Application = {
  id: string;
  quote_id: string;
  product_code: string;
  status: string;
  annual_premium: number;
  uw_decision: string | null;
};

type AutoRisk = {
  vehicle_year: number;
  drivers: number;
  prior_claims: number;
  driver_age: number;
};

type HomeRisk = {
  property_value: number;
  year_built: number;
  flood_zone: boolean;
};

type LifeRisk = {
  insured_age: number;
  sum_insured: number;
  smoker: boolean;
};

const DEFAULT_AUTO: AutoRisk = {
  vehicle_year: 2022,
  drivers: 1,
  prior_claims: 0,
  driver_age: 34,
};

const DEFAULT_HOME: HomeRisk = {
  property_value: 320000,
  year_built: 1998,
  flood_zone: false,
};

const DEFAULT_LIFE: LifeRisk = {
  insured_age: 40,
  sum_insured: 400000,
  smoker: false,
};

export default function Quotes() {
  const [parties, setParties] = useState<Party[]>([]);
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [apps, setApps] = useState<Application[]>([]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [partyId, setPartyId] = useState("");
  const [product, setProduct] = useState("AUTO");
  const [autoRisk, setAutoRisk] = useState<AutoRisk>(DEFAULT_AUTO);
  const [homeRisk, setHomeRisk] = useState<HomeRisk>(DEFAULT_HOME);
  const [lifeRisk, setLifeRisk] = useState<LifeRisk>(DEFAULT_LIFE);
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

  async function createParty(e: FormEvent) {
    e.preventDefault();
    await api.post("/nb/parties", { full_name: name, email });
    setName("");
    setEmail("");
    await refresh();
  }

  function riskAttributes() {
    if (product === "HOME") return homeRisk;
    if (product === "LIFE") return lifeRisk;
    return autoRisk;
  }

  async function createQuote(e: FormEvent) {
    e.preventDefault();
    await api.post("/nb/quotes", {
      party_id: partyId,
      product_code: product,
      risk_attributes: riskAttributes(),
    });
    setMsg("Quote created");
    await refresh();
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

          {product === "AUTO" && (
            <>
              <label>
                Vehicle year
                <input
                  type="number"
                  min={1980}
                  max={2030}
                  value={autoRisk.vehicle_year}
                  onChange={(e) => setAutoRisk({ ...autoRisk, vehicle_year: Number(e.target.value) })}
                  required
                />
              </label>
              <label>
                Drivers
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={autoRisk.drivers}
                  onChange={(e) => setAutoRisk({ ...autoRisk, drivers: Number(e.target.value) })}
                  required
                />
              </label>
              <label>
                Prior claims
                <input
                  type="number"
                  min={0}
                  max={20}
                  value={autoRisk.prior_claims}
                  onChange={(e) => setAutoRisk({ ...autoRisk, prior_claims: Number(e.target.value) })}
                  required
                />
              </label>
              <label>
                Driver age
                <input
                  type="number"
                  min={16}
                  max={100}
                  value={autoRisk.driver_age}
                  onChange={(e) => setAutoRisk({ ...autoRisk, driver_age: Number(e.target.value) })}
                  required
                />
              </label>
            </>
          )}

          {product === "HOME" && (
            <>
              <label>
                Property value
                <input
                  type="number"
                  min={10000}
                  step={1000}
                  value={homeRisk.property_value}
                  onChange={(e) => setHomeRisk({ ...homeRisk, property_value: Number(e.target.value) })}
                  required
                />
              </label>
              <label>
                Year built
                <input
                  type="number"
                  min={1800}
                  max={2030}
                  value={homeRisk.year_built}
                  onChange={(e) => setHomeRisk({ ...homeRisk, year_built: Number(e.target.value) })}
                  required
                />
              </label>
              <label>
                Flood zone
                <select
                  value={homeRisk.flood_zone ? "yes" : "no"}
                  onChange={(e) => setHomeRisk({ ...homeRisk, flood_zone: e.target.value === "yes" })}
                >
                  <option value="no">No</option>
                  <option value="yes">Yes</option>
                </select>
              </label>
            </>
          )}

          {product === "LIFE" && (
            <>
              <label>
                Insured age
                <input
                  type="number"
                  min={18}
                  max={90}
                  value={lifeRisk.insured_age}
                  onChange={(e) => setLifeRisk({ ...lifeRisk, insured_age: Number(e.target.value) })}
                  required
                />
              </label>
              <label>
                Sum insured
                <input
                  type="number"
                  min={10000}
                  step={10000}
                  value={lifeRisk.sum_insured}
                  onChange={(e) => setLifeRisk({ ...lifeRisk, sum_insured: Number(e.target.value) })}
                  required
                />
              </label>
              <label>
                Smoker
                <select
                  value={lifeRisk.smoker ? "yes" : "no"}
                  onChange={(e) => setLifeRisk({ ...lifeRisk, smoker: e.target.value === "yes" })}
                >
                  <option value="no">No</option>
                  <option value="yes">Yes</option>
                </select>
              </label>
            </>
          )}

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
