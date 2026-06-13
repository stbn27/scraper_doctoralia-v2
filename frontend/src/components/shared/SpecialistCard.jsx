import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  RiMapPin2Line,
  RiHeartLine,
  RiHeartFill,
  RiUserLine,
  RiAlertLine,
  RiSparkling2Line
} from 'react-icons/ri';
import { Avatar } from '@/components/ui/Avatar';
import { StarRating } from '@/components/ui/StarRating';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/hooks/useToast';
import { addFavorite, removeFavorite, isFavorite } from '@/services/api';

/**
 * Devuelve color y etiqueta del score IA.
 * @param {number|null} puntuacion — Valor 0–10.
 */
function resolveScore(puntuacion) {
  const n = typeof puntuacion === 'number' ? puntuacion : parseFloat(puntuacion);
  if (isNaN(n) || puntuacion === null || puntuacion === undefined) return null;
  const clamped = Math.min(10, Math.max(0, n));
  let color;
  if (clamped >= 8) color = 'text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
  else if (clamped >= 6) color = 'text-royalBlue-600 dark:text-royalBlue-300 bg-royalBlue-500/10 border-royalBlue-500/20';
  else if (clamped >= 4) color = 'text-amber-600 dark:text-amber-400 bg-amber-500/10 border-amber-500/20';
  else color = 'text-red-600 dark:text-red-400 bg-red-500/10 border-red-500/20';
  return { label: `${clamped.toFixed(1)}/10`, color };
}

/**
 * Devuelve clases y etiqueta de confiabilidad IA.
 * @param {string} conf — 'alta' | 'media' | 'baja' | 'sospechosa'
 */
function resolveConfiabilidad(conf) {
  const c = String(conf || '').toLowerCase();
  if (c === 'alta') return { label: 'Confiable', cls: 'text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border-emerald-500/20' };
  if (c === 'media') return { label: 'Confiab. media', cls: 'text-royalBlue-600 dark:text-royalBlue-300 bg-royalBlue-500/10 border-royalBlue-500/20' };
  if (c === 'baja') return { label: 'Confiab. baja', cls: 'text-amber-600 dark:text-amber-400 bg-amber-500/10 border-amber-500/20' };
  if (c === 'sospechosa') return { label: 'Revisar', cls: 'text-red-600 dark:text-red-400 bg-red-500/10 border-red-500/20' };
  return null;
}

/**
 * SpecialistCard — Tarjeta de especialista para listado de búsqueda y favoritos.
 * Diseño limpio, compatible con modo claro y oscuro.
 * @param {{ specialist: Object, showDelete?: boolean, onDelete?: Function, index?: number }} props
 */
