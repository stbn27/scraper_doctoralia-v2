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
    <>
      {/* Fondo dark mode */}
      <div
        className={`fixed inset-0 -z-10 h-full w-full dark:block hidden ${className}`}
        style={{
          background: 'radial-gradient(125% 125% at 50% 10%, #04010fff 40%, rgba(3, 50, 74, 1) 100%)',
        }}
      />
      {/* Fondo light mode */}
      <div
        className={`fixed inset-0 -z-10 h-full w-full dark:hidden block ${className}`}
        style={{
          background: 'radial-gradient(125% 125% at 50% 10%, #fff 40%, rgba(10, 152, 200, 1) 100%)',
        }}
      />
    </>
  );
}
