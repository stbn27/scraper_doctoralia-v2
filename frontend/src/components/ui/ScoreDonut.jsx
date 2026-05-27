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
 * @param {{ score: number, size?: number, strokeWidth?: number, className?: string }} props
 * @example
 * <ScoreDonut score={87.4} size={56} />           // Compacto (tarjetas)
 * <ScoreDonut score={87.4} size={120} />           // Grande (detalle)
 */
export function ScoreDonut({ score, size = 56, strokeWidth = 4, className = '' }) {
  const [offset, setOffset] = useState(0);
  const radius = (size / 2) - strokeWidth;
  const circumference = 2 * Math.PI * radius;
  const targetOffset = circumference - (score / 100) * circumference;

  useEffect(() => {
    // Inicializar sin progreso
    setOffset(circumference);
    // Animar después de un frame
    const timer = requestAnimationFrame(() => {
      setTimeout(() => setOffset(targetOffset), 50);
    });
    return () => cancelAnimationFrame(timer);
  }, [score, circumference, targetOffset]);

  const color = scoreColor(score);
  const fontSize = size >= 100 ? '1.25rem' : size >= 70 ? '0.875rem' : '0.7rem';

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
          stroke="rgba(255,255,255,0.1)"
          strokeWidth={strokeWidth}
        />
        {/* Arco de progreso */}
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
      </svg>
      {/* Porcentaje en el centro */}
      <span
        className="absolute font-semibold"
        style={{ fontSize, color }}
      >
        {Math.round(score)}%
      </span>
    </div>
  );
}
