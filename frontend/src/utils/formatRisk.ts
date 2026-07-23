/** Format risk attribute values for staff detail panels (no [object Object]). */

function isIdKey(key: string): boolean {
  const k = key.toLowerCase();
  return k === "id" || k.endsWith("_id") || k.endsWith("_ids") || k.endsWith(" id") || k.endsWith(" ids");
}

export function formatRiskValue(value: unknown): string {
  if (value == null || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number" || typeof value === "bigint") return String(value);
  if (typeof value === "string") return value;
  if (Array.isArray(value)) {
    if (!value.length) return "—";
    return value.map((item) => formatRiskValue(item)).join(", ");
  }
  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>).filter(([k]) => !isIdKey(k));
    if (!entries.length) return "—";
    return entries
      .map(([k, v]) => `${k.replace(/_/g, " ")}: ${formatRiskValue(v)}`)
      .join(" · ");
  }
  return String(value);
}

export function flattenRiskEntries(
  attrs: Record<string, unknown>,
  prefix = "",
): { key: string; label: string; value: string }[] {
  const rows: { key: string; label: string; value: string }[] = [];
  for (const [key, value] of Object.entries(attrs)) {
    // Prefer human-readable codes; skip raw UUID / id fields
    if (isIdKey(key)) continue;
    const label = prefix ? `${prefix} / ${key.replace(/_/g, " ")}` : key.replace(/_/g, " ");
    const path = prefix ? `${prefix}.${key}` : key;
    if (value && typeof value === "object" && !Array.isArray(value)) {
      rows.push(...flattenRiskEntries(value as Record<string, unknown>, label));
    } else {
      rows.push({ key: path, label, value: formatRiskValue(value) });
    }
  }
  return rows;
}
