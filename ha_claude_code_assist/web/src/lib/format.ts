/** Date and time, in the browser's language: "22 Nov 2026, 10:15". */
export function formatDateTime(iso: string | null | undefined): string {
  return iso ? new Date(iso).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }) : "–";
}

/** Time only: "10:15". */
export function formatClock(iso: string | null | undefined): string {
  return iso ? new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "";
}

/** Date only: "22 Nov 2026". */
export function formatDate(iso: string | null | undefined): string {
  return iso ? new Date(iso).toLocaleDateString([], { dateStyle: "medium" }) : "–";
}

/** A duration in seconds with one decimal: "1.4 s". */
export function formatSeconds(milliseconds: number): string {
  return `${(milliseconds / 1000).toFixed(1)} s`;
}

/** "haiku" → "Haiku": a setting's value shown as a name. */
export function capitalize(text: string): string {
  return text ? text[0].toUpperCase() + text.slice(1) : text;
}

const COMPACT = new Intl.NumberFormat("en", { notation: "compact", maximumSignificantDigits: 3 });

/** A count in few characters: "950", "11.6K", "122K", "1.2M". */
export function formatCompact(value: number): string {
  return COMPACT.format(value);
}
