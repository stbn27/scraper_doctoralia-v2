import React, { useEffect, useState } from 'react';

/**
 * Determina el color del arco según el score.
 * @param {number} score — Score de recomendación (0-100).
 * @returns {string} Color hex.
 */
function scoreColor(score) {
  if (score >= 80) return 'var(--score-high)';    // emerald
  if (score >= 60) return 'var(--score-mid)';     // blue
  if (score >= 40) return 'var(--score-low)';     // amber
  return 'var(--score-critical)';                  // red
}

/**
 * ScoreDonut — Anillo SVG con porcentaje animado.
 * @param {{ score: number|string|null|undefined, size?: number, strokeWidth?: number, className?: string }} props
 * @example
 * <ScoreDonut score={8.7} size={56} />            // En escala 0-10
 * <ScoreDonut score={87} size={56} />             // En escala 0-100
 */
export function ScoreDonut({ score, size = 56, strokeWidth = 4, className = '' }) {
  const parsed = typeof score === 'number' ? score : parseFloat(score);
  const hasScore = !isNaN(parsed) && score !== null && score !== undefined;
  
  // Si viene en escala 0–10, convertir a 0–100
  const adjustedScore = hasScore ? (parsed <= 10 ? parsed * 10 : parsed) : null;
  
  const [offset, setOffset] = useState(0);
  const radius = (size / 2) - strokeWidth;
  const circumference = 2 * Math.PI * radius;
  const targetOffset = hasScore ? (circumference - (adjustedScore / 100) * circumference) : circumference;

  useEffect(() => {
    setOffset(circumference);
    if (hasScore) {
      const timer = requestAnimationFrame(() => {
        setTimeout(() => setOffset(targetOffset), 50);
      });
      return () => cancelAnimationFrame(timer);
    }
  }, [adjustedScore, circumference, targetOffset, hasScore]);

  // Si no hay score, usar un color neutro grisáceo en lugar de rojo crítico
  const color = hasScore ? scoreColor(adjustedScore) : 'rgba(255, 255, 255, 0.2)';
  const fontSize = size >= 100 ? '1.15rem' : size >= 70 ? '0.875rem' : '0.65rem';

  return (
    <div className={`relative inline-flex items-center justify-center ${className}`} style={{ width: size, height: size }}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="-rotate-90"
      >
        {/* Pista de fondo */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth={strokeWidth}
        />
        {/* Arco de progreso */}
        {hasScore && (
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            style={{ transition: 'stroke-dashoffset 0.8s ease-out' }}
          />
        )}
      </svg>
      {/* Porcentaje en el centro */}
      <span
        className="absolute font-semibold text-center leading-none"
        style={{ fontSize, color }}
      >
        {hasScore ? `${Math.round(adjustedScore)}%` : '—'}
      </span>
    </div>
  );
}
