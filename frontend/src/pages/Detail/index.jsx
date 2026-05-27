import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  RiArrowLeftLine,
  RiMapPinLine,
  RiShieldCheckLine,
  RiHeartLine,
  RiHeartFill,
  RiExternalLinkLine,
  RiArrowDownSLine,
} from 'react-icons/ri';
import { PageWrapper } from '@/components/layout/PageWrapper';
import { BubbleBackground } from '@/components/layout/BubbleBackground';
import { Navbar } from '@/components/layout/Navbar';
import { Avatar } from '@/components/ui/Avatar';
import { Badge } from '@/components/ui/Badge';
import { ScoreDonut } from '@/components/ui/ScoreDonut';
import { StarRating } from '@/components/ui/StarRating';
import { Button } from '@/components/ui/Button';
import { SkeletonCard } from '@/components/ui/SkeletonCard';
import { useToast } from '@/hooks/useToast';
import { useAuth } from '@/hooks/useAuth';
import { getSpecialistById, getReviewSummary, addFavorite, removeFavorite, isFavorite } from '@/services/api';

/**
 * Detail — Página de detalle del especialista.
 * Muestra hero, servicios, experiencia, consultorio y reseñas.
 */
export default function Detail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { addToast } = useToast();

  const [specialist, setSpecialist] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reviewSummary, setReviewSummary] = useState('');
  const [showAllServices, setShowAllServices] = useState(false);
  const [fav, setFav] = useState(false);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const [data, review] = await Promise.all([
          getSpecialistById(id),
          getReviewSummary(id),
        ]);
        setSpecialist(data);
        setReviewSummary(review);
        setFav(isFavorite(id));
      } catch (err) {
        console.error('Error al cargar especialista:', err);
        addToast({ type: 'error', message: 'Error al cargar los datos del especialista.' });
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [id, addToast]);

  /**
   * Maneja el toggle de favorito.
   */
  const handleFavorite = async () => {
    if (!user) {
      addToast({ type: 'info', message: 'Inicia sesión para guardar favoritos.' });
      navigate('/login');
      return;
    }

    try {
      if (fav) {
        await removeFavorite(id);
        setFav(false);
        addToast({ type: 'success', message: 'Eliminado de favoritos.' });
      } else {
        await addFavorite(id);
        setFav(true);
        addToast({ type: 'success', message: 'Especialista guardado en favoritos.' });
      }
    } catch {
      addToast({ type: 'error', message: 'Error al actualizar favoritos.' });
    }
  };

  /**
   * Abre Google Maps con la dirección del consultorio.
   * @param {string} direccion
   */
  const openMap = (direccion) => {
    window.open(`https://www.google.com/maps/search/${encodeURIComponent(direccion)}`, '_blank');
  };

  if (loading) {
    return (
      <PageWrapper name="detail">
        <BubbleBackground />
        <Navbar />
        <div className="relative z-10 pt-20 pb-8 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto space-y-6">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </PageWrapper>
    );
  }

  if (!specialist) {
    return (
      <PageWrapper name="detail">
        <BubbleBackground />
        <Navbar />
        <div className="relative z-10 pt-20 pb-8 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto">
          <div className="glass-card p-12 text-center">
            <p className="text-lg font-medium mb-4">Especialista no encontrado.</p>
            <Button variant="outline" onClick={() => navigate('/resultados')}>
              <RiArrowLeftLine /> Volver a resultados
            </Button>
          </div>
        </div>
      </PageWrapper>
    );
  }

  const consultorio = specialist.consultorios?.[0];
  const visibleServices = showAllServices
    ? specialist.servicios
    : specialist.servicios?.slice(0, 6);

  return (
    <PageWrapper name="detail">
      <BubbleBackground />
      <Navbar />

      <div className="relative z-10 pt-20 pb-8 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto space-y-6">
        {/* Botón volver */}
        <button
          onClick={() => navigate('/resultados')}
          className="flex items-center gap-2 text-sm hover:text-royalBlue-400 transition-colors"
          style={{ color: 'var(--text-muted)' }}
        >
          <RiArrowLeftLine /> Volver a resultados
        </button>

        {/* Hero */}
        <section className="glass-card p-6 sm:p-8 scroll-reveal">
          <div className="flex flex-col sm:flex-row gap-6">
            {/* Lado izquierdo: info principal */}
            <div className="flex-1">
              <div className="flex items-start gap-4 mb-4">
                <Avatar name={specialist.nombre} id={specialist._id} size={96} className="text-2xl" />
                <div className="flex-1 min-w-0">
                  <h1 className="text-xl sm:text-2xl font-bold leading-tight">{specialist.nombre}</h1>
                  <Badge variant="blue" className="mt-2">{specialist.especialidad}</Badge>

                  <div className="flex items-center gap-2 mt-3">
                    <StarRating rating={specialist.rating_global} />
                    <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                      {specialist.total_opiniones} opiniones
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5 mt-2" style={{ color: 'var(--text-muted)' }}>
                    <RiMapPinLine className="shrink-0" />
                    <span className="text-sm">{specialist.ciudad}</span>
                    {consultorio && <span className="text-sm">— {consultorio.direccion}</span>}
                  </div>
                </div>
              </div>

              {/* Chips de pacientes */}
              <div className="flex flex-wrap gap-2 mt-4">
                {specialist.pacientes?.atiende_ninos && (
                  <Badge variant="emerald">Atiende niños</Badge>
                )}
                {specialist.pacientes?.atiende_adultos && (
                  <Badge variant="emerald">Atiende adultos</Badge>
                )}
                {specialist.pacientes?.atiende_adolescentes && (
                  <Badge variant="emerald">Atiende adolescentes</Badge>
                )}
              </div>

              {/* Cédula */}
              {specialist.cedula && (
                <div className="flex items-center gap-2 mt-4 text-sm text-emerald-400">
                  <RiShieldCheckLine />
                  <span>Cédula: {specialist.cedula}</span>
                </div>
              )}

              {/* Botón favorito */}
              <Button
                variant={fav ? 'outline' : 'primary'}
                icon={fav ? <RiHeartFill className="text-red-400" /> : <RiHeartLine />}
                onClick={handleFavorite}
                className="mt-5"
              >
                {fav ? 'Guardado en favoritos' : 'Guardar favorito'}
              </Button>
            </div>

            {/* Lado derecho: Score donut grande */}
            <div className="flex flex-col items-center justify-center sm:border-l sm:border-white/10 sm:pl-8">
              <ScoreDonut score={specialist.score_recomendacion} size={120} strokeWidth={6} />
              <p className="text-xs mt-3 text-center" style={{ color: 'var(--text-muted)' }}>
                Score de recomendación
              </p>
            </div>
          </div>
        </section>

        {/* Experiencia */}
        <section className="glass-card p-6 scroll-reveal">
          <h2 className="text-lg font-semibold mb-4">Experiencia / Sobre el especialista</h2>
          {specialist.experiencia?.length > 0 ? (
            <div className="space-y-3">
              {specialist.experiencia.map((text, i) => (
                <p key={i} className="text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                  {text}
                </p>
              ))}
            </div>
          ) : (
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              Sin información disponible.
            </p>
          )}
        </section>

        {/* Servicios y precios */}
        <section className="glass-card p-6 scroll-reveal">
          <h2 className="text-lg font-semibold mb-4">Servicios y precios</h2>
          {specialist.servicios?.length > 0 ? (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {visibleServices.map((serv, i) => (
                  <div key={i} className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/5">
                    <span className="text-sm">{serv.nombre}</span>
                    <span className="text-sm font-semibold text-royalBlue-300">{serv.precio_texto}</span>
                  </div>
                ))}
              </div>
              {specialist.servicios.length > 6 && !showAllServices && (
                <Button
                  variant="ghost"
                  onClick={() => setShowAllServices(true)}
                  className="mt-3"
                  icon={<RiArrowDownSLine />}
                >
                  Ver todos ({specialist.servicios.length})
                </Button>
              )}
            </>
          ) : (
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Sin servicios registrados.</p>
          )}
        </section>

        {/* Consultorio */}
        {consultorio && (
          <section className="glass-card p-6 scroll-reveal">
            <h2 className="text-lg font-semibold mb-4">Consultorio</h2>
            {consultorio.clinica && (
              <p className="text-sm font-medium mb-1">{consultorio.clinica}</p>
            )}
            <p className="text-sm mb-4" style={{ color: 'var(--text-muted)' }}>
              {consultorio.direccion}
            </p>
            <Button
              variant="outline"
              icon={<RiExternalLinkLine />}
              onClick={() => openMap(consultorio.direccion)}
            >
              Ver en mapa
            </Button>
          </section>
        )}

        {/* Resumen de reseñas (mock PLN) */}
        <section className="scroll-reveal">
          <div
            className="p-6 rounded-xl border-l-4"
            style={{
              background: 'rgba(23, 37, 84, 0.4)',
              borderColor: 'var(--color-primary-500)',
            }}
          >
            <h2 className="text-lg font-semibold mb-3">Resumen de reseñas</h2>
            <p className="text-sm leading-relaxed italic" style={{ color: 'var(--text-muted)' }}>
              "{reviewSummary}"
            </p>
          </div>
        </section>
      </div>
    </PageWrapper>
  );
}
