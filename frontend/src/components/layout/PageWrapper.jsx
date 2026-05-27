import React from 'react';
import { useScrollTrigger } from '@/hooks/useScrollTrigger';

/**
 * PageWrapper — Wrapper de página con view-transition-name y scroll-trigger.
 * @param {{ children: React.ReactNode, className?: string, name?: string }} props
 * @example
 * <PageWrapper name="results">
 *   <h1>Resultados</h1>
 * </PageWrapper>
 */
export function PageWrapper({ children, className = '', name = 'page' }) {
  useScrollTrigger();

  return (
    <div
      className={`page-enter min-h-screen ${className}`}
      style={{ viewTransitionName: name }}
    >
      {children}
    </div>
  );
}
