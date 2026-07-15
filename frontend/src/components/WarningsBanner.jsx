import { useState } from "react";

const VISIBLE_LIMIT = 5;

export default function WarningsBanner({ warnings }) {
  const [expanded, setExpanded] = useState(false);

  if (!warnings || warnings.length === 0) return null;

  const hasMore = warnings.length > VISIBLE_LIMIT;
  const visible = expanded ? warnings : warnings.slice(0, VISIBLE_LIMIT);
  const hiddenCount = warnings.length - VISIBLE_LIMIT;

  return (
    <div className="bg-loss-soft border border-loss/30 rounded-md px-4 py-3">
      <div className="text-xs font-medium text-loss mb-1">
        {warnings.length} warning{warnings.length > 1 ? "s" : ""} during this backtest
      </div>
      <ul className="text-xs text-text-secondary space-y-0.5 list-disc list-inside">
        {visible.map((w, i) => (
          <li key={i}>{w}</li>
        ))}
        {hasMore && !expanded && (
          <li className="list-none -ml-0">
            <button
              type="button"
              onClick={() => setExpanded(true)}
              className="text-loss hover:underline cursor-pointer"
            >
              … and {hiddenCount} more — click to show all
            </button>
          </li>
        )}
        {hasMore && expanded && (
          <li className="list-none -ml-0">
            <button
              type="button"
              onClick={() => setExpanded(false)}
              className="text-text-faint hover:underline cursor-pointer"
            >
              Show less
            </button>
          </li>
        )}
      </ul>
    </div>
  );
}
