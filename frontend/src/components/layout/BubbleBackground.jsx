import React from 'react';

/**
 * BubbleBackground — Fondo con radial gradient.
 * 
 * Estable el background de las vistas.
 * 
 * Dark: radial-gradient negro → azul-oscuro.
 * Light: radial-gradient blanco → azul-claro.
 * @param {{ className?: string }} props
 * @example
 */
export function BubbleBackground({ className = '' }) {
  return (
    <div
      className={`fixed inset-0 -z-10 h-full w-full ${className}`}
      style={{
        background: 'var(--bubble-bg)',
      }}
    />
  );
}
