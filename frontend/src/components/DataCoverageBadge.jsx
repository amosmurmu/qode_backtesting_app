export default function DataCoverageBadge({ coverage }) {
  if (!coverage) {
    return <span className="text-xs text-text-faint">Checking data coverage…</span>;
  }
  if (!coverage.stocks) {
    return (
      <span className="text-xs text-loss">
        No data found — run the ingestion script first (see README).
      </span>
    );
  }
  const [start, end] = coverage.price_date_range || [];
  return (
    <span className="text-xs text-text-faint font-mono">
      {coverage.stocks} stocks · {coverage.price_rows.toLocaleString("en-IN")} price rows
      {start && end ? ` · ${start} → ${end}` : ""}
    </span>
  );
}
