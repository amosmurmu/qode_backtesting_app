export function Card({ children, className = "" }) {
  return (
    <div className={`bg-surface border border-border rounded-lg ${className}`}>
      {children}
    </div>
  );
}

export function SectionLabel({ children }) {
  return (
    <h3 className="font-display text-sm font-semibold text-text-secondary uppercase tracking-wider mb-3">
      {children}
    </h3>
  );
}

export function PrimaryButton({ children, onClick, disabled, type = "button", className = "" }) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`bg-accent hover:bg-accent/90 disabled:bg-text-faint disabled:cursor-not-allowed
                  text-bg font-display font-semibold text-sm px-5 py-2.5 rounded-md
                  transition-colors duration-150 ${className}`}
    >
      {children}
    </button>
  );
}

export function SecondaryButton({ children, onClick, disabled, className = "" }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`bg-surface-raised hover:bg-border border border-border
                  text-text-primary font-medium text-sm px-4 py-2 rounded-md
                  transition-colors duration-150 disabled:opacity-40 disabled:cursor-not-allowed ${className}`}
    >
      {children}
    </button>
  );
}

export function IconButton({ children, onClick, title, className = "" }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      className={`text-text-secondary hover:text-loss transition-colors duration-150 ${className}`}
    >
      {children}
    </button>
  );
}
