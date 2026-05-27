import React from 'react';

/**
 * SkeletonCard — Tarjeta de skeleton con efecto shimmer glassmorphism.
 * @param {{ className?: string }} props
 * @example
 * {loading && Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
 */
export function SkeletonCard({ className = '' }) {
  return (
    <div className={`glass-card p-5 space-y-4 ${className}`}>
      {/* Avatar + nombre */}
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 rounded-full skeleton-shimmer" />
        <div className="flex-1 space-y-2">
          <div className="h-4 rounded-lg skeleton-shimmer w-3/4" />
          <div className="h-3 rounded-lg skeleton-shimmer w-1/2" />
        </div>
      </div>
      {/* Badge */}
      <div className="h-6 rounded-full skeleton-shimmer w-24" />
      {/* Info rows */}
      <div className="space-y-2">
        <div className="h-3 rounded-lg skeleton-shimmer w-full" />
        <div className="h-3 rounded-lg skeleton-shimmer w-2/3" />
      </div>
      {/* Score + botón */}
      <div className="flex items-center justify-between pt-2">
        <div className="w-14 h-14 rounded-full skeleton-shimmer" />
        <div className="h-9 rounded-xl skeleton-shimmer w-28" />
      </div>
    </div>
  );
}
