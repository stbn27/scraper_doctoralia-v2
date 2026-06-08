import React, { useState } from 'react';

/**
 * Genera un color HSL determinista basado en un string (hash).
 * @param {string} str — String a convertir en color (ej: _id).
 * @returns {string} Color HSL.
 */
function stringToColor(str) {
  if (!str) return 'hsl(220, 60%, 45%)';
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
  
  // Guardar contra nombres que sean URLs accidentales
  const str = String(name).trim();
  if (str.startsWith('http://') || str.startsWith('https://') || str.includes('/') || str.includes('.')) {
    return 'MC'; // Fallback genérico: "Médico / Consultorio"
  }

  // Filtrar palabras que comiencen con mayúscula
  const parts = str.split(/\s+/).filter((p) => p.length > 0 && p[0] === p[0].toUpperCase());
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }
  return str.slice(0, 2).toUpperCase();
}

/**
 * Avatar — Componente de avatar con imagen (foto_perfil_url), fallback a iniciales con color determinista.
 * @param {{ name: string, id?: string, src?: string, size?: number, className?: string }} props
 * @example
 * <Avatar name="Dra. María Aquino" id="6a13b0c4" src="http://..." size={48} />
 */
export function Avatar({ name, id = '', src = '', size = 48, className = '' }) {
  const [hasError, setHasError] = useState(false);
  const bgColor = stringToColor(id || name);
  const initials = getInitials(name);

  // Si tiene URL de imagen y no ha fallado la carga, renderizar la imagen
  if (src && !hasError) {
    return (
      <img
        src={src}
        alt={`Avatar de ${name}`}
        onError={() => setHasError(true)}
        className={`rounded-full object-cover shrink-0 select-none border border-white/10 ${className}`}
        style={{
          width: size,
          height: size,
        }}
      />
    );
  }

  // Fallback a iniciales con color de fondo determinista
  return (
    <div
      className={`flex items-center justify-center rounded-full font-semibold text-white select-none shrink-0 border border-white/5 ${className}`}
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
