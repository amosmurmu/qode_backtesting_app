export function formatINR(value) {
  if (value == null) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatPct(value, { showSign = false } = {}) {
  if (value == null) return "—";
  const sign = showSign && value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

export function formatNumber(value, decimals = 2) {
  if (value == null) return "—";
  return value.toFixed(decimals);
}

export function formatDate(dateStr) {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

/** Tailwind text color class for a +/- numeric value. */
export function signColor(value) {
  if (value == null) return "text-text-secondary";
  if (value > 0) return "text-gain";
  if (value < 0) return "text-loss";
  return "text-text-secondary";
}
