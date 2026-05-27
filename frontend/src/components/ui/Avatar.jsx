import React from 'react';

/**
 * Genera un color HSL determinista basado en un string (hash).
 * @param {string} str — String a convertir en color (ej: _id).
 * @returns {string} Color HSL.
 */
function stringToColor(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue = Math.abs(hash) % 360;
  return `hsl(${hue}, 60%, 45%)`;
}

/**
 * Obtiene las iniciales de un nombre (máx. 2 letras).
 * @param {string} name — Nombre completo.
 * @returns {string}
 */
function getInitials(name) {
  if (!name) return '?';
  const parts = name.split(' ').filter((p) => p.length > 0 && p[0] === p[0].toUpperCase());
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
}

/**
 * Avatar — Componente de avatar con iniciales y color generado por hash.
 * @param {{ name: string, id?: string, size?: number, className?: string }} props
 * @example
 * <Avatar name="Dra. María Aquino" id="6a13b0c4" size={48} />
 */
export function Avatar({ name, id = '', size = 48, className = '' }) {
  const bgColor = stringToColor(id || name);
  const initials = getInitials(name);

  return (
    <div
      className={`flex items-center justify-center rounded-full font-semibold text-white select-none shrink-0 ${className}`}
      style={{
        width: size,
        height: size,
        backgroundColor: bgColor,
        fontSize: size * 0.36,
      }}
      title={name}
      aria-label={`Avatar de ${name}`}
    >
      {initials}
    </div>
  );
}
