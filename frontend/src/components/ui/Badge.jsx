import React from 'react';

/**
 * Badge — Etiqueta de color adaptable a modo claro y oscuro.
 * @param {{ variant?: 'blue'|'emerald'|'amber'|'red'|'gray', children: React.ReactNode, className?: string }} props
 * @example
 * <Badge variant="blue">Cardiología</Badge>
 * <Badge variant="emerald">Confiable</Badge>
 */
export function Badge({ variant = 'blue', children, className = '' }) {
  const variants = {
    blue:    'bg-royalBlue-500/10 text-royalBlue-600 dark:text-royalBlue-300 border-royalBlue-500/25',
    emerald: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/25',
    amber:   'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/25',
    red:     'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/25',
    gray:    'bg-black/5 dark:bg-white/5 border-black/10 dark:border-white/10',
  };

  const base = variants[variant] || variants.blue;

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${base} ${className}`}
    >
      {children}
    </span>
  );
}
