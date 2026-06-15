import React from 'react';
import { RiStarFill, RiStarLine } from 'react-icons/ri';

/**
 * StarRating — Componente de estrellas de calificación.
 * @param {{ rating: number, maxStars?: number, showNumber?: boolean, className?: string }} props
 * @example
 * <StarRating rating={4.5} showNumber />
 */
export function StarRating({ rating = 0, maxStars = 5, showNumber = true, className = '' }) {
  const safeRating = Number(rating) || 0;
  const stars = [];

  for (let i = 1; i <= maxStars; i++) {
    stars.push(
      i <= Math.round(safeRating) ? (
        <RiStarFill key={i} className="text-amber-400" />
      ) : (
        <RiStarLine key={i} className="text-amber-400/30" />
      )
    );
  }

  return (
    <div className={`inline-flex items-center gap-0.5 ${className}`}>
      {stars}
      {showNumber && (
        <span className="ml-1.5 text-sm font-medium" style={{ color: 'var(--text-muted)' }}>
          ({safeRating.toFixed(1)})
        </span>
      )}
    </div>
  );
}
