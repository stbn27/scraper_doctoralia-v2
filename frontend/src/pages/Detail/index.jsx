import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import {
  RiArrowLeftLine,
  RiMapPinLine,
  RiMapPin2Line,
  RiShieldCheckLine,
  RiShieldLine,
  RiHeartLine,
  RiHeartFill,
  RiExternalLinkLine,
  RiArrowDownSLine,
  RiArrowUpSLine,
  RiAlertFill,
  RiAlertLine,
  RiCheckboxCircleLine,
  RiCloseCircleLine,
  RiStarFill,
  RiUserLine,
  RiHospitalLine,
  RiStethoscopeLine,
  RiSparkling2Line
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
  const [showAllExp, setShowAllExp] = useState(false);

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

  const handleBack = () => {
    if (window.history.state && window.history.state.idx > 0) {
      navigate(-1);
    } else {
      navigate('/busqueda');
    }
  };

  return (
    <PageWrapper name="detail">
      <BubbleBackground />
      <Navbar />

      <div className="relative z-10 pt-20 pb-8 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto space-y-6">
        {/* Botón volver */}
        <button
          onClick={handleBack}
          className="flex items-center gap-2 text-sm hover:text-royalBlue-400 transition-colors"
          style={{ color: 'var(--text-muted)' }}
        >
          <RiArrowLeftLine /> Volver a la búsqueda
        </button>

        {/* Hero Section — editorial */}
        <section className="glass-card overflow-hidden scroll-reveal">
          {/* Franja superior de color */}
          <div className="h-1.5 w-full bg-gradient-to-r from-royalBlue-500/60 via-royalBlue-400/40 to-transparent" />

          <div className="p-6 sm:p-8">
            {/* Cabecera: foto + datos + score inline */}
            <div className="flex flex-col sm:flex-row gap-5 sm:gap-8 items-start">

              {/* Foto */}
              <div className="shrink-0">
                <Avatar
                  name={specialist.nombre}
                  id={specialist._id}
                  src={specialist.foto_perfil_url}
                  size={88}
                  className="text-2xl ring-2 ring-royalBlue-500/20"
                />
              </div>

              {/* Info principal */}
              <div className="flex-1 min-w-0 space-y-2">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h1 className="text-2xl sm:text-3xl font-bold leading-snug tracking-tight">
                      {specialist.nombre}
                    </h1>
                    {specialist.especialidad && (
                      <p className="text-sm mt-0.5 font-medium text-royalBlue-400 flex items-center gap-1.5">
                        <RiStethoscopeLine className="text-base" />
                        {specialist.especialidad}
                      </p>
                    )}
                  </div>

                  {/* Score compacto en línea */}
                  {hasIa && specialist.analisis?.puntuacion_recomendacion != null && (
                    <div className="flex flex-col items-center gap-0.5 shrink-0">
                      <div className="flex items-baseline gap-1">
                        <span className="text-3xl font-extrabold text-royalBlue-400 leading-none">
                          {Math.round(specialist.analisis.puntuacion_recomendacion)}
                        </span>
                        <span className="text-sm font-medium" style={{ color: 'var(--text-muted)' }}>/10</span>
                      </div>
                      <span className="text-[10px] uppercase tracking-widest font-semibold opacity-60" style={{ color: 'var(--text-muted)' }}>
                        Score IA
                      </span>
                    </div>
                  )}
                </div>

                {/* Rating + ubicación */}
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
                  <div className="flex items-center gap-1.5">
                    <StarRating rating={specialist.rating_global} />
                    <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                      {specialist.total_opiniones} opiniones
                    </span>
                  </div>
                  <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--text-muted)' }}>
                    <RiMapPin2Line className="shrink-0" />
                    {specialist.ciudad}
                  </span>
                  {consultorio?.precio_minimo && (
                    <span className="text-xs text-royalBlue-400 font-medium">
                      Desde ${consultorio.precio_minimo.toLocaleString()}
                    </span>
                  )}
                </div>

                {/* Metadatos en fila */}
                <div className="flex flex-wrap gap-2 pt-1">
                  {specialist.pacientes?.atiende_ninos && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                      <RiUserLine className="text-xs" /> Niños
                    </span>
                  )}
                  {specialist.pacientes?.atiende_adultos && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                      <RiUserLine className="text-xs" /> Adultos
                    </span>
                  )}
                  {specialist.pacientes?.atiende_adolescentes && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                      <RiUserLine className="text-xs" /> Adolescentes
                    </span>
                  )}
                  {specialist.cedula && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-royalBlue-500/10 text-royalBlue-500 dark:text-royalBlue-300 border border-royalBlue-500/20">
                      <RiShieldCheckLine className="text-xs" /> Cédula {specialist.cedula}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Separador + acción favorito */}
            <div className="flex items-center justify-between mt-5 pt-4 border-t border-white/5">
              {profileUrl ? (
                <a
                  href={profileUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs flex items-center gap-1.5 hover:text-royalBlue-400 bg-white/4 border border-royalBlue-500/10 hover:bg-royalBlue-500/15 rounded-lg px-4 py-2 transition-colors"
                  style={{ color: 'var(--text-muted)' }}
                >
                  <RiExternalLinkLine />
                  Ver perfil en Doctoralia
                </a>
              ) : <span />}

              <button
                onClick={handleFavorite}
                className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg transition-all ${fav
                    ? 'text-red-500 bg-red-500/10 hover:bg-red-500/15'
                    : 'hover:bg-white/5'
                  }`}
                style={!fav ? { color: 'var(--text-muted)' } : {}}
              >
                {fav ? <RiHeartFill className="text-sm" /> : <RiHeartLine className="text-sm" />}
                {fav ? 'En favoritos' : 'Guardar'}
              </button>
            </div>
          </div>
        </section>

        {/* Análisis IA */}
        <section className="glass-card p-6 sm:p-8 space-y-5 scroll-reveal">
          {/* Encabezado */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <RiSparkling2Line className="text-royalBlue-400 text-lg shrink-0" />
              <h2 className="text-base font-semibold">Resumen de recomendación</h2>
            </div>
            {hasIa ? (
              <span className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full border ${ia.confiabilidad_opiniones === 'alta'
                  ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20'
                  : ia.confiabilidad_opiniones === 'baja' || ia.confiabilidad_opiniones === 'sospechosa'
                    ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20'
                    : 'bg-royalBlue-500/10 text-royalBlue-600 dark:text-royalBlue-300 border-royalBlue-500/20'
                }`}>
                Confiabilidad {ia.confiabilidad_opiniones || 'media'}
              </span>
            ) : (
              <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full border bg-white/5 border-white/10" style={{ color: 'var(--text-muted)' }}>
                Sin análisis
              </span>
            )}
          </div>

          {hasIa ? (
            <div className="space-y-5">
              {/* Resumen en párrafo, no en cita gigante */}
              <p className="text-sm leading-relaxed" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-primary)' }}>
                {ia.resumen || 'Sin resumen disponible.'}
              </p>

              {/* Puntos fuertes y débiles — tarjetas pequeñas */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <p className="text-[11px] uppercase tracking-widest font-bold mb-2 text-emerald-600 dark:text-emerald-400">
                    Puntos fuertes
                  </p>
                  {ia.puntos_fuertes?.length > 0 ? (
                    <ul className="space-y-1.5">
                      {ia.puntos_fuertes.map((p, i) => (
                        <li key={i} className="flex items-start gap-2 text-xs leading-relaxed" style={{ color: 'var(--text-primary)' }}>
                          <RiCheckboxCircleLine className="text-emerald-500 shrink-0 mt-0.5 text-sm" />
                          {p}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs italic" style={{ color: 'var(--text-muted)' }}>Ninguno detectado</p>
                  )}
                </div>
                <div>
                  <p className="text-[11px] uppercase tracking-widest font-bold mb-2 text-amber-600 dark:text-amber-400">
                    Puntos a considerar
                  </p>
                  {ia.puntos_debiles?.length > 0 ? (
                    <ul className="space-y-1.5">
                      {ia.puntos_debiles.map((p, i) => (
                        <li key={i} className="flex items-start gap-2 text-xs leading-relaxed" style={{ color: 'var(--text-primary)' }}>
                          <RiCloseCircleLine className="text-amber-500 shrink-0 mt-0.5 text-sm" />
                          {p}
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
                <div className="pt-1">
                  <p className="text-[11px] uppercase tracking-widest font-bold mb-1.5" style={{ color: 'var(--text-muted)' }}>
                    Justificación del score
                  </p>
                  <p className="text-xs leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                    {ia.justificacion_puntuacion}
                  </p>
                </div>
              )}

              {/* Alerta de fraude — sutil */}
              {localMetrics.sospecha_fraude && (
                <div className="flex gap-3 p-3 rounded-lg bg-amber-50/60 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-700/30">
                  <RiAlertLine className="text-amber-500 shrink-0 mt-0.5 text-base" />
                  <div>
                    <p className="text-xs font-semibold text-amber-700 dark:text-amber-400 mb-1">
                      Posibles anomalías detectadas en opiniones
                    </p>
                    {localMetrics.razones_fraude?.length > 0 && (
                      <ul className="space-y-0.5">
                        {localMetrics.razones_fraude.map((r, i) => (
                          <li key={i} className="text-xs text-amber-700 dark:text-amber-300">{r}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              )}

              {/* Métricas — fila limpia */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1">
                <MetricCard label="Opiniones" value={localMetrics.total_opiniones_bd ?? 0} />
                <MetricCard label="Verificadas" value={`${(localMetrics.porcentaje_verificadas || 0).toFixed(1).replace('.0', '')}%`} />
                <MetricCard label="Long. promedio" value={`${Math.round(localMetrics.longitud_promedio_palabras || 0)} pal.`} />
                <MetricCard label="Textos cortos" value={`${(localMetrics.porcentaje_texto_corto || 0).toFixed(1).replace('.0', '')}%`} />
              </div>
            </div>
          ) : (
            <p className="text-sm italic" style={{ color: 'var(--text-muted)' }}>
              Este especialista no cuenta con análisis de IA generado todavía.
            </p>
          )}
        </section>

        {/* Experiencia — con "Leer más" */}
        {specialist.experiencia?.length > 0 && (
          <section className="scroll-reveal px-1">
            <h2 className="text-sm font-semibold uppercase tracking-widest mb-3" style={{ color: 'var(--text-muted)' }}>
              Trayectoria profesional
            </h2>
            <div className="space-y-2">
              {(showAllExp ? specialist.experiencia : specialist.experiencia.slice(0, 2)).map((text, i) => (
                <p key={i} className="text-sm leading-relaxed" style={{ color: 'var(--text-primary)' }}>
                  {text}
                </p>
              ))}
            </div>
            {specialist.experiencia.length > 2 && (
              <button
                onClick={() => setShowAllExp(v => !v)}
                className="mt-3 text-xs flex items-center gap-1 hover:text-royalBlue-400 transition-colors"
                style={{ color: 'var(--text-muted)' }}
              >
                {showAllExp ? <><RiArrowUpSLine /> Mostrar menos</> : <><RiArrowDownSLine /> Leer más</>}
              </button>
            )}
          </section>
        )}

        {/* Servicios — lista limpia */}
        {specialist.servicios?.length > 0 && (
          <section className="glass-card p-6 scroll-reveal">
            <h2 className="text-sm font-semibold uppercase tracking-widest mb-4" style={{ color: 'var(--text-muted)' }}>
              Servicios y precios
            </h2>
            <div className="divide-y divide-white/5">
              {visibleServices.map((serv, i) => (
                <div key={i} className="flex items-center justify-between py-2.5 gap-4">
                  <span className="text-sm" style={{ color: 'var(--text-primary)' }}>{serv.nombre}</span>
                  <span className={`text-xs font-semibold shrink-0 ${serv.precio_texto ? 'text-royalBlue-400' : ''}`} style={!serv.precio_texto ? { color: 'var(--text-muted)' } : {}}>
                    {serv.precio_texto || 'Precio no publicado'}
                  </span>
                </div>
              ))}
            </div>
            {specialist.servicios.length > 6 && (
              <button
                onClick={() => setShowAllServices(v => !v)}
                className="mt-3 text-xs flex items-center gap-1 hover:text-royalBlue-400 transition-colors"
                style={{ color: 'var(--text-muted)' }}
              >
                {showAllServices
                  ? <><RiArrowUpSLine /> Ver menos</>
                  : <><RiArrowDownSLine /> Ver todos ({specialist.servicios.length})</>
                }
              </button>
            )}
          </section>
        )}

        {/* Ubicación — práctica, sin card gigante */}
        {consultorio && (
          <section className="scroll-reveal px-1">
            <h2 className="text-sm font-semibold uppercase tracking-widest mb-3" style={{ color: 'var(--text-muted)' }}>
              Ubicación
            </h2>
            <div className="flex items-start gap-3">
              <div className="mt-0.5 p-1.5 rounded-lg bg-royalBlue-500/10 shrink-0">
                <RiHospitalLine className="text-royalBlue-700 dark:text-royalBlue-400 text-base" />
              </div>
              <div>
                {consultorio.clinica && (
                  <p className="text-sm font-semibold mb-0.5" style={{ color: 'var(--text-primary)' }}>{consultorio.clinica}</p>
                )}
                <p className="text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>{consultorio.direccion}</p>
                <button
                  onClick={() => openMap(consultorio.direccion)}
                  className="mt-2 text-xs flex items-center gap-1.5 text-royal-800 dark:text-royalBlue-500 hover:text-royalBlue-900 dark:hover:text-royalBlue-400 transition-colors"
                >
                  <RiExternalLinkLine /> Ver en Google Maps
                </button>
              </div>
            </div>
          </section>
        )}

      </div>
    </PageWrapper>
  );
}

/**
 * Tarjeta pequeña para métricas de opiniones.
 * @param {{ label: string, value: string|number }} props
 */
function MetricCard({ label, value }) {
  return (
    <div className="p-3 rounded-lg bg-white/4 border border-white/5 flex flex-col gap-1">
      <span className="text-[10px] uppercase tracking-wider font-semibold" style={{ color: 'var(--text-muted)' }}>
        {label}
      </span>
      <span className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
        {value}
      </span>
    </div>
  );
}
