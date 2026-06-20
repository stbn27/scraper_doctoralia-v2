import React from "react";

/**
 * Checkbox — Componente de checkbox premium personalizado.
 * @param {{ label?: string, checked: boolean, onChange: Function, disabled?: boolean, id: string, className?: string }} props
 * @example
 * <Checkbox id="scrape-only" label="Solo hacer Scraping" checked={scrapeOnly} onChange={setScrapeOnly} />
 */
export function Checkbox({
  label,
  checked,
  onChange,
  disabled = false,
  id,
  className = "",
  ...rest
}) {
  return (
    <label
      htmlFor={id}
      className={`flex items-center gap-3 cursor-pointer select-none group text-sm ${
        disabled ? "opacity-50 cursor-not-allowed" : ""
      } ${className}`}
    >
      <div className="relative flex items-center justify-center">
        <input
          type="checkbox"
          id={id}
          checked={checked}
          onChange={(e) => !disabled && onChange(e.target.checked)}
          disabled={disabled}
          className="sr-only"
          {...rest}
        />
        <div
          className={`w-5 h-5 flex items-center justify-center border transition-all duration-300 ${
            checked
              ? "bg-royalBlue-500 border-royalBlue-400 rounded-full shadow-lg shadow-royalBlue-500/25"
              : "bg-white/5 border-white/10 rounded-lg group-hover:border-white/20"
          }`}
        >
          <svg
            className={`w-3 h-3 text-white transition-all duration-300 transform ${
              checked ? "scale-100 opacity-100 rotate-0" : "scale-0 opacity-0 -rotate-45"
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="3.5"
              d="M5 13l4 4L19 7"
            />
          </svg>
        </div>
      </div>
      {label && (
        <span className="text-slate-300 group-hover:text-white transition-colors duration-200">
          {label}
        </span>
      )}
    </label>
  );
}
