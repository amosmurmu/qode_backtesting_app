export const REBALANCE_OPTIONS = [
  { value: "monthly", label: "Monthly" },
  { value: "quarterly", label: "Quarterly" },
  { value: "yearly", label: "Yearly" },
];

export const WEIGHTING_OPTIONS = [
  { value: "equal", label: "Equal-weighted" },
  { value: "market_cap", label: "Market cap-weighted" },
  { value: "metric", label: "Metric-weighted" },
];

export const OPERATOR_OPTIONS = [
  { value: ">", label: "greater than" },
  { value: ">=", label: "≥" },
  { value: "<", label: "less than" },
  { value: "<=", label: "≤" },
  { value: "==", label: "equal to" },
];

export const DIRECTION_OPTIONS = [
  { value: "desc", label: "Descending (higher is better)" },
  { value: "asc", label: "Ascending (lower is better)" },
];

// Fallback list used if the /metrics/available API call hasn't resolved yet.
export const FALLBACK_METRICS = [
  { key: "market_cap_cr", label: "Market Cap (₹ Cr)" },
  { key: "pe_ratio", label: "PE Ratio" },
  { key: "pb_ratio", label: "PB Ratio" },
  { key: "roce_pct", label: "ROCE (%)" },
  { key: "roe_pct", label: "ROE (%)" },
  { key: "revenue_cr", label: "Revenue (₹ Cr)" },
  { key: "pat_cr", label: "PAT (₹ Cr)" },
  { key: "operating_margin_pct", label: "Operating Margin (%)" },
  { key: "total_debt_cr", label: "Total Debt (₹ Cr)" },
  { key: "debt_to_equity", label: "Debt to Equity" },
  { key: "operating_cash_flow_cr", label: "Operating Cash Flow (₹ Cr)" },
];
