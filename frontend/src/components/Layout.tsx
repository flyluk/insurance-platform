import { Link, NavLink, Outlet } from "react-router-dom";
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
  const { user, logout } = useAuth();
  const role = user?.role || "";

  return (
    <div className="shell">
      <header className="topbar">
        <Link to="/" className="brand">
          Meridian
        </Link>
        <nav className="nav">
          {links
            .filter((l) => l.roles.includes(role) || role === "admin")
            .map((l) => (
              <NavLink key={l.to} to={l.to} className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
                {l.label}
              </NavLink>
            ))}
        </nav>
        <div className="userbox">
          <span>
            {user?.full_name} · {user?.role}
          </span>
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
