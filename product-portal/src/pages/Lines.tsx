import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/client";

type LineSummary = {
  product_code: string;
  plan_count: number;
  rider_count: number;
  published_plans: number;
};

export default function Lines() {
  const [lines, setLines] = useState<LineSummary[]>([]);

  useEffect(() => {
    api.get("/products/lines").then((r) => setLines(r.data)).catch(console.error);
  }, []);

  return (
    <div className="stack">
      <div className="hero">
        <h1>Product lines</h1>
        <p>Each line has basic plans and optional riders. Publish plans before agents can quote them.</p>
      </div>
      <div className="grid-3">
        {lines.map((line) => (
          <div className="panel stack" key={line.product_code}>
            <h3 style={{ margin: 0 }}>{line.product_code}</h3>
            <div className="muted">
              {line.plan_count} plans · {line.published_plans} published · {line.rider_count} riders
            </div>
            <div className="row">
              <Link className="btn ghost" to={`/plans?line=${line.product_code}`}>
                Plans
              </Link>
              <Link className="btn ghost" to={`/riders?line=${line.product_code}`}>
                Riders
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
