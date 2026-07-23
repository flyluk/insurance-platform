import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "./AuthContext";

export default function Layout() {
  const { user, logout } = useAuth();
  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          Meridian<span>My Account</span>
        </div>
        <nav className="nav">
          <NavLink className={({ isActive }) => `nav-link${isActive ? " active" : ""}`} to="/" end>
            Home
          </NavLink>
          <NavLink className={({ isActive }) => `nav-link${isActive ? " active" : ""}`} to="/policies">
            Policies
          </NavLink>
          <NavLink className={({ isActive }) => `nav-link${isActive ? " active" : ""}`} to="/billing">
            Billing
          </NavLink>
          <NavLink className={({ isActive }) => `nav-link${isActive ? " active" : ""}`} to="/claims">
            Claims
          </NavLink>
        </nav>
        <div className="userbox">
          <span>
            {user?.full_name}
          </span>
          <button className="btn ghost" type="button" onClick={logout}>
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
