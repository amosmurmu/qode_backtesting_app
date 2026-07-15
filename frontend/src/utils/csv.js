/**
 * Tiny CSV export helper - no library needed for this.
 * Triggers a browser download of the given rows as a .csv file.
 */
export function downloadCSV(filename, rows) {
  if (!rows || rows.length === 0) return;

  const headers = Object.keys(rows[0]);
  const escapeCell = (value) => {
    const str = String(value ?? "");
    if (str.includes(",") || str.includes('"') || str.includes("\n")) {
      return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
  };

  const lines = [
    headers.join(","),
    ...rows.map((row) => headers.map((h) => escapeCell(row[h])).join(",")),
  ];

  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/** Flattens rebalance logs (nested holdings) into one row per holding, for CSV export. */
export function flattenRebalanceLogs(rebalanceLogs) {
  const rows = [];
  for (const log of rebalanceLogs) {
    for (const holding of log.holdings) {
      rows.push({
        rebalance_date: log.rebalance_date,
        portfolio_value: log.portfolio_value,
        ticker: holding.ticker,
        name: holding.name,
        weight: holding.weight,
        shares: holding.shares,
        entry_price: holding.entry_price,
      });
    }
  }
  return rows;
}
