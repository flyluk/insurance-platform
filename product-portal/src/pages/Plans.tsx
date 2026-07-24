import { FormEvent, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import api from "../api/client";
import Pagination, { usePagination } from "../components/Pagination";

type Rider = {
  id: string;
  product_code: string;
  code: string;
  name: string;
  premium: number;
  status: string;
};

type RiskField = {
  key: string;
  label: string;
  type: string;
  required?: boolean;
  default?: unknown;
  min?: number;
  max?: number;
  step?: number;
};

type RateVersion = {
  id: string;
  version_code: string;
  amount: number;
  effective_from: string;
  effective_to: string | null;
  status: string;
};

type Plan = {
  id: string;
  product_code: string;
  code: string;
  name: string;
  description: string | null;
  base_premium: number;
  status: string;
  risk_schema: RiskField[];
  uw_rules: { decline: unknown[]; refer: unknown[] };
  riders: Rider[];
};

const LINES = ["AUTO", "HOME", "LIFE"];
const FIELD_TYPES = ["number", "boolean", "text", "select"];

export default function Plans() {
  const [params, setParams] = useSearchParams();
  const line = (params.get("line") || "AUTO").toUpperCase();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [lineRiders, setLineRiders] = useState<Rider[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [msg, setMsg] = useState("");
  const [form, setForm] = useState({
    code: "",
    name: "",
    description: "",
    base_premium: 0,
  });
  const [attachIds, setAttachIds] = useState<string[]>([]);
  const [schemaDraft, setSchemaDraft] = useState<RiskField[]>([]);
  const [uwJson, setUwJson] = useState('{"decline":[],"refer":[]}');
  const [rates, setRates] = useState<RateVersion[]>([]);
  const [rateForm, setRateForm] = useState({
    version_code: "v2",
    amount: 0,
    effective_from: new Date().toISOString().slice(0, 10),
    effective_to: "",
  });

  const selected = useMemo(() => plans.find((p) => p.id === selectedId) || null, [plans, selectedId]);
  const planPage = usePagination(plans);
  const ratePage = usePagination(rates);

  async function refresh() {
    const [p, r] = await Promise.all([
      api.get("/products/plans", { params: { product_code: line } }),
      api.get("/products/riders", { params: { product_code: line } }),
    ]);
    setPlans(p.data);
    setLineRiders(r.data);
    if (p.data[0] && !p.data.find((x: Plan) => x.id === selectedId)) {
      setSelectedId(p.data[0].id);
    }
  }

  useEffect(() => {
    refresh().catch(console.error);
  }, [line]);

  useEffect(() => {
    if (!selected) return;
    setAttachIds(selected.riders.map((r) => r.id));
    setSchemaDraft(selected.risk_schema?.length ? [...selected.risk_schema] : []);
    setUwJson(JSON.stringify(selected.uw_rules || { decline: [], refer: [] }, null, 2));
    setRateForm((f) => ({ ...f, amount: selected.base_premium }));
    api
      .get(`/products/plans/${selected.id}/rates`)
      .then((res) => setRates(res.data))
      .catch(console.error);
  }, [selected]);

  async function createPlan(e: FormEvent) {
    e.preventDefault();
    await api.post("/products/plans", {
      product_code: line,
      code: form.code,
      name: form.name,
      description: form.description || null,
      base_premium: Number(form.base_premium),
    });
    setForm({ code: "", name: "", description: "", base_premium: 0 });
    setMsg("Plan created (DRAFT)");
    await refresh();
  }

  async function saveAttach() {
    if (!selected) return;
    await api.put(`/products/plans/${selected.id}/riders`, { rider_ids: attachIds });
    setMsg("Attached riders updated");
    await refresh();
  }

  async function saveSchema() {
    if (!selected) return;
    await api.patch(`/products/plans/${selected.id}`, { risk_schema: schemaDraft });
    setMsg("Risk schema saved");
    await refresh();
  }

  async function saveUw() {
    if (!selected) return;
    try {
      const parsed = JSON.parse(uwJson);
      await api.patch(`/products/plans/${selected.id}`, { uw_rules: parsed });
      setMsg("UW rules saved");
      await refresh();
    } catch {
      setMsg("UW rules JSON is invalid");
    }
  }

  async function addRate(e: FormEvent) {
    e.preventDefault();
    if (!selected) return;
    await api.post(`/products/plans/${selected.id}/rates`, {
      version_code: rateForm.version_code,
      amount: Number(rateForm.amount),
      effective_from: rateForm.effective_from,
      effective_to: rateForm.effective_to || null,
    });
    setMsg("Rate version created (DRAFT)");
    const res = await api.get(`/products/plans/${selected.id}/rates`);
    setRates(res.data);
  }

  async function publishRate(rateId: string) {
    if (!selected) return;
    await api.post(`/products/plans/${selected.id}/rates/${rateId}/publish`);
    setMsg("Rate version published");
    await refresh();
    const res = await api.get(`/products/plans/${selected.id}/rates`);
    setRates(res.data);
  }

  async function publish(id: string) {
    await api.post(`/products/plans/${id}/publish`);
    setMsg("Plan published");
    await refresh();
  }

  async function unpublish(id: string) {
    await api.post(`/products/plans/${id}/unpublish`);
    setMsg("Plan unpublished");
    await refresh();
  }

  function toggleRider(id: string) {
    setAttachIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  function updateField(idx: number, patch: Partial<RiskField>) {
    setSchemaDraft((prev) => prev.map((f, i) => (i === idx ? { ...f, ...patch } : f)));
  }

  function addField() {
    setSchemaDraft((prev) => [
      ...prev,
      { key: `field_${prev.length + 1}`, label: "New field", type: "number", required: true, default: 0 },
    ]);
  }

  function removeField(idx: number) {
    setSchemaDraft((prev) => prev.filter((_, i) => i !== idx));
  }

  return (
    <div className="stack">
      <div className="hero">
        <h1>Basic plans</h1>
        <p>Configure plans, risk fields, UW thresholds, and effective-dated rates.</p>
      </div>
      {msg && <div className="muted">{msg}</div>}
      <div className="row">
        {LINES.map((l) => (
          <button
            key={l}
            type="button"
            className={`btn ${line === l ? "" : "ghost"}`}
            onClick={() => setParams({ line: l })}
          >
            {l}
          </button>
        ))}
      </div>
      <div className="grid-2">
        <div className="panel">
          <h3>{line} plans</h3>
          <table>
            <thead>
              <tr>
                <th>Code</th>
                <th>Name</th>
                <th>Base</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {planPage.pageItems.map((p) => (
                <tr key={p.id} className={p.id === selectedId ? "row-selected" : undefined}>
                  <td>
                    <button type="button" className="linkish" onClick={() => setSelectedId(p.id)}>
                      {p.code}
                    </button>
                  </td>
                  <td>{p.name}</td>
                  <td>${p.base_premium.toFixed(2)}</td>
                  <td>
                    <span className={`badge ${p.status !== "PUBLISHED" ? "warn" : ""}`}>{p.status}</span>
                  </td>
                  <td className="row">
                    {p.status === "PUBLISHED" ? (
                      <button className="btn ghost" type="button" onClick={() => unpublish(p.id)}>
                        Unpublish
                      </button>
                    ) : (
                      <button className="btn" type="button" onClick={() => publish(p.id)}>
                        Publish
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pagination
            page={planPage.page}
            totalPages={planPage.totalPages}
            total={planPage.total}
            pageSize={planPage.pageSize}
            onPageChange={planPage.setPage}
            onPageSizeChange={planPage.setPageSize}
          />
        </div>
        <form className="panel stack" onSubmit={createPlan}>
          <h3>New {line} plan</h3>
          <label>
            Code
            <input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} required />
          </label>
          <label>
            Name
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </label>
          <label>
            Description
            <textarea
              rows={2}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </label>
          <label>
            Base premium
            <input
              type="number"
              min={0}
              step={1}
              value={form.base_premium}
              onChange={(e) => setForm({ ...form, base_premium: Number(e.target.value) })}
              required
            />
          </label>
          <button className="btn" type="submit">
            Create draft plan
          </button>
        </form>
      </div>

      {selected && (
        <>
          <div className="panel stack">
            <h3>Risk field schema · {selected.code}</h3>
            <p className="muted" style={{ margin: 0 }}>
              Defines the New Business quote form for this plan.
            </p>
            {schemaDraft.map((field, idx) => (
              <div className="grid-2" key={idx}>
                <label>
                  Key
                  <input value={field.key} onChange={(e) => updateField(idx, { key: e.target.value })} />
                </label>
                <label>
                  Label
                  <input value={field.label} onChange={(e) => updateField(idx, { label: e.target.value })} />
                </label>
                <label>
                  Type
                  <select value={field.type} onChange={(e) => updateField(idx, { type: e.target.value })}>
                    {FIELD_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Default
                  <input
                    value={String(field.default ?? "")}
                    onChange={(e) => {
                      const raw = e.target.value;
                      const val =
                        field.type === "number"
                          ? Number(raw)
                          : field.type === "boolean"
                            ? raw === "true" || raw === "1"
                            : raw;
                      updateField(idx, { default: val });
                    }}
                  />
                </label>
                <div className="row">
                  <button className="btn danger" type="button" onClick={() => removeField(idx)}>
                    Remove
                  </button>
                </div>
              </div>
            ))}
            <div className="row">
              <button className="btn ghost" type="button" onClick={addField}>
                Add field
              </button>
              <button className="btn" type="button" onClick={saveSchema}>
                Save risk schema
              </button>
            </div>
          </div>

          <div className="panel stack">
            <h3>UW rules · {selected.code}</h3>
            <p className="muted" style={{ margin: 0 }}>
              JSON rule sets evaluated by underwriting (decline first, then refer). Use field names from the
              risk schema plus annual_premium.
            </p>
            <textarea rows={12} value={uwJson} onChange={(e) => setUwJson(e.target.value)} />
            <button className="btn" type="button" onClick={saveUw}>
              Save UW rules
            </button>
          </div>

          <div className="panel stack">
            <h3>Rate versions · {selected.code}</h3>
            <table>
              <thead>
                <tr>
                  <th>Version</th>
                  <th>Amount</th>
                  <th>From</th>
                  <th>To</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {ratePage.pageItems.map((r) => (
                  <tr key={r.id}>
                    <td>{r.version_code}</td>
                    <td>${r.amount.toFixed(2)}</td>
                    <td>{r.effective_from}</td>
                    <td>{r.effective_to || "—"}</td>
                    <td>
                      <span className={`badge ${r.status !== "PUBLISHED" ? "warn" : ""}`}>{r.status}</span>
                    </td>
                    <td>
                      {r.status !== "PUBLISHED" && (
                        <button className="btn" type="button" onClick={() => publishRate(r.id)}>
                          Publish
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pagination
              page={ratePage.page}
              totalPages={ratePage.totalPages}
              total={ratePage.total}
              pageSize={ratePage.pageSize}
              onPageChange={ratePage.setPage}
              onPageSizeChange={ratePage.setPageSize}
            />
            <form className="stack" onSubmit={addRate}>
              <div className="grid-2">
                <label>
                  Version code
                  <input
                    value={rateForm.version_code}
                    onChange={(e) => setRateForm({ ...rateForm, version_code: e.target.value })}
                    required
                  />
                </label>
                <label>
                  Amount
                  <input
                    type="number"
                    min={0}
                    value={rateForm.amount}
                    onChange={(e) => setRateForm({ ...rateForm, amount: Number(e.target.value) })}
                    required
                  />
                </label>
                <label>
                  Effective from
                  <input
                    type="date"
                    value={rateForm.effective_from}
                    onChange={(e) => setRateForm({ ...rateForm, effective_from: e.target.value })}
                    required
                  />
                </label>
                <label>
                  Effective to (optional)
                  <input
                    type="date"
                    value={rateForm.effective_to}
                    onChange={(e) => setRateForm({ ...rateForm, effective_to: e.target.value })}
                  />
                </label>
              </div>
              <button className="btn" type="submit">
                Add draft rate version
              </button>
            </form>
          </div>

          <div className="panel stack">
            <h3>
              Attach riders · {selected.code}
            </h3>
            {lineRiders.length === 0 && <div className="muted">No riders on this line yet.</div>}
            {lineRiders.map((r) => (
              <label key={r.id} className="checkbox-row">
                <input
                  type="checkbox"
                  checked={attachIds.includes(r.id)}
                  onChange={() => toggleRider(r.id)}
                />
                {r.code} — {r.name} (${r.premium.toFixed(2)}) · {r.status}
              </label>
            ))}
            <button className="btn" type="button" onClick={saveAttach}>
              Save rider attachments
            </button>
          </div>
        </>
      )}
    </div>
  );
}
