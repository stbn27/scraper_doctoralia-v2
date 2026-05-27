import React, { useState, useCallback } from 'react';

/**
 * SliderRange — Componente de slider doble para rango de precio.
 * @param {{ min?: number, max?: number, step?: number, value: [number, number], onChange: Function, label?: string, formatValue?: Function }} props
 * @example
 * <SliderRange
 *   min={0} max={10000} value={[0, 5000]}
 *   onChange={([min, max]) => setRange([min, max])}
 *   formatValue={(v) => `$${v.toLocaleString()}`}
 * />
 */
export function SliderRange({
  min = 0,
  max = 10000,
  step = 100,
  value,
  onChange,
  label = '',
  formatValue = (v) => `$${v.toLocaleString('es-MX')}`,
}) {
  const [localValue, setLocalValue] = useState(value);

  const handleMinChange = useCallback((e) => {
    const newMin = Math.min(Number(e.target.value), localValue[1] - step);
    const newValue = [newMin, localValue[1]];
    setLocalValue(newValue);
    onChange(newValue);
  }, [localValue, step, onChange]);

  const handleMaxChange = useCallback((e) => {
    const newMax = Math.max(Number(e.target.value), localValue[0] + step);
    const newValue = [localValue[0], newMax];
    setLocalValue(newValue);
    onChange(newValue);
  }, [localValue, step, onChange]);

  const minPercent = ((localValue[0] - min) / (max - min)) * 100;
  const maxPercent = ((localValue[1] - min) / (max - min)) * 100;

  return (
    <div className="space-y-2">
      {label && (
        <label className="block text-sm font-medium" style={{ color: 'var(--text-muted)' }}>
          {label}
        </label>
      )}
      <div className="flex justify-between text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
        <span>{formatValue(localValue[0])}</span>
        <span>{formatValue(localValue[1])}</span>
      </div>
      <div className="relative h-6">
        {/* Pista de fondo */}
        <div className="absolute top-1/2 -translate-y-1/2 w-full h-1.5 rounded-full bg-white/10" />
        {/* Pista activa */}
        <div
          className="absolute top-1/2 -translate-y-1/2 h-1.5 rounded-full bg-royalBlue-500"
          style={{ left: `${minPercent}%`, width: `${maxPercent - minPercent}%` }}
        />
        {/* Input min */}
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={localValue[0]}
          onChange={handleMinChange}
          className="absolute top-0 w-full h-6 appearance-none bg-transparent pointer-events-none [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-royalBlue-500 [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-white [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:shadow-lg"
        />
        {/* Input max */}
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={localValue[1]}
          onChange={handleMaxChange}
          className="absolute top-0 w-full h-6 appearance-none bg-transparent pointer-events-none [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-royalBlue-500 [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-white [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:shadow-lg"
        />
      </div>
    </div>
  );
}
