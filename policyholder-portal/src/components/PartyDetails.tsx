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

function Field({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="party-field">
      <span className="party-field-label">{label}</span>
      <span className="party-field-value">{value?.trim() ? value : "—"}</span>
    </div>
  );
}

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
      <div className="party-name">{party.full_name || "—"}</div>
      <div className="party-fields">
        <Field label="Name" value={party.full_name} />
        <Field label="DOB" value={party.date_of_birth} />
        <Field label="Address" value={party.address} />
        {!compact && <Field label="Email" value={party.email} />}
        {!compact && <Field label="Phone" value={party.phone} />}
        {!compact && <Field label="ID number" value={party.id_number} />}
      </div>
    </div>
  );
}