export function SpecialistCard({ specialist, showDelete = false, onDelete = null, index = 0 }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const { addToast } = useToast();
  const [fav, setFav] = useState(isFavorite(specialist._id));
  const [favLoading, setFavLoading] = useState(false);
  const [visible, setVisible] = useState(false);

  // Aparición suave escalonada
  React.useEffect(() => {
    const t = setTimeout(() => setVisible(true), index * 60);
    return () => clearTimeout(t);
  }, [index]);

  // Precio mínimo desde servicios
  const prices = (specialist.servicios || [])
    .map(s => s.precio_desde)
    .filter(p => typeof p === 'number' && !isNaN(p));
  const minPrice = prices.length > 0 ? Math.min(...prices) : null;

  const ia = specialist.analisis || {};
  const hasIa = ia.tiene_analisis || ia.puntuacion_recomendacion != null;
  const scoreInfo = resolveScore(ia.puntuacion_recomendacion);
  const confInfo = hasIa ? resolveConfiabilidad(ia.confiabilidad_opiniones) : null;
  const hasFraud = !!(ia.sospecha_fraude || ia.metricas_locales?.sospecha_fraude);

  // Pacientes
  const pacientes = [];
  if (specialist.pacientes?.atiende_ninos) pacientes.push('Niños');
  if (specialist.pacientes?.atiende_adultos) pacientes.push('Adultos');
  if (specialist.pacientes?.atiende_adolescentes) pacientes.push('Adolescentes');

  /**
   * Toggle favorito con login guard.
   */
  const handleFavorite = async () => {
    if (!user) {
      addToast({ type: 'info', message: 'Inicia sesión para guardar favoritos.' });
      navigate('/login', { state: { from: location.pathname } });
      return;
    }
    setFavLoading(true);
    try {
      if (fav) {
        await removeFavorite(specialist._id);
        setFav(false);
        addToast({ type: 'success', message: 'Eliminado de favoritos.' });
        if (onDelete) onDelete(specialist._id);
      } else {
        await addFavorite(specialist._id);
        setFav(true);
        addToast({ type: 'success', message: 'Especialista guardado en favoritos.' });
      }
    } catch {
      addToast({ type: 'error', message: 'Error al actualizar favoritos.' });
    } finally {
      setFavLoading(false);
    }
  };

  return (
    <div
      className={`glass-card rounded-tl-none flex flex-col transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'
        }`}
      style={{ transitionDelay: `${index * 40}ms` }}
    >
      {/* Franja de acento superior */}
      <div className="h-0.5 w-full rounded-t-xl bg-gradient-to-r from-royalBlue-500/50 via-royalBlue-400/20 to-transparent" />

      <div className="p-4 flex flex-col gap-3 flex-1">
        {/* ── Fila 1: Avatar · Nombre/ciudad · Favorito ── */}
        <div className="flex items-start gap-3">
          <Avatar
            name={specialist.nombre}
            id={specialist._id}
            src={specialist.foto_perfil_url}
            size={44}
            className="shrink-0"
          />

          <div className="flex-1 min-w-0">
            <h3
              className="font-semibold text-sm leading-tight cursor-pointer hover:text-royalBlue-500 dark:hover:text-royalBlue-400 transition-colors"
              style={{ color: 'var(--text-primary)' }}
              title={specialist.nombre}
              onClick={() => navigate(`/especialistas/${specialist._id}`)}
            >
              {specialist.nombre}
            </h3>
            {specialist.especialidad && (
              <p className="text-xs mt-0.5 font-medium text-royalBlue-500 dark:text-royalBlue-400 truncate">
                {specialist.especialidad}
              </p>
            )}
            <div className="flex items-start gap-1 mt-0.5" style={{ color: 'var(--text-muted)' }}>
              <RiMapPin2Line className="text-xs shrink-0 mt-0.5" />
              <span className="text-xs line-clamp-2">
                {specialist.ciudad || specialist.consultorio_principal?.direccion || 'Ubicación no especificada'}
              </span>
            </div>
          </div>

          {/* Favorito */}
          <button
            onClick={handleFavorite}
            disabled={favLoading}
            className={`p-1.5 rounded-lg shrink-0 transition-all duration-200 ${fav
                ? 'text-red-500 bg-red-500/10 hover:bg-red-500/15'
                : 'hover:bg-black/5 dark:hover:bg-white/10'
              }`}
            style={!fav ? { color: 'var(--text-muted)' } : {}}
            aria-label={fav ? 'Quitar de favoritos' : 'Agregar a favoritos'}
          >
            {fav ? <RiHeartFill className="text-base" /> : <RiHeartLine className="text-base" />}
          </button>
        </div>

        {/* ── Fila 2: Rating + opiniones ── */}
        <div className="flex items-center gap-1.5">
          <StarRating rating={specialist.rating_global} />
          <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
            {specialist.total_opiniones
              ? `${specialist.total_opiniones} ${specialist.total_opiniones === 1 ? 'reseña' : 'reseñas'}`
              : 'Sin reseñas'}
          </span>
        </div>

        {/* ── Fila 3: Badges IA + pacientes ── */}
        <div className="flex flex-wrap gap-1.5">
          {/* Score IA */}
          {scoreInfo ? (
            <span className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full border ${scoreInfo.color}`}>
              <RiSparkling2Line className="text-[10px]" />
              {scoreInfo.label}
            </span>
          ) : (
            <span className="inline-flex text-[10px] font-medium px-2 py-0.5 rounded-full border border-white/10 bg-white/5" style={{ color: 'var(--text-muted)' }}>
              Sin análisis IA
            </span>
          )}

          {/* Confiabilidad */}
          {confInfo && !hasFraud && (
            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${confInfo.cls}`}>
              {confInfo.label}
            </span>
          )}

          {/* Sospecha de fraude */}
          {hasFraud && (
            <span className="inline-flex items-center gap-0.5 text-[10px] font-semibold px-2 py-0.5 rounded-full border border-amber-500/20 bg-amber-500/10 text-amber-600 dark:text-amber-400">
              <RiAlertLine className="text-[10px]" /> Revisar opiniones
            </span>
          )}

          {/* Pacientes */}
          {pacientes.map(p => (
            <span
              key={p}
              className="inline-flex items-center gap-0.5 text-[10px] font-medium px-2 py-0.5 rounded-full border border-white/10 bg-white/5"
              style={{ color: 'var(--text-muted)' }}
            >
              <RiUserLine className="text-[10px]" /> {p}
            </span>
          ))}
        </div>

        {/* ── Footer: precio + botón perfil ── */}
        <div className="flex items-center justify-between mt-auto pt-3 border-t border-black/5 dark:border-white/5">
          {minPrice != null ? (
            <div className="flex flex-col leading-tight">
              <span className="text-[9px] uppercase tracking-widest font-semibold" style={{ color: 'var(--text-muted)' }}>
                Desde
              </span>
              <span className="text-sm font-bold text-royalBlue-500 dark:text-royalBlue-400">
                ${minPrice.toLocaleString('es-MX')}
              </span>
            </div>
          ) : (
            <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
              Precio no publicado
            </span>
          )}

          <button
            onClick={() => navigate(`/especialistas/${specialist._id}`)}
            className="text-xs font-semibold px-3.5 py-1.5 rounded-lg bg-royalBlue-600 hover:bg-royalBlue-500 active:bg-royalBlue-700 text-white transition-colors shadow-sm"
          >
            Ver perfil
          </button>
        </div>
      </div>
    </div>
  );
}
