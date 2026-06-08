import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import {
  RiArrowLeftLine,
  RiMapPinLine,
  RiShieldCheckLine,
  RiHeartLine,
  RiHeartFill,
  RiExternalLinkLine,
  RiArrowDownSLine,
  RiAlertFill,
  RiCheckboxCircleLine,
  RiCloseCircleLine,
  RiMessage2Line,
  RiCalendarLine,
  RiUser3Line
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
import {
  obtenerDetalleEspecialista,
  obtenerOpinionesEspecialista,
  addFavorite,
  removeFavorite,
  isFavorite
} from '@/services/api';

/**
 * Detail — Página de detalle del especialista.
 * Muestra hero, análisis IA, consultorio, servicios y opiniones paginadas.
 */
export default function Detail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const { addToast } = useToast();

  const [specialist, setSpecialist] = useState(null);
  const [loading, setLoading] = useState(true);
  const [fav, setFav] = useState(false);
  const [showAllServices, setShowAllServices] = useState(false);

  // Estados de opiniones
  const [opinions, setOpinions] = useState([]);
  const [opinionsLoading, setOpinionsLoading] = useState(true);
  const [opinionsPage, setOpinionsPage] = useState(1);
  const [opinionsTotal, setOpinionsTotal] = useState(0);
  const [opinionsPages, setOpinionsPages] = useState(0);

  // Cargar datos del especialista
  useEffect(() => {
    const loadSpecialist = async () => {
      setLoading(true);
      try {
        const data = await obtenerDetalleEspecialista(id);
        if (data) {
          setSpecialist(data);
          setFav(isFavorite(data._id));
        } else {
          setSpecialist(null);
        }
      } catch (err) {
        console.error('Error al cargar especialista:', err);
        addToast({ type: 'error', message: 'Error al cargar los datos del especialista.' });
      } finally {
        setLoading(false);
      }
    };
    loadSpecialist();
  }, [id, addToast]);

  // Cargar opiniones paginadas
  const loadOpinions = useCallback(async () => {
    if (!specialist?._id) return;
    setOpinionsLoading(true);
    try {
      const data = await obtenerOpinionesEspecialista(specialist._id, {
        page: opinionsPage,
        limit: 5
      });
      if (data) {
        setOpinions(data.results || []);
        setOpinionsTotal(data.total || 0);
        setOpinionsPages(data.pages || 0);
      }
    } catch (err) {
      console.error('Error al cargar opiniones:', err);
    } finally {
      setOpinionsLoading(false);
    }
  }, [specialist?._id, opinionsPage]);

  useEffect(() => {
    loadOpinions();
  }, [loadOpinions]);

  /**
   * Maneja el toggle de favorito.
   */
  const handleFavorite = async () => {
    if (!user) {
      addToast({ type: 'info', message: 'Inicia sesión para guardar favoritos.' });
      navigate('/login', { state: { from: location.pathname } });
      return;
    }

    try {
      if (fav) {
        await removeFavorite(specialist._id);
        setFav(false);
        addToast({ type: 'success', message: 'Eliminado de favoritos.' });
      } else {
        await addFavorite(specialist._id);
        setFav(true);
        addToast({ type: 'success', message: 'Especialista guardado en favoritos.' });
      }
    } catch {
      addToast({ type: 'error', message: 'Error al actualizar favoritos.' });
    }
  };

  /**
   * Abre Google Maps con la dirección del consultorio.
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
            <Button variant="outline" onClick={() => navigate('/busqueda')}>
              <RiArrowLeftLine /> Volver a búsqueda
            </Button>
          </div>
        </div>
      </PageWrapper>
    );
  }

  const consultorio = specialist.consultorios?.[0];
  const visibleServices = showAllServices
    ? specialist.servicios || []
    : (specialist.servicios || []).slice(0, 6);

  const ia = specialist.analisis || {};
  const localMetrics = ia.metricas_locales || {};
  const hasIa = ia.tiene_analisis;

  const profileUrl = specialist.scraping_meta?.url_origen || specialist.url_origen || specialist.url || (specialist.doctoralia_id ? `https://www.doctoralia.com.mx/doctor/id/${specialist.doctoralia_id}` : null);

  return (
    <PageWrapper name="detail">
      <BubbleBackground />
      <Navbar />

      <div className="relative z-10 pt-20 pb-8 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto space-y-6">
        {/* Botón volver */}
        <button
          onClick={() => navigate('/busqueda')}
          className="flex items-center gap-2 text-sm hover:text-royalBlue-400 transition-colors"
          style={{ color: 'var(--text-muted)' }}
        >
          <RiArrowLeftLine /> Volver a la búsqueda
        </button>

        {/* Hero Section */}
        <section className="glass-card p-6 sm:p-8 scroll-reveal">
          <div className="flex flex-col sm:flex-row gap-6">
            <div className="flex-1">
              <div className="flex items-start gap-4 mb-4">
                <Avatar name={specialist.nombre} id={specialist._id} src={specialist.foto_perfil_url} size={96} className="text-2xl" />
                <div className="flex-1 min-w-0">
                  <h1 className="text-xl sm:text-2xl font-bold leading-tight">{specialist.nombre}</h1>
                  {specialist.especialidad && <Badge variant="blue" className="mt-2">{specialist.especialidad}</Badge>}

                  <div className="flex items-center gap-2 mt-3">
                    <StarRating rating={specialist.rating_global} />
                    <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                      {specialist.total_opiniones} opiniones en Doctoralia
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5 mt-2" style={{ color: 'var(--text-muted)' }}>
                    <RiMapPinLine className="shrink-0" />
                    <span className="text-sm">{specialist.ciudad}</span>
                    {consultorio && <span className="text-sm">— {consultorio.direccion}</span>}
                  </div>
                </div>
              </div>

              {/* Chips de tipo de paciente */}
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
                  <span>Cédula profesional: {specialist.cedula}</span>
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

            {/* Score donut */}
            <div className="flex flex-col items-center justify-center sm:border-l sm:border-white/10 sm:pl-8">
              <ScoreDonut score={specialist.analisis?.puntuacion_recomendacion} size={120} strokeWidth={6} />
              <p className="text-xs mt-3 text-center font-medium" style={{ color: 'var(--text-muted)' }}>
                Score de recomendación
              </p>
              {hasIa && (
                <p className="text-[10px] mt-1 text-center opacity-65" style={{ color: 'var(--text-muted)' }}>
                  Generado por {ia.modelo_usado || 'NLP model'}
                </p>
              )}
            </div>
          </div>
        </section>

        {/* Enlace original de Doctoralia */}
        {profileUrl && (
          <div className="glass-card p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 border border-royalBlue-500/20 bg-royalBlue-550/5 hover:bg-royalBlue-550/10 transition-colors scroll-reveal">
            <div className="space-y-1">
              <h4 className="text-sm font-semibold text-slate-100 flex items-center gap-1.5">
                <RiExternalLinkLine className="text-royalBlue-400 text-base" />
                Perfil original en Doctoralia
              </h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Puedes consultar la disponibilidad, agendar una cita o ver opiniones completas visitando el perfil directo en la plataforma original.
              </p>
            </div>
            <a
              href={profileUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 text-xs font-semibold text-white bg-royalBlue-600 hover:bg-royalBlue-500 active:bg-royalBlue-700 transition-colors px-4 py-2.5 rounded-xl shrink-0 shadow-lg shadow-royalBlue-600/25"
            >
              Visitar Perfil Médico
            </a>
          </div>
        )}

        {/* Sección de Análisis IA */}
        <section className="glass-card p-6 sm:p-8 space-y-6 scroll-reveal">
          <div className="flex items-center justify-between border-b border-white/10 pb-4">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-royalBlue-400"></span>
              Análisis Inteligente Local (IA)
            </h2>
            {hasIa ? (
              <Badge variant={
                ia.confiabilidad_opiniones === 'alta' ? 'emerald' : 
                ia.confiabilidad_opiniones === 'media' ? 'blue' : 'amber'
              }>
                Confiabilidad: {ia.confiabilidad_opiniones?.toUpperCase() || 'MEDIA'}
              </Badge>
            ) : (
              <Badge variant="gray">Sin procesar</Badge>
            )}
          </div>

          {hasIa ? (
            <div className="space-y-6">
              {/* Resumen */}
              <div className="p-4 rounded-xl bg-royalBlue-900/20 border border-royalBlue-500/10 italic text-sm text-slate-200 leading-relaxed">
                "{ia.resumen || 'Sin resumen disponible.'}"
              </div>

              {/* Puntos Fuertes y Débiles */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-3">
                  <h3 className="text-sm font-semibold text-emerald-400 flex items-center gap-1.5">
                    <RiCheckboxCircleLine className="text-lg" /> Puntos fuertes destacados
                  </h3>
                  {ia.puntos_fuertes?.length > 0 ? (
                    <ul className="space-y-2">
                      {ia.puntos_fuertes.map((punto, idx) => (
                        <li key={idx} className="text-xs text-slate-300 pl-2 border-l-2 border-emerald-500/50">
                          {punto}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs italic" style={{ color: 'var(--text-muted)' }}>Ninguno detectado</p>
                  )}
                </div>

                <div className="space-y-3">
                  <h3 className="text-sm font-semibold text-amber-400 flex items-center gap-1.5">
                    <RiCloseCircleLine className="text-lg" /> Puntos débiles detectados
                  </h3>
                  {ia.puntos_debiles?.length > 0 ? (
                    <ul className="space-y-2">
                      {ia.puntos_debiles.map((punto, idx) => (
                        <li key={idx} className="text-xs text-slate-300 pl-2 border-l-2 border-amber-500/50">
                          {punto}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs italic" style={{ color: 'var(--text-muted)' }}>Ninguno detectado</p>
                  )}
                </div>
              </div>

              {/* Justificación */}
              {ia.justificacion_puntuacion && (
                <div className="space-y-2">
                  <h3 className="text-sm font-semibold">Justificación del score</h3>
                  <p className="text-xs leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                    {ia.justificacion_puntuacion}
                  </p>
                </div>
              )}

              {/* Sospecha de Fraude */}
              {localMetrics.sospecha_fraude && (
                <div className="p-4 rounded-xl bg-red-900/30 border border-red-500/30 text-red-200 text-sm space-y-2">
                  <div className="flex items-center gap-2 font-bold text-red-400">
                    <RiAlertFill className="text-xl shrink-0" />
                    <span>ALERTA: Sospecha de anomalías o fraude en opiniones</span>
                  </div>
                  {localMetrics.razones_fraude?.length > 0 && (
                    <ul className="list-disc list-inside space-y-1 text-xs text-red-300">
                      {localMetrics.razones_fraude.map((razon, idx) => (
                        <li key={idx}>{razon}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

              {/* Métricas de opiniones */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold">Métricas de opiniones locales</h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <MetricCard
                    label="Opiniones en BD"
                    value={localMetrics.total_opiniones_bd ?? 0}
                  />
                  <MetricCard
                    label="Verificadas"
                    value={`${((localMetrics.porcentaje_verificadas || 0) * 100).toFixed(0)}%`}
                  />
                  <MetricCard
                    label="Longitud promedio"
                    value={`${Math.round(localMetrics.longitud_promedio_palabras || 0)} palabras`}
                  />
                  <MetricCard
                    label="Textos cortos"
                    value={`${((localMetrics.porcentaje_texto_corto || 0) * 100).toFixed(0)}%`}
                  />
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-6 text-sm" style={{ color: 'var(--text-muted)' }}>
              El especialista no cuenta con análisis de IA generado todavía.
            </div>
          )}
        </section>

        {/* Experiencia */}
        <section className="glass-card p-6 scroll-reveal">
          <h2 className="text-lg font-semibold mb-4 border-b border-white/10 pb-2">Experiencia y trayectoria</h2>
          {specialist.experiencia?.length > 0 ? (
            <div className="space-y-3">
              {specialist.experiencia.map((text, i) => (
                <p key={i} className="text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                  {text}
                </p>
              ))}
            </div>
          ) : (
            <p className="text-sm italic" style={{ color: 'var(--text-muted)' }}>
              Sin trayectoria cargada en el perfil.
            </p>
          )}
        </section>

        {/* Servicios y precios */}
        <section className="glass-card p-6 scroll-reveal">
          <h2 className="text-lg font-semibold mb-4 border-b border-white/10 pb-2">Servicios y precios</h2>
          {specialist.servicios?.length > 0 ? (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {visibleServices.map((serv, i) => (
                  <div key={i} className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/5 transition-all">
                    <span className="text-sm font-medium">{serv.nombre}</span>
                    <span className="text-sm font-semibold text-royalBlue-300">{serv.precio_texto}</span>
                  </div>
                ))}
              </div>
              {specialist.servicios.length > 6 && !showAllServices && (
                <Button
                  variant="ghost"
                  onClick={() => setShowAllServices(true)}
                  className="mt-3 text-xs"
                  icon={<RiArrowDownSLine />}
                >
                  Ver todos ({specialist.servicios.length})
                </Button>
              )}
            </>
          ) : (
            <p className="text-sm italic" style={{ color: 'var(--text-muted)' }}>Sin servicios registrados.</p>
          )}
        </section>

        {/* Consultorio */}
        {consultorio && (
          <section className="glass-card p-6 scroll-reveal">
            <h2 className="text-lg font-semibold mb-4 border-b border-white/10 pb-2">Ubicación y consultorio</h2>
            {consultorio.clinica && (
              <p className="text-sm font-semibold mb-1 text-slate-100">{consultorio.clinica}</p>
            )}
            <p className="text-sm mb-4 leading-relaxed" style={{ color: 'var(--text-muted)' }}>
              {consultorio.direccion}
            </p>
            <Button
              variant="outline"
              icon={<RiExternalLinkLine />}
              onClick={() => openMap(consultorio.direccion)}
              className="text-xs"
            >
              Ver en Google Maps
            </Button>
          </section>
        )}

        {/* Opiniones de Pacientes */}
        <section className="glass-card p-6 sm:p-8 space-y-6 scroll-reveal">
          <h2 className="text-lg font-semibold flex items-center gap-2 border-b border-white/10 pb-4">
            <RiMessage2Line /> Opiniones de pacientes ({opinionsTotal})
          </h2>

          {opinionsLoading ? (
            <div className="space-y-4">
              {Array.from({ length: 2 }).map((_, idx) => (
                <div key={idx} className="p-4 rounded-xl bg-white/5 space-y-2 animate-pulse">
                  <div className="h-4 bg-white/10 rounded w-1/4"></div>
                  <div className="h-3 bg-white/10 rounded w-full"></div>
                  <div className="h-3 bg-white/10 rounded w-2/3"></div>
                </div>
              ))}
            </div>
          ) : opinions.length > 0 ? (
            <div className="space-y-4">
              {opinions.map((opinion) => (
                <div key={opinion._id} className="p-4 rounded-xl bg-white/5 border border-white/5 hover:border-white/10 transition-colors space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-royalBlue-600/30 flex items-center justify-center text-royalBlue-400">
                        <RiUser3Line />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-slate-200">
                          {opinion.nombre_usuario || 'Paciente anónimo'}
                        </p>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <StarRating rating={opinion.rating} />
                          <span className="text-[10px] text-slate-400">({opinion.rating}/5)</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-2 text-xs" style={{ color: 'var(--text-muted)' }}>
                      {opinion.es_verificada && (
                        <span className="text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded-full font-medium flex items-center gap-1">
                          <RiShieldCheckLine /> Verificada
                        </span>
                      )}
                      <span className="flex items-center gap-1">
                        <RiCalendarLine /> {opinion.fecha_publicacion ? new Date(opinion.fecha_publicacion).toLocaleDateString('es-MX', { year: 'numeric', month: 'short', day: 'numeric' }) : 'Reciente'}
                      </span>
                    </div>
                  </div>

                  {opinion.servicio_consultado && (
                    <p className="text-xs text-royalBlue-300 font-medium">
                      Servicio: {opinion.servicio_consultado}
                    </p>
                  )}

                  <p className="text-sm leading-relaxed text-slate-300 font-light italic">
                    "{opinion.comentario || opinion.opinion || 'Sin comentarios adicionales.'}"
                  </p>
                </div>
              ))}

              {/* Controles de paginación */}
              {opinionsPages > 1 && (
                <div className="flex items-center justify-between pt-4 border-t border-white/10">
                  <Button
                    variant="outline"
                    className="text-xs px-3 py-1.5"
                    disabled={opinionsPage === 1}
                    onClick={() => setOpinionsPage(prev => Math.max(prev - 1, 1))}
                  >
                    Anterior
                  </Button>
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    Página {opinionsPage} de {opinionsPages}
                  </span>
                  <Button
                    variant="outline"
                    className="text-xs px-3 py-1.5"
                    disabled={opinionsPage === opinionsPages}
                    onClick={() => setOpinionsPage(prev => Math.min(prev + 1, opinionsPages))}
                  >
                    Siguiente
                  </Button>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm italic text-center py-4" style={{ color: 'var(--text-muted)' }}>
              No se encontraron opiniones registradas en la base de datos local.
            </p>
          )}
        </section>
      </div>
    </PageWrapper>
  );
}

/**
 * Tarjeta pequeña para métricas de opiniones.
 */
function MetricCard({ label, value }) {
  return (
    <div className="p-3 rounded-xl bg-white/5 border border-white/5 flex flex-col justify-between">
      <span className="text-[10px] uppercase font-bold tracking-wider opacity-60" style={{ color: 'var(--text-muted)' }}>
        {label}
      </span>
      <span className="text-sm font-semibold mt-1 text-slate-100">
        {value}
      </span>
    </div>
  );
}
