import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "./AuthContext";

const links = [
  { to: "/clients", label: "Clients", roles: ["agent", "claims", "admin"] },
  { to: "/quotes", label: "New Business", roles: ["agent", "admin"] },
  { to: "/underwriting", label: "Underwriting", roles: ["underwriter", "admin"] },
  { to: "/policies", label: "Policies", roles: ["agent", "admin", "underwriter"] },
  { to: "/claims", label: "Claims", roles: ["claims", "admin"] },
  { to: "/finance", label: "Finance", roles: ["finance", "admin"] },
  { to: "/users", label: "Users", roles: ["admin"] },
];

export default function Layout() {
  const { user, logout, impersonating, returnToAdmin } = useAuth();
  const navigate = useNavigate();
  const role = user?.role || "";

  return (
    <div className="shell">
      <header className="topbar">
        <Link to="/" className="brand">
          Meridian
        </Link>
        <nav className="nav">
          {links
            .filter((l) => l.roles.includes(role))
            .map((l) => (
              <NavLink key={l.to} to={l.to} className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
                {l.label}
              </NavLink>
            ))}
        </nav>
        <div className="userbox">
          <span>
            {user?.full_name} · {user?.role}
            {impersonating ? " · impersonating" : ""}
          </span>
          {impersonating && (
            <button
              type="button"
              className="btn"
              onClick={() => {
                if (returnToAdmin()) navigate("/users");
              }}
            >
              Back to admin
            </button>
          )}
          <button type="button" className="btn ghost" onClick={logout}>
            Sign out
          </button>
        </div>
      </header>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
