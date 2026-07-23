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

export function PartyCell({ party }: { party?: PartySummary | null }) {
  if (!party) return <span className="muted">—</span>;
  return (
    <div className="party-cell">
      <strong>{party.full_name || "—"}</strong>
      <div className="muted">DOB {party.date_of_birth || "—"}</div>
      <div className="muted">{party.address || "No address on file"}</div>
    </div>
  );
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

  return (
    <div className={`party-card${compact ? " compact" : ""}`}>
      <div className="party-role">{role}</div>
      <strong>{party.full_name || "—"}</strong>
      <div className="detail-grid" style={{ marginTop: "0.5rem" }}>
        <div className="detail-row">
          <span className="muted">Name</span>
          <strong>{party.full_name || "—"}</strong>
        </div>
        <div className="detail-row">
          <span className="muted">DOB</span>
          <strong>{party.date_of_birth || "—"}</strong>
        </div>
        <div className="detail-row">
          <span className="muted">Address</span>
          <strong>{party.address || "—"}</strong>
        </div>
        {!compact && party.email && (
          <div className="detail-row">
            <span className="muted">Email</span>
            <strong>{party.email}</strong>
          </div>
        )}
        {!compact && party.phone && (
          <div className="detail-row">
            <span className="muted">Phone</span>
            <strong>{party.phone}</strong>
          </div>
        )}
      </div>
    </div>
  );
}
