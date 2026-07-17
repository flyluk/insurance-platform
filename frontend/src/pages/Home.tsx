import { Link } from "react-router-dom";
import { useAuth } from "../components/AuthContext";

export default function Home() {
  const { user } = useAuth();
  return (
    <section className="hero">
      <h1>Meridian Insurance</h1>
      <p>
        Welcome, {user?.full_name}. Work quotes, underwriting decisions, policies, claims, and ledger
        entries across AUTO, HOME, and LIFE.
      </p>
      <div className="row">
        <Link className="btn" to="/quotes">
          New Business
        </Link>
        <Link className="btn ghost" to="/policies">
          Policies
        </Link>
        <Link className="btn ghost" to="/claims">
          Claims
        </Link>
      </div>
    </section>
  );
}
