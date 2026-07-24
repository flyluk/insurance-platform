import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "./AuthContext";

const links = [
  { to: "/", label: "Home", roles: ["agent", "underwriter", "claims", "finance", "product", "admin", "policyholder"] },
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
  const location = useLocation();
  const role = user?.role || "";
  const [menuOpen, setMenuOpen] = useState(false);
  const visibleLinks = links.filter((l) => l.roles.includes(role));

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!menuOpen) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setMenuOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menuOpen]);

  return (
    <div className={`shell${menuOpen ? " menu-open" : ""}`}>
      <header className="topbar">
        <button
          type="button"
          className="hamburger"
          aria-label={menuOpen ? "Close menu" : "Open menu"}
          aria-expanded={menuOpen}
          aria-controls="app-side-menu"
          onClick={() => setMenuOpen((open) => !open)}
        >
          <span />
          <span />
          <span />
        </button>
        <Link to="/" className="brand">
          Meridian
        </Link>
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

      {menuOpen && (
        <button
          type="button"
          className="side-menu-backdrop"
          aria-label="Close menu"
          onClick={() => setMenuOpen(false)}
        />
      )}

      <aside id="app-side-menu" className="side-menu" aria-hidden={!menuOpen}>
        <div className="side-menu-header">
          <strong>Menu</strong>
          <button type="button" className="btn ghost" onClick={() => setMenuOpen(false)}>
            Close
          </button>
        </div>
        <nav className="side-nav">
          {visibleLinks.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.to === "/"}
              className={({ isActive }) => (isActive ? "side-nav-link active" : "side-nav-link")}
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
