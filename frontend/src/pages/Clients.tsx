import { FormEvent, useEffect, useRef, useState } from "react";
import api from "../api/client";
import Pagination, { usePagination } from "../components/Pagination";

type Party = {
  id: string;
  full_name: string;
  email: string;
  phone?: string | null;
  date_of_birth?: string | null;
  address?: string | null;
  id_number?: string | null;
  gender?: string | null;
  created_at?: string;
};

type EditForm = {
  full_name: string;
  email: string;
  phone: string;
  date_of_birth: string;
  address: string;
  id_number: string;
  gender: string;
};

function emptyForm(): EditForm {
  return {
    full_name: "",
    email: "",
    phone: "",
    date_of_birth: "",
    address: "",
    id_number: "",
    gender: "",
  };
}

function formFromParty(p: Party): EditForm {
  return {
    full_name: p.full_name || "",
    email: p.email || "",
    phone: p.phone || "",
    date_of_birth: p.date_of_birth || "",
    address: p.address || "",
    id_number: p.id_number || "",
    gender: p.gender || "",
  };
}

export default function Clients() {
  const [clients, setClients] = useState<Party[]>([]);
  const [name, setName] = useState("");
  const [searched, setSearched] = useState(false);
  const [searchBusy, setSearchBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [editing, setEditing] = useState<Party | null>(null);
  const [form, setForm] = useState<EditForm>(emptyForm());
  const [saveBusy, setSaveBusy] = useState(false);
  const [formError, setFormError] = useState("");
  const selectionRequest = useRef(0);

  async function loadAll() {
    const { data } = await api.get("/nb/parties");
    setClients(Array.isArray(data) ? data : []);
    setSearched(false);
  }

  useEffect(() => {
    loadAll().catch(console.error);
  }, []);

  useEffect(() => {
    if (!editing) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") closeModal();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [editing]);

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
      setClients(hits);
      setSearched(true);
      setMsg(
        hits.length
          ? `Found ${hits.length} client${hits.length === 1 ? "" : "s"}`
          : "No matching clients",
      );
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err instanceof Error ? err.message : "Search failed");
      setMsg(String(detail));
    } finally {
      setSearchBusy(false);
    }
  }

  async function clearSearch() {
    setName("");
    setMsg("");
    await loadAll();
  }

  function openEdit(p: Party) {
    const request = ++selectionRequest.current;
    setEditing(p);
    setForm(formFromParty(p));
    setFormError("");
    api
      .get(`/nb/parties/${p.id}`)
      .then(({ data }) => {
        if (request !== selectionRequest.current) return;
        setEditing(data);
        setForm(formFromParty(data));
      })
      .catch(console.error);
  }

  function closeModal() {
    selectionRequest.current += 1;
    setEditing(null);
    setForm(emptyForm());
    setFormError("");
  }

  function setField<K extends keyof EditForm>(key: K, value: EditForm[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function saveClient(e: FormEvent) {
    e.preventDefault();
    if (!editing) return;
    const missing = (
      [
        ["full_name", "full name"],
        ["email", "email"],
        ["date_of_birth", "date of birth"],
        ["address", "address"],
        ["id_number", "ID number"],
        ["gender", "gender"],
        ["phone", "contact number"],
      ] as const
    ).filter(([key]) => !form[key].trim());
    if (missing.length) {
      setFormError(`Required: ${missing.map(([, label]) => label).join(", ")}`);
      return;
    }
    setSaveBusy(true);
    setFormError("");
    try {
      const { data } = await api.put(`/nb/parties/${editing.id}`, {
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        phone: form.phone.trim(),
        date_of_birth: form.date_of_birth.trim(),
        address: form.address.trim(),
        id_number: form.id_number.trim(),
        gender: form.gender.trim(),
      });
      setClients((prev) =>
        prev
          .map((c) => (c.id === data.id ? data : c))
          .sort((a, b) => a.full_name.localeCompare(b.full_name)),
      );
      setMsg(`Updated ${data.full_name}`);
      closeModal();
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err instanceof Error ? err.message : "Save failed");
      setFormError(String(detail));
    } finally {
      setSaveBusy(false);
    }
  }

  const page = usePagination(clients);

  return (
    <div className="stack">
      <div className="hero">
        <h1>Clients</h1>
        <p>Search and update client contact details used across quotes, policies, and claims.</p>
      </div>
      {msg && <div className="muted">{msg}</div>}

      <form className="panel stack" onSubmit={searchClients}>
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
            }}
            required
          />
        </label>
        <div className="row">
          <button className="btn" type="submit" disabled={searchBusy}>
            {searchBusy ? "Searching…" : "Search clients"}
          </button>
          {searched && (
            <button className="btn ghost" type="button" onClick={() => clearSearch().catch(console.error)}>
              Show all clients
            </button>
          )}
        </div>
      </form>

      <div className="panel stack">
        <h3 style={{ margin: 0 }}>
          {searched ? `Matches (${clients.length})` : `All clients (${clients.length})`}
        </h3>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Phone</th>
              <th>DOB</th>
              <th>ID number</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {page.pageItems.map((c) => (
              <tr key={c.id}>
                <td>
                  <button type="button" className="linkish" onClick={() => openEdit(c)}>
                    {c.full_name}
                  </button>
                </td>
                <td>{c.email || "—"}</td>
                <td>{c.phone || "—"}</td>
                <td>{c.date_of_birth || "—"}</td>
                <td>{c.id_number || "—"}</td>
                <td>
                  <button className="btn ghost" type="button" onClick={() => openEdit(c)}>
                    Edit
                  </button>
                </td>
              </tr>
            ))}
            {!clients.length && (
              <tr>
                <td colSpan={6} className="muted">
                  {searched ? "No matching clients." : "No clients yet."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
        <Pagination
          page={page.page}
          totalPages={page.totalPages}
          total={page.total}
          pageSize={page.pageSize}
          onPageChange={page.setPage}
          onPageSizeChange={page.setPageSize}
        />
      </div>

      {editing && (
        <div className="modal-backdrop" onClick={closeModal} role="presentation">
          <div
            className="modal-panel stack"
            role="dialog"
            aria-modal="true"
            aria-labelledby="client-edit-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="row" style={{ justifyContent: "space-between" }}>
              <h3 id="client-edit-title" style={{ margin: 0 }}>
                Edit client
              </h3>
              <button className="btn ghost" type="button" onClick={closeModal}>
                Close
              </button>
            </div>
            {formError && <div className="muted">{formError}</div>}
            <form className="stack" onSubmit={(e) => saveClient(e).catch(console.error)}>
              <label>
                Full name
                <input
                  value={form.full_name}
                  onChange={(e) => setField("full_name", e.target.value)}
                  required
                />
              </label>
              <label>
                Email
                <input
                  value={form.email}
                  onChange={(e) => setField("email", e.target.value)}
                  type="email"
                  required
                />
              </label>
              <label>
                Date of birth
                <input
                  value={form.date_of_birth}
                  onChange={(e) => setField("date_of_birth", e.target.value)}
                  type="date"
                  required
                />
              </label>
              <label>
                Address
                <textarea
                  value={form.address}
                  onChange={(e) => setField("address", e.target.value)}
                  rows={2}
                  required
                />
              </label>
              <label>
                ID number
                <input
                  value={form.id_number}
                  onChange={(e) => setField("id_number", e.target.value)}
                  required
                />
              </label>
              <label>
                Gender
                <select
                  value={form.gender}
                  onChange={(e) => setField("gender", e.target.value)}
                  required
                >
                  <option value="">Select…</option>
                  <option value="female">Female</option>
                  <option value="male">Male</option>
                  <option value="unspecified">Unspecified</option>
                </select>
              </label>
              <label>
                Contact number
                <input
                  value={form.phone}
                  onChange={(e) => setField("phone", e.target.value)}
                  type="tel"
                  required
                />
              </label>
              <div className="row">
                <button className="btn" type="submit" disabled={saveBusy}>
                  {saveBusy ? "Saving…" : "Save changes"}
                </button>
                <button className="btn ghost" type="button" onClick={closeModal}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
