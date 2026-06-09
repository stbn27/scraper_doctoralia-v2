import React from 'react';

/**
 * Button — Componente de botón reutilizable con variantes.
 * @param {{ variant?: 'primary'|'ghost'|'outline'|'danger', loading?: boolean, icon?: React.ReactNode, fullWidth?: boolean, children: React.ReactNode, className?: string, disabled?: boolean }} props
 * @example
 * <Button variant="primary" icon={<RiSearchLine />} onClick={handleSearch}>
 *   Buscar
 * </Button>
 */
export function Button({
  variant = 'primary',
  loading = false,
  icon = null,
  fullWidth = false,
  children,
  className = '',
  disabled = false,
  ...rest
}) {
  const baseStyles = 'inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-medium text-sm transition-all duration-200 press-effect focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-royalBlue-400 focus-visible:ring-offset-2 focus-visible:ring-offset-transparent disabled:opacity-50 disabled:cursor-not-allowed';

  const variants = {
    primary: 'bg-royalBlue-600 hover:bg-royalBlue-700 text-white shadow-lg shadow-royalBlue-600/25',
    ghost: 'bg-transparent hover:bg-royalBlue-400/20 dark:hover:bg-white/10 text-royalBlue-800 dark:text-royalBlue-300',
    outline: 'bg-transparent border border-royalBlue-400/50 hover:bg-royalBlue-600/20 text-royalBlue-300',
    danger: 'bg-red-600 hover:bg-red-700 text-white shadow-lg shadow-red-600/25',
  };

  return (
    <button
      className={`${baseStyles} ${variants[variant] || variants.primary} ${fullWidth ? 'w-full' : ''} ${className}`}
      disabled={disabled || loading}
      {...rest}
    >
      {loading ? (
        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      ) : icon ? (
        <span className="text-lg">{icon}</span>
      ) : null}
      {children}
    </button>
  );
}
