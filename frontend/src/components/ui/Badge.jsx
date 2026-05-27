import React from 'react';

/**
 * Badge — Componente de etiqueta/badge con variantes de color.
 * @param {{ variant?: 'blue'|'emerald'|'amber'|'red', children: React.ReactNode, className?: string }} props
 * @example
 * <Badge variant="blue">Cardiología</Badge>
 * <Badge variant="emerald">Atiende niños</Badge>
 */
export function Badge({ variant = 'blue', children, className = '' }) {
  const variants = {
    blue: 'bg-royalBlue-800/60 text-royalBlue-200 border-royalBlue-600/30',
    emerald: 'bg-emerald-900/60 text-emerald-300 border-emerald-600/30',
    amber: 'bg-amber-900/60 text-amber-300 border-amber-600/30',
    red: 'bg-red-900/60 text-red-300 border-red-600/30',
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${variants[variant] || variants.blue} ${className}`}
    >
      {children}
    </span>
  );
}
