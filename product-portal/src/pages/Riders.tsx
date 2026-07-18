import { FormEvent, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import api from "../api/client";

type Rider = {
  id: string;
  product_code: string;
  code: string;
  name: string;
  description: string | null;
  premium: number;
  status: string;
};

const LINES = ["AUTO", "HOME", "LIFE"];

export default function Riders() {
  const [params, setParams] = useSearchParams();
  const line = (params.get("line") || "AUTO").toUpperCase();
  const [riders, setRiders] = useState<Rider[]>([]);
  const [msg, setMsg] = useState("");
  const [form, setForm] = useState({
    code: "",
    name: "",
    description: "",
    premium: 0,
  });

  async function refresh() {
    const { data } = await api.get("/products/riders", { params: { product_code: line } });
    setRiders(data);
  }

  useEffect(() => {
    refresh().catch(console.error);
  }, [line]);

  async function createRider(e: FormEvent) {
    e.preventDefault();
    await api.post("/products/riders", {
      product_code: line,
      code: form.code,
      name: form.name,
      description: form.description || null,
      premium: Number(form.premium),
    });
    setForm({ code: "", name: "", description: "", premium: 0 });
    setMsg("Rider created (DRAFT)");
    await refresh();
  }

  async function publish(id: string) {
    await api.post(`/products/riders/${id}/publish`);
    setMsg("Rider published");
    await refresh();
  }

  async function unpublish(id: string) {
    await api.post(`/products/riders/${id}/unpublish`);
    setMsg("Rider unpublished");
    await refresh();
  }

  return (
    <div className="stack">
      <div className="hero">
        <h1>Riders</h1>
        <p>Optional add-ons attached to basic plans on the same line.</p>
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
          <h3>{line} riders</h3>
          <table>
            <thead>
              <tr>
                <th>Code</th>
                <th>Name</th>
                <th>Premium</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {riders.map((r) => (
                <tr key={r.id}>
                  <td>{r.code}</td>
                  <td>{r.name}</td>
                  <td>${r.premium.toFixed(2)}</td>
                  <td>
                    <span className={`badge ${r.status !== "PUBLISHED" ? "warn" : ""}`}>{r.status}</span>
                  </td>
                  <td>
                    {r.status === "PUBLISHED" ? (
                      <button className="btn ghost" type="button" onClick={() => unpublish(r.id)}>
                        Unpublish
                      </button>
                    ) : (
                      <button className="btn" type="button" onClick={() => publish(r.id)}>
                        Publish
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <form className="panel stack" onSubmit={createRider}>
          <h3>New {line} rider</h3>
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
            Premium
            <input
              type="number"
              min={0}
              step={1}
              value={form.premium}
              onChange={(e) => setForm({ ...form, premium: Number(e.target.value) })}
              required
            />
          </label>
          <button className="btn" type="submit">
            Create draft rider
          </button>
        </form>
      </div>
    </div>
  );
}
