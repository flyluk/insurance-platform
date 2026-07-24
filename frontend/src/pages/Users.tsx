import { FormEvent, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";
import { useAuth } from "../components/AuthContext";
import Pagination, { usePagination } from "../components/Pagination";

const ROLES = [
  "admin",
  "agent",
  "underwriter",
  "claims",
  "finance",
  "product",
  "policyholder",
] as const;

type UserRow = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  party_id?: string | null;
  is_active: boolean;
  created_at?: string;
};

type EditForm = {
  full_name: string;
  email: string;
  role: string;
  party_id: string;
  is_active: boolean;
  password: string;
};

function emptyForm(): EditForm {
  return {
    full_name: "",
    email: "",
    role: "agent",
    party_id: "",
    is_active: true,
    password: "",
  };
}

function formFromUser(u: UserRow): EditForm {
  return {
    full_name: u.full_name || "",
    email: u.email || "",
    role: u.role || "agent",
    party_id: u.party_id || "",
    is_active: u.is_active !== false,
    password: "",
  };
}

export default function Users() {
  const navigate = useNavigate();
  const { user: currentUser, adoptSession } = useAuth();
  const [users, setUsers] = useState<UserRow[]>([]);
  const [msg, setMsg] = useState("");
  const [editing, setEditing] = useState<UserRow | null>(null);
  const [form, setForm] = useState<EditForm>(emptyForm());
  const [saveBusy, setSaveBusy] = useState(false);
  const [loginBusyId, setLoginBusyId] = useState<string | null>(null);
  const [formError, setFormError] = useState("");
  const selectionRequest = useRef(0);

  async function refresh() {
    const { data } = await api.get("/users");
    setUsers(Array.isArray(data) ? data : []);
  }

  useEffect(() => {
    refresh().catch(console.error);
  }, []);

  useEffect(() => {
    if (!editing) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") closeModal();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [editing]);

  function openEdit(u: UserRow) {
    const request = ++selectionRequest.current;
    setEditing(u);
    setForm(formFromUser(u));
    setFormError("");
    api
      .get(`/users/${u.id}`)
      .then(({ data }) => {
        if (request !== selectionRequest.current) return;
        setEditing(data);
        setForm(formFromUser(data));
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

  async function loginAs(u: UserRow) {
    if (!u.is_active) {
      setMsg("Cannot login as an inactive user");
      return;
    }
    if (currentUser?.email === u.email) {
      setMsg(`Already signed in as ${u.full_name}`);
      return;
    }
    setLoginBusyId(u.id);
    setMsg("");
    try {
      const { data } = await api.post(`/users/${u.id}/login-as`);
      adoptSession(data, { keepAdminReturn: true });
      closeModal();
      navigate("/");
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err instanceof Error ? err.message : "Login as failed");
      setMsg(String(detail));
    } finally {
      setLoginBusyId(null);
    }
  }

  async function saveUser(e: FormEvent) {
    e.preventDefault();
    if (!editing) return;
    if (!form.full_name.trim() || !form.email.trim() || !form.role.trim()) {
      setFormError("Full name, email, and role are required");
      return;
    }
    setSaveBusy(true);
    setFormError("");
    try {
      const payload: Record<string, unknown> = {
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        role: form.role.trim(),
        party_id: form.party_id.trim() || null,
        is_active: form.is_active,
      };
      if (form.password.trim()) {
        payload.password = form.password.trim();
      }
      const { data } = await api.put(`/users/${editing.id}`, payload);
      setUsers((prev) =>
        prev
          .map((u) => (u.id === data.id ? data : u))
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

  const page = usePagination(users);

  return (
    <div className="stack">
      <div className="hero">
        <h1>Users</h1>
        <p>
          Manage accounts and login as admin, agent, underwriter, claims, finance, and other roles
          without their passwords.
        </p>
      </div>
      {msg && <div className="muted">{msg}</div>}

      <div className="panel stack">
        <h3 style={{ margin: 0 }}>All users ({users.length})</h3>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Active</th>
              <th>Party ID</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {page.pageItems.map((u) => (
              <tr key={u.id}>
                <td>
                  <button type="button" className="linkish" onClick={() => openEdit(u)}>
                    {u.full_name}
                  </button>
                </td>
                <td>{u.email}</td>
                <td>
                  <span className="badge">{u.role}</span>
                </td>
                <td>
                  <span className={`badge ${u.is_active ? "" : "bad"}`}>
                    {u.is_active ? "Yes" : "No"}
                  </span>
                </td>
                <td className="mono muted">{u.party_id || "—"}</td>
                <td className="row">
                  <button
                    className="btn"
                    type="button"
                    disabled={!u.is_active || loginBusyId === u.id}
                    onClick={() => loginAs(u).catch(console.error)}
                  >
                    {loginBusyId === u.id ? "Signing in…" : "Login as"}
                  </button>
                  <button className="btn ghost" type="button" onClick={() => openEdit(u)}>
                    Edit
                  </button>
                </td>
              </tr>
            ))}
            {!users.length && (
              <tr>
                <td colSpan={6} className="muted">
                  No users found.
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
            aria-labelledby="user-edit-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="row" style={{ justifyContent: "space-between" }}>
              <h3 id="user-edit-title" style={{ margin: 0 }}>
                Edit user
              </h3>
              <button className="btn ghost" type="button" onClick={closeModal}>
                Close
              </button>
            </div>
            {formError && <div className="muted">{formError}</div>}
            <form className="stack" onSubmit={(e) => saveUser(e).catch(console.error)}>
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
                Role
                <select
                  value={form.role}
                  onChange={(e) => setField("role", e.target.value)}
                  required
                >
                  {ROLES.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Party ID <span className="muted">(optional, for policyholder)</span>
                <input
                  value={form.party_id}
                  onChange={(e) => setField("party_id", e.target.value)}
                  placeholder="00000000-0000-4000-8000-…"
                />
              </label>
              <label className="row" style={{ alignItems: "center", gap: "0.5rem" }}>
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(e) => setField("is_active", e.target.checked)}
                />
                Active account
              </label>
              <label>
                New password <span className="muted">(leave blank to keep)</span>
                <input
                  value={form.password}
                  onChange={(e) => setField("password", e.target.value)}
                  type="password"
                  autoComplete="new-password"
                  minLength={6}
                />
              </label>
              <div className="row">
                <button className="btn" type="submit" disabled={saveBusy}>
                  {saveBusy ? "Saving…" : "Save changes"}
                </button>
                <button
                  className="btn"
                  type="button"
                  disabled={!editing.is_active || loginBusyId === editing.id}
                  onClick={() => loginAs(editing).catch(console.error)}
                >
                  {loginBusyId === editing.id ? "Signing in…" : `Login as ${editing.role}`}
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
