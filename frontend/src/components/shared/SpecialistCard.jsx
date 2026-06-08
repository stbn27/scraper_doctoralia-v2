import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { RiMapPinLine, RiHeartLine, RiHeartFill } from 'react-icons/ri';
import { Avatar } from '@/components/ui/Avatar';
import { Badge } from '@/components/ui/Badge';
import { ScoreDonut } from '@/components/ui/ScoreDonut';
import { StarRating } from '@/components/ui/StarRating';
import { Button } from '@/components/ui/Button';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/hooks/useToast';
import { addFavorite, removeFavorite, isFavorite } from '@/services/api';

/**
 * SpecialistCard — Tarjeta de especialista reutilizable (Búsqueda y Favoritos).
 * @param {{ specialist: Object, showDelete?: boolean, onDelete?: Function }} props
 */
export function SpecialistCard({ specialist, showDelete = false, onDelete = null }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const { addToast } = useToast();
  const [fav, setFav] = useState(isFavorite(specialist._id));
  const [favLoading, setFavLoading] = useState(false);

  const minPrice = specialist.servicios?.length > 0
    ? Math.min(...specialist.servicios.map((s) => s.precio_desde))
    : null;

  const ia = specialist.analisis || {};
  const hasIa = ia.tiene_analisis || ia.puntuacion_recomendacion !== undefined;

  /**
   * Maneja el toggle de favorito.
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

  /**
   * Determina el badge de confiabilidad de la IA.
   */
  const renderConfiabilidadBadge = () => {
    if (!hasIa) return null;

    if (ia.sospecha_fraude || ia.metricas_locales?.sospecha_fraude) {
      return <Badge variant="red">Sospecha Fraude</Badge>;
    }

    const conf = String(ia.confiabilidad_opiniones || '').toLowerCase();
    if (conf === 'alta') return <Badge variant="emerald">IA Confiable</Badge>;
    if (conf === 'media') return <Badge variant="blue">IA Media</Badge>;
    if (conf === 'baja') return <Badge variant="amber">IA Baja</Badge>;

    return null;
  };

  return (
    <div className="glass-card p-5 hover-lift flex flex-col gap-3.5 transition-all">
      {/* Header: Avatar, Info de Nombre y Favorito */}
      <div className="flex items-start gap-3">
        <Avatar name={specialist.nombre} id={specialist._id} size={48} />
        <div className="flex-1 min-w-0">
          <h3
            className="font-bold text-sm leading-tight text-slate-100 truncate cursor-pointer hover:text-royalBlue-400 transition-colors"
            title={specialist.nombre}
            onClick={() => navigate(`/especialistas/${specialist._id}`)}
          >
            {specialist.nombre}
          </h3>
          <div className="flex items-center gap-1 mt-1" style={{ color: 'var(--text-muted)' }}>
            <RiMapPinLine className="text-xs shrink-0" />
            <span className="text-xs truncate">{specialist.ciudad}</span>
          </div>
        </div>
        {/* Botón Favorito */}
        <button
          onClick={handleFavorite}
          disabled={favLoading}
          className={`p-2 rounded-xl transition-all duration-200 shrink-0 ${
            fav ? 'text-red-400 bg-red-400/5 hover:bg-red-400/10' : 'hover:bg-white/10'
          }`}
          style={!fav ? { color: 'var(--text-muted)' } : {}}
          aria-label={fav ? 'Quitar de favoritos' : 'Agregar a favoritos'}
        >
          {fav ? <RiHeartFill className="text-lg" /> : <RiHeartLine className="text-lg" />}
        </button>
      </div>

      {/* Badges de Especialidad y Confiabilidad IA */}
      <div className="flex flex-wrap gap-1.5">
        <Badge variant="blue">{specialist.especialidad}</Badge>
        {renderConfiabilidadBadge()}
      </div>

      {/* Rating y Reseñas */}
      <div className="flex items-center gap-2">
        <StarRating rating={specialist.rating_global} />
        <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
          ({specialist.total_opiniones} {specialist.total_opiniones === 1 ? 'reseña' : 'reseñas'})
        </span>
      </div>

      {/* Resumen de IA en máximo 2 líneas */}
      <div className="text-[11px] leading-relaxed text-slate-300 min-h-[34px]">
        {hasIa && ia.resumen ? (
          <p className="line-clamp-2 italic font-light border-l border-royalBlue-500/20 pl-2">
            "{ia.resumen}"
          </p>
        ) : (
          <p className="italic text-slate-500 font-light pl-2">
            Sin análisis IA
          </p>
        )}
      </div>

      {/* Footer: Donut IA + Precio Mínimo + Botón Ver Perfil */}
      <div className="flex items-center justify-between mt-auto pt-3 border-t border-white/5">
        <div className="flex items-center gap-3">
          <div className="flex flex-col items-center">
            <ScoreDonut score={ia.puntuacion_recomendacion} size={42} strokeWidth={3.5} />
          </div>
          
          <div className="flex flex-col">
            {minPrice != null ? (
              <>
                <span className="text-[9px] uppercase tracking-wider opacity-60" style={{ color: 'var(--text-muted)' }}>Desde</span>
                <span className="text-xs font-semibold text-slate-200">${minPrice.toLocaleString('es-MX')}</span>
              </>
            ) : (
              <span className="text-[9px] uppercase tracking-wider opacity-60" style={{ color: 'var(--text-muted)' }}>
                {hasIa ? 'Score IA' : 'Sin Score'}
              </span>
            )}
          </div>
        </div>

        <Button
          variant="primary"
          className="text-xs px-3.5 py-1.5 rounded-xl"
          onClick={() => navigate(`/especialistas/${specialist._id}`)}
        >
          Ver perfil
        </Button>
      </div>
    </div>
  );
}
