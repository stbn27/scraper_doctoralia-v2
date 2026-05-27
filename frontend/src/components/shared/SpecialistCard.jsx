import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
 * SpecialistCard — Tarjeta de especialista reutilizable (Results y Dashboard).
 * @param {{ specialist: Object, showDelete?: boolean, onDelete?: Function }} props
 * @example
 * <SpecialistCard specialist={specialist} />
 */
export function SpecialistCard({ specialist, showDelete = false, onDelete = null }) {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { addToast } = useToast();
  const [fav, setFav] = useState(isFavorite(specialist._id));
  const [favLoading, setFavLoading] = useState(false);

  const minPrice = specialist.servicios?.length > 0
    ? Math.min(...specialist.servicios.map((s) => s.precio_desde))
    : null;

  /**
   * Maneja el toggle de favorito.
   */
  const handleFavorite = async () => {
    if (!user) {
      addToast({ type: 'info', message: 'Inicia sesión para guardar favoritos.' });
      navigate('/login');
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
    <div className="glass-card p-5 hover-lift flex flex-col gap-4">
      {/* Header: Avatar + Nombre */}
      <div className="flex items-start gap-3">
        <Avatar name={specialist.nombre} id={specialist._id} size={48} />
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-sm leading-tight truncate" title={specialist.nombre}>
            {specialist.nombre}
          </h3>
          <div className="flex items-center gap-1.5 mt-1" style={{ color: 'var(--text-muted)' }}>
            <RiMapPinLine className="text-xs shrink-0" />
            <span className="text-xs truncate">{specialist.ciudad}</span>
          </div>
        </div>
        {/* Botón favorito */}
        <button
          onClick={handleFavorite}
          disabled={favLoading}
          className={`p-2 rounded-lg transition-all duration-200 shrink-0 ${
            fav ? 'text-red-400 hover:bg-red-400/10' : 'hover:bg-white/10'
          }`}
          style={!fav ? { color: 'var(--text-muted)' } : {}}
          aria-label={fav ? 'Quitar de favoritos' : 'Agregar a favoritos'}
        >
          {fav ? <RiHeartFill className="text-xl" /> : <RiHeartLine className="text-xl" />}
        </button>
      </div>

      {/* Badge especialidad */}
      <Badge variant="blue">{specialist.especialidad}</Badge>

      {/* Rating + Opiniones */}
      <div className="flex items-center gap-2">
        <StarRating rating={specialist.rating_global} />
        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
          {specialist.total_opiniones} reseñas
        </span>
      </div>

      {/* Score + Precio + Botón */}
      <div className="flex items-end justify-between mt-auto pt-2">
        <div className="flex items-center gap-3">
          <ScoreDonut score={specialist.score_recomendacion} size={56} strokeWidth={4} />
          {minPrice != null && (
            <div>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Desde</p>
              <p className="text-sm font-semibold">${minPrice.toLocaleString('es-MX')}</p>
            </div>
          )}
        </div>
        <Button
          variant="primary"
          className="text-xs px-4 py-2"
          onClick={() => navigate(`/especialista/${specialist._id}`)}
        >
          Ver perfil
        </Button>
      </div>
    </div>
  );
}
