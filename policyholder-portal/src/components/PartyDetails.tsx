export type PartySummary = {
  id: string;
  full_name?: string;
  email?: string;
  phone?: string | null;
  date_of_birth?: string | null;
  address?: string | null;
  id_number?: string | null;
  gender?: string | null;
};

type Props = {
  role: "Owner" | "Insured";
  party?: PartySummary | null;
  compact?: boolean;
};

export function partyLabel(party?: PartySummary | null, fallbackId?: string) {
  if (party?.full_name) return party.full_name;
  if (party?.email) return party.email;
  return party?.id || fallbackId || "—";
}

export default function PartyDetails({ role, party, compact = false }: Props) {
  if (!party) {
    return (
      <div className="party-card">
        <div className="party-role">{role}</div>
        <div className="muted">Not available</div>
      </div>
    );
  }

  if (compact) {
    return (
      <div className="party-card compact">
        <div className="party-role">{role}</div>
        <strong>{party.full_name || "—"}</strong>
        {party.email && <div className="muted">{party.email}</div>}
      </div>
    );
  }

  return (
    <div className="party-card">
      <div className="party-role">{role}</div>
      <strong>{party.full_name || "—"}</strong>
      <div className="detail-grid" style={{ marginTop: "0.5rem" }}>
        {party.email && (
          <div className="detail-row">
            <span className="muted">Email</span>
            <strong>{party.email}</strong>
          </div>
        )}
        {party.phone && (
          <div className="detail-row">
            <span className="muted">Phone</span>
            <strong>{party.phone}</strong>
          </div>
        )}
        {party.date_of_birth && (
          <div className="detail-row">
            <span className="muted">DOB</span>
            <strong>{party.date_of_birth}</strong>
          </div>
        )}
        {party.address && (
          <div className="detail-row">
            <span className="muted">Address</span>
            <strong>{party.address}</strong>
          </div>
        )}
        {party.id_number && (
          <div className="detail-row">
            <span className="muted">ID</span>
            <strong>{party.id_number}</strong>
          </div>
        )}
      </div>
    </div>
  );
}
