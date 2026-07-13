import React, { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  RiMapPinLine as IconMap,
  RiStarFill as IconStar,
  RiLink as IconLink,
  RiDeleteBinLine as IconDelete,
  RiRefreshLine as IconRefresh,
  RiBrainLine as IconBrain,
  RiArrowLeftLine as IconBack,
  RiUserLine as IconUser,
  RiCheckDoubleLine as IconCheck,
  RiErrorWarningLine as IconWarning,
  RiCalendarEventLine as IconCalendar,
  RiMoneyDollarCircleLine as IconMoney,
  RiInformationLine as IconInfo,
  RiArrowDownSLine as IconArrowDown,
  RiArrowUpSLine as IconArrowUp,
} from "react-icons/ri";

import { PageWrapper } from "@/components/layout/PageWrapper";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { BubbleBackground } from "@/components/layout/BubbleBackground";
import { ConfirmModal } from "@/components/ui/ConfirmModal";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Avatar } from "@/components/ui/Avatar";
import { SkeletonCard } from "@/components/ui/SkeletonCard";

import {
  getDetalleEspecialistaAdmin,
  deleteEspecialistaAdmin,
  reescrapearEspecialistaAdmin,
  analizarEspecialistaAdmin,
} from "@/services/admin.api";

import { getOpiniones } from "@/services/opiniones.api";
import { useToast } from "@/hooks/useToast";

/* --- Helpers --- */
const fmt = (n) => (n ?? 0).toLocaleString("es-MX");
const fmtFecha = (iso) => {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return "—";
  return d.toLocaleString("es-MX", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};
const normalizeName = (name) =>
  name?.replace(/^(Dra\.|Dr\.|Dra|Dr)\s+/i, "") || "—";

/* --- Components --- */

function StatBox({ label, value, sub, warning }) {
  return (
    <div className="glass-card p-4 flex flex-col gap-1 border border-[var(--glass-border)]">
      <div className="text-[11px] text-[var(--text-muted)] uppercase tracking-wider">
        {label}
      </div>
      <div
        className={`text-2xl font-bold ${warning ? "text-amber-500" : "text-[var(--text-primary)]"}`}
      >
        {value}
      </div>
      {sub && <div className="text-[11px] text-[var(--text-muted)]">{sub}</div>}
    </div>
  );
}

function Section({ title, children, className = "", style = {} }) {
  return (
    <section
      className={`glass-card border border-[var(--glass-border)] p-6 mb-6 ${className}`}
      style={style}
    >
      <h2 className="text-base font-semibold text-[var(--text-primary)] mb-4 flex items-center gap-2">
        {title}
      </h2>
      {children}
    </section>
  );
}

function EstatusBadge({ status }) {
  const map = {
    completado: { color: "#10b981", text: "Completado" },
    sin_opiniones: { color: "#6b7280", text: "Sin opiniones" },
    error: { color: "#ef4444", text: "Error" },
    parcial: { color: "#f59e0b", text: "Parcial" },
    procesando: { color: "#3b82f6", text: "Procesando" },
    pendiente: { color: "#8b5cf6", text: "Pendiente" },
  };
  const s = map[status] || { color: "#94a3b8", text: status || "Desconocido" };
  return <Badge texto={s.text} color={s.color} />;
}

export default function AdminDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { addToast } = useToast();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [opinions, setOpinions] = useState([]);
  const [opPage, setOpPage] = useState(1);
  const [opHasMore, setOpHasMore] = useState(true);
  const [opLoading, setOpLoading] = useState(false);
  const [opError, setOpError] = useState(null);

  const [deleteModal, setDeleteModal] = useState(false);
  const [analysisModal, setAnalysisModal] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const [numOpinions, setNumOpinions] = useState(30);
  const [expandedDiseases, setExpandedDiseases] = useState(false);
  const diseasesContainerRef = useRef(null);
  const [showDiseasesButton, setShowDiseasesButton] = useState(false);

  const [expandedServices, setExpandedServices] = useState(false);
  const servicesContainerRef = useRef(null);
  const [servicesHeightLimit, setServicesHeightLimit] = useState(450);

  const observerRef = useRef();

  useEffect(() => {
    const checkOverflow = () => {
      if (diseasesContainerRef.current) {
        const hasOverflow = diseasesContainerRef.current.scrollHeight > 82;
        setShowDiseasesButton(hasOverflow);
      }
    };

    const timer = setTimeout(checkOverflow, 100);
    window.addEventListener("resize", checkOverflow);
    return () => {
      clearTimeout(timer);
      window.removeEventListener("resize", checkOverflow);
    };
  }, [data]);

  useEffect(() => {
    if (servicesContainerRef.current && data?.doctor?.servicios_y_precios?.length > 10) {
      const children = servicesContainerRef.current.children;
      if (children && children.length >= 10) {
        const tenthChild = children[9];
        const rect = tenthChild.getBoundingClientRect();
        const containerRect = servicesContainerRef.current.getBoundingClientRect();
        const heightOf10 = rect.bottom - containerRect.top;
        setServicesHeightLimit(heightOf10);
      }
    }
  }, [data]);

  const cargarData = useCallback(async () => {
    try {
      const res = await getDetalleEspecialistaAdmin(id);
      setData(res);
    } catch (e) {
      setError(e.message || "Error al cargar perfil");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    cargarData();
  }, [cargarData]);

  // Infinite loading opinions
  const loadOpinions = useCallback(
    async (page, reset = false) => {
      if (!data?.doctoralia_id && !data?._id) return;
      setOpLoading(true);
      setOpError(null);
      try {
        const refId = data._id || data.doctoralia_id;
        const res = await getOpiniones(refId, { page, limit: 10 });

        const newOpinions = res?.results ?? [];
        const totalPages = res?.pages ?? 0;

        setOpinions((prev) =>
          reset ? newOpinions : [...prev, ...newOpinions],
        );
        setOpHasMore(page < totalPages);
        setOpPage(page);
      } catch (e) {
        setOpError("Error al cargar opiniones");
        addToast({ type: "error", message: "Error al cargar opiniones" });
      } finally {
        setOpLoading(false);
      }
    },
    [data, addToast],
  );

  useEffect(() => {
    if (data) loadOpinions(1, true);
  }, [data]); // eslint-disable-line

  const lastOpinionElementRef = useCallback(
    (node) => {
      if (opLoading) return;
      if (observerRef.current) observerRef.current.disconnect();
      observerRef.current = new IntersectionObserver(
        (entries) => {
          if (entries[0].isIntersecting && opHasMore) {
            loadOpinions(opPage + 1);
          }
        },
        { rootMargin: "200px" },
      );
      if (node) observerRef.current.observe(node);
    },
    [opLoading, opHasMore, opPage, loadOpinions],
  );

  const handleDelete = async () => {
    try {
      setActionLoading(true);
      await deleteEspecialistaAdmin(id);
      addToast({
        type: "success",
        message: "Especialista eliminado con éxito",
      });
      setDeleteModal(false);
      navigate("/admin");
    } catch (e) {
      addToast({ type: "error", message: e.message || "Error al eliminar" });
    } finally {
      setActionLoading(false);
    }
  };

  const handleRescrape = async () => {
    if (!data?.scraping?.fuente) return;
    try {
      setActionLoading(true);
      await reescrapearEspecialistaAdmin(data.scraping.fuente);
      addToast({ type: "success", message: "Re-scraping completado" });
      cargarData();
    } catch (e) {
      addToast({ type: "error", message: e.message || "Error al re-scrapear" });
    } finally {
      setActionLoading(false);
    }
  };

  const handleAnalyze = async () => {
    if (!data?.doctoralia_id) return;
    try {
      setActionLoading(true);
      const res = await analizarEspecialistaAdmin(data.doctoralia_id, numOpinions);
      addToast({
        type: "success",
        message: `Análisis ejecutado con éxito (modelo: ${res.modelo_usado || "desconocido"})`,
      });
      setAnalysisModal(false);
      cargarData();
    } catch (e) {
      addToast({
        type: "error",
        message: e.message || "Error al ejecutar análisis",
      });
    } finally {
      setActionLoading(false);
    }
  };

  if (loading)
    return (
      <PageWrapper>
        <Navbar />
        <div className="pt-24 px-8">
          <SkeletonCard />
        </div>
      </PageWrapper>
    );
  if (error || !data)
    return (
      <PageWrapper>
        <Navbar />
        <div className="pt-24 px-8 text-red-500">{error}</div>
      </PageWrapper>
    );

  const doc = data.doctor || {};
  const ana = data.analisis;

  // Comparación de opiniones
  const diffOps = data.total_opiniones_bd - data.total_opiniones_perfil;
  let syncStatus = "Sincronizado";
  let syncColor = "#10b981";
  if (diffOps < 0) {
    syncStatus = "Faltan opiniones en BD";
    syncColor = "#ef4444";
  } else if (diffOps > 0) {
    syncStatus = "BD excede total del perfil";
    syncColor = "#f59e0b";
  }

  return (
    <PageWrapper name="admin-detail">
      <BubbleBackground />
      <Navbar />

      <div
        className="relative z-10 pt-24 pb-20 px-4 sm:px-6 lg:px-8 max-w-5xl mx-auto"
        style={{ color: "var(--text-primary)" }}
      >
        {/* Top actions */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 16,
            marginBottom: 24,
          }}
        >
          <button
            onClick={() => navigate("/admin")}
            className="hover:opacity-80"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              color: "var(--text-muted)",
              background: "transparent",
              border: "none",
              cursor: "pointer",
              fontSize: 13,
              fontWeight: 500,
            }}
          >
            <IconBack /> Volver a la lista
          </button>

          <div style={{ marginLeft: "auto", display: "flex", gap: 10 }}>
            {data.scraping?.fuente && (
              <Button
                variant="secondary"
                onClick={handleRescrape}
                disabled={actionLoading}
                className="text-xs px-3 py-1.5 h-auto"
              >
                <IconRefresh className="mr-1.5" /> Re-scrapear
              </Button>
            )}
            <Button
              variant="primary"
              onClick={() => setAnalysisModal(true)}
              disabled={actionLoading}
              className="text-xs px-3 py-1.5 h-auto bg-primary-600 hover:bg-primary-500"
            >
              <IconBrain className="mr-1.5" /> Generar Análisis
            </Button>
            <Button
              variant="danger"
              onClick={() => setDeleteModal(true)}
              disabled={actionLoading}
              className="text-xs px-3 py-1.5 h-auto"
            >
              <IconDelete className="mr-1.5" /> Eliminar
            </Button>
          </div>
        </div>

        {/* Header Profile */}
        <div
          className="glass-card"
          style={{
            border: "1px solid var(--glass-border)",
            padding: 32,
            marginBottom: 24,
            display: "flex",
            gap: 24,
            alignItems: "flex-start",
            flexWrap: "wrap",
          }}
        >
          {doc.foto_perfil ? (
            <img
              src={doc.foto_perfil}
              alt=""
              style={{
                width: 80,
                height: 80,
                borderRadius: "50%",
                objectFit: "cover",
              }}
            />
          ) : (
            <div
              style={{
                width: 80,
                height: 80,
                borderRadius: "50%",
                background: "var(--color-primary-100)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <IconUser
                size={32}
                style={{ color: "var(--color-primary-500)" }}
              />
            </div>
          )}

          <div style={{ flex: 1, minWidth: 250 }}>
            <h1
              className="font-secondary"
              style={{
                fontSize: 24,
                fontWeight: 700,
                color: "var(--text-primary)",
                margin: "0 0 8px 0",
              }}
            >
              {normalizeName(doc.nombre)}
            </h1>
            <div
              style={{
                display: "flex",
                gap: 8,
                flexWrap: "wrap",
                marginBottom: 16,
              }}
            >
              {(doc.especialidades || []).map((e, i) => (
                <Badge key={i} texto={e} color="var(--text-muted)" />
              ))}
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                gap: 16,
              }}
            >
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                <strong style={{ color: "var(--text-primary)" }}>
                  Estado:
                </strong>{" "}
                {(doc.estado || []).join(", ") || "—"}
              </div>
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                <strong style={{ color: "var(--text-primary)" }}>
                  Última actualización:
                </strong>{" "}
                {fmtFecha(
                  data.scraping?.ultima_actualizacion ||
                  data.scraping?.ultimo_scraping
                )}
              </div>
              <div
                style={{
                  fontSize: 12,
                  color: "var(--text-muted)",
                  display: "flex",
                  alignItems: "center",
                  gap: 4,
                }}
              >
                <IconStar style={{ color: "#f59e0b" }} />
                <strong style={{ color: "var(--text-primary)" }}>
                  Rating Global:
                </strong>{" "}
                {doc.rating_global || "—"}
              </div>
            </div>
          </div>

          {doc.url_perfil && (
            <a
              href={doc.url_perfil}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:opacity-80"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                fontSize: 12,
                color: "var(--color-primary-600)",
                background: "var(--color-primary-100)",
                padding: "8px 12px",
                borderRadius: 8,
                textDecoration: "none",
                fontWeight: 600,
              }}
            >
              <IconLink /> Perfil Oficial Doctoralia
            </a>
          )}
        </div>

        {/* Comparación de Opiniones */}
        <Section
          title={
            <>
              <IconCheck /> Comparación de Opiniones
            </>
          }
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: 16,
            }}
          >
            <StatBox
              label="Opiniones Reportadas (Perfil)"
              value={fmt(data.total_opiniones_perfil)}
            />
            <StatBox
              label="Opiniones Almacenadas (BD)"
              value={fmt(data.total_opiniones_bd)}
            />
            <StatBox
              label="Diferencia"
              value={fmt(Math.abs(diffOps))}
              sub={`Estado: ${syncStatus}`}
              warning={diffOps !== 0}
            />
          </div>
        </Section>

        {/* Análisis IA */}
        <Section
          title={
            <>
              <IconBrain /> Análisis del Especialista
            </>
          }
        >
          {!ana ? (
            <div
              style={{
                textAlign: "center",
                padding: "32px 0",
                color: "var(--text-muted)",
              }}
            >
              <IconBrain
                size={32}
                style={{ opacity: 0.5, margin: "0 auto 12px" }}
              />
              <p style={{ fontSize: 14 }}>
                No hay análisis IA generado para este perfil.
              </p>
              <Button
                variant="secondary"
                onClick={() => setAnalysisModal(true)}
                className="mt-4 text-xs"
              >
                Generar ahora
              </Button>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                <EstatusBadge status={ana.estatus} />
                <Badge
                  texto={`Modelo: ${ana.modelo_usado || "—"}`}
                  color="#a78bfa"
                />
                <Badge
                  texto={`Prompt v${ana.version_prompt || "?"}`}
                  color="var(--text-muted)"
                />
                <span
                  style={{
                    fontSize: 11,
                    color: "var(--text-muted)",
                    display: "flex",
                    alignItems: "center",
                  }}
                >
                  {fmtFecha(ana.fecha_analisis)}
                </span>
              </div>

              {ana.error_detalle ? (
                <div
                  style={{
                    padding: 16,
                    background: "rgba(239,68,68,0.1)",
                    border: "1px solid rgba(239,68,68,0.2)",
                    borderRadius: 12,
                    color: "#fca5a5",
                    fontSize: 13,
                  }}
                >
                  <strong style={{ display: "block", marginBottom: 4 }}>
                    Error durante el análisis:
                  </strong>
                  {ana.error_detalle}
                </div>
              ) : (
                <>
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr 2fr",
                      gap: 20,
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: 16,
                      }}
                    >
                      <div
                        style={{
                          fontSize: 48,
                          fontWeight: 800,
                          color: "var(--text-primary)",
                          lineHeight: 1,
                        }}
                      >
                        {ana.puntuacion ?? "—"}
                        <span
                          style={{
                            fontSize: 18,
                            color: "var(--text-muted)",
                            fontWeight: 500,
                          }}
                        >
                          /10
                        </span>
                      </div>
                      <div>
                        <div
                          style={{
                            fontSize: 11,
                            color: "var(--text-muted)",
                            textTransform: "uppercase",
                          }}
                        >
                          Confiabilidad
                        </div>
                        <div
                          style={{
                            fontSize: 14,
                            fontWeight: 600,
                            color: "var(--text-primary)",
                            textTransform: "capitalize",
                          }}
                        >
                          {ana.confiabilidad || "—"}
                        </div>
                      </div>
                      <div>
                        <div
                          style={{
                            fontSize: 11,
                            color: "var(--text-muted)",
                            textTransform: "uppercase",
                          }}
                        >
                          Opiniones analizadas
                        </div>
                        <div
                          style={{
                            fontSize: 14,
                            fontWeight: 600,
                            color: "var(--text-primary)",
                          }}
                        >
                          {ana.opiniones_enviadas_modelo || 0} de{" "}
                          {ana.opiniones_en_bd || data.total_opiniones_bd || 0}
                        </div>
                      </div>
                    </div>

                    <div
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: 16,
                      }}
                    >
                      <div>
                        <h4                        
                          className="font-secondary"
                          style={{
                            fontSize: 13,
                            color: "var(--text-muted)",
                            marginBottom: 6,
                          }}
                        >
                          Resumen
                        </h4>
                        <p                          
                          style={{
                            fontSize: 14,
                            color: "var(--text-primary)",
                            lineHeight: 1.5,
                            margin: 0,
                          }}
                        >
                          {ana.resumen || "Sin resumen disponible."}
                        </p>
                      </div>
                      <div>
                        <h4                          
                          style={{
                            fontSize: 13,
                            color: "var(--text-muted)",
                            marginBottom: 6,
                          }}
                        >
                          Justificación
                        </h4>
                        <p                          
                          style={{
                            fontSize: 13,
                            color: "var(--text-primary)",
                            lineHeight: 1.5,
                            margin: 0,
                          }}
                        >
                          {ana.justificacion || "—"}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr 1fr",
                      gap: 20,
                    }}
                  >
                    <div
                      style={{
                        background: "rgba(16,185,129,0.1)",
                        padding: 16,
                        borderRadius: 12,
                      }}
                    >
                      <h4
                        className="font-secondary"
                        style={{
                          fontSize: 13,
                          color: "#10b981",
                          marginBottom: 10,
                          fontWeight: 600,
                        }}
                      >
                        Puntos Fuertes
                      </h4>
                      <ul
                        style={{
                          margin: 0,
                          paddingLeft: 20,
                          fontSize: 13,
                          color: "var(--text-primary)",
                          display: "flex",
                          flexDirection: "column",
                          gap: 6,
                        }}
                      >
                        {(ana.puntos_fuertes || []).map((p, i) => (
                          <li key={i}>{p}</li>
                        ))}
                        {(!ana.puntos_fuertes ||
                          ana.puntos_fuertes.length === 0) && (
                            <li
                              style={{
                                color: "var(--text-muted)",
                                listStyle: "none",
                                marginLeft: -20,
                              }}
                            >
                              No se detectaron.
                            </li>
                          )}
                      </ul>
                    </div>
                    <div
                      style={{
                        background: "rgba(239,68,68,0.1)",
                        padding: 16,
                        borderRadius: 12,
                      }}
                    >
                      <h4
                        className="font-secondary"
                        style={{
                          fontSize: 13,
                          color: "#ef4444",
                          marginBottom: 10,
                          fontWeight: 600,
                        }}
                      >
                        Puntos Débiles
                      </h4>
                      <ul
                        style={{
                          margin: 0,
                          paddingLeft: 20,
                          fontSize: 13,
                          color: "var(--text-primary)",
                          display: "flex",
                          flexDirection: "column",
                          gap: 6,
                        }}
                      >
                        {(ana.puntos_debiles || []).map((p, i) => (
                          <li key={i}>{p}</li>
                        ))}
                        {(!ana.puntos_debiles ||
                          ana.puntos_debiles.length === 0) && (
                            <li
                              style={{
                                color: "var(--text-muted)",
                                listStyle: "none",
                                marginLeft: -20,
                              }}
                            >
                              No se detectaron.
                            </li>
                          )}
                      </ul>
                    </div>
                  </div>

                  {ana.alertas_preprocesamiento &&
                    Object.keys(ana.alertas_preprocesamiento).length > 0 && (
                      <div
                        style={{
                          background: "rgba(245,158,11,0.05)",
                          border: "1px solid rgba(245,158,11,0.2)",
                          padding: 16,
                          borderRadius: 12,
                        }}
                      >
                        <h4
                          className="font-secondary"
                          style={{
                            fontSize: 13,
                            color: "#f59e0b",
                            marginBottom: 10,
                            fontWeight: 600,
                            display: "flex",
                            alignItems: "center",
                            gap: 6,
                          }}
                        >
                          <IconWarning /> Alertas de Preprocesamiento
                        </h4>
                        <ul
                          style={{
                            margin: 0,
                            paddingLeft: 20,
                            fontSize: 13,
                            color: "#fbbf24",
                            display: "flex",
                            flexDirection: "column",
                            gap: 4,
                          }}
                        >
                          {Object.entries(ana.alertas_preprocesamiento).map(
                            ([k, v]) => (
                              <li key={k}>
                                <strong>{k}:</strong> {v}
                              </li>
                            ),
                          )}
                        </ul>
                      </div>
                    )}

                  {/* Metadatos de Opiniones Analizadas */}
                  <div
                    style={{
                      borderTop: "1px solid var(--glass-border)",
                      paddingTop: 16,
                      marginTop: 8,
                    }}
                  >
                    <h4
                      style={{
                        fontSize: 12,
                        color: "var(--text-muted)",
                        textTransform: "uppercase",
                        marginBottom: 12,
                      }}
                    >
                      Metadatos de Opiniones
                    </h4>
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns:
                          "repeat(auto-fill, minmax(150px, 1fr))",
                        gap: 12,
                      }}
                    >
                      <div style={{ fontSize: 12 }}>
                        <span style={{ color: "var(--text-muted)" }}>
                          Rating prom:
                        </span>{" "}
                        <strong style={{ color: "var(--text-primary)" }}>
                          {ana.rating_promedio_analisis ?? "—"}
                        </strong>
                      </div>
                      <div style={{ fontSize: 12 }}>
                        <span style={{ color: "var(--text-muted)" }}>
                          Recencia prom:
                        </span>{" "}
                        <strong style={{ color: "var(--text-primary)" }}>
                          {ana.recencia_promedio_dias
                            ? `${ana.recencia_promedio_dias} días`
                            : "—"}
                        </strong>
                      </div>
                      <div style={{ fontSize: 12 }}>
                        <span style={{ color: "var(--text-muted)" }}>
                          Sospecha fraude:
                        </span>{" "}
                        <strong
                          style={{
                            color: ana.sospecha_fraude ? "#ef4444" : "#10b981",
                          }}
                        >
                          {ana.sospecha_fraude ? "Sí" : "No"}
                        </strong>
                      </div>
                    </div>
                    {ana.razones_fraude && ana.razones_fraude.length > 0 && (
                      <div
                        style={{ marginTop: 8, fontSize: 12, color: "#ef4444" }}
                      >
                        Motivos de sospecha: {ana.razones_fraude.join(", ")}
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          )}
        </Section>

        {/* Información Profesional */}
        <Section
          title={
            <>
              <IconInfo /> Información Profesional
            </>
          }
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: 24,
            }}
          >
            <div>
              <h4
                style={{
                  fontSize: 12,
                  color: "var(--text-muted)",
                  textTransform: "uppercase",
                  marginBottom: 8,
                }}
              >
                Cédulas Profesionales
              </h4>
              {doc.cedulas && doc.cedulas.length > 0 ? (
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {doc.cedulas.map((c, i) => (
                    <Badge key={i} texto={c} color="#3b82f6" />
                  ))}
                </div>
              ) : (
                <div style={{ fontSize: 13, color: "var(--text-muted)" }}>
                  No disponible
                </div>
              )}
            </div>

            <div>
              <h4
                style={{
                  fontSize: 12,
                  color: "var(--text-muted)",
                  textTransform: "uppercase",
                  marginBottom: 8,
                }}
              >
                Idiomas
              </h4>
              {doc.idiomas && doc.idiomas.length > 0 ? (
                <div style={{ fontSize: 13, color: "var(--text-primary)" }}>
                  {doc.idiomas.join(", ")}
                </div>
              ) : (
                <div style={{ fontSize: 13, color: "var(--text-muted)" }}>
                  No disponible
                </div>
              )}
            </div>

            <div>
              <h4
                style={{
                  fontSize: 12,
                  color: "var(--text-muted)",
                  textTransform: "uppercase",
                  marginBottom: 8,
                }}
              >
                Pacientes que atiende
              </h4>
              {doc.pacientes_que_atiende &&
                Object.values(doc.pacientes_que_atiende).some((v) => v) ? (
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {doc.pacientes_que_atiende.ninos && (
                    <Badge texto="Niños" color="#10b981" />
                  )}
                  {doc.pacientes_que_atiende.adolescentes && (
                    <Badge texto="Adolescentes" color="#10b981" />
                  )}
                  {doc.pacientes_que_atiende.adultos && (
                    <Badge texto="Adultos" color="#10b981" />
                  )}
                </div>
              ) : (
                <div style={{ fontSize: 13, color: "var(--text-muted)" }}>
                  No disponible
                </div>
              )}
            </div>

            <div>
              <h4
                style={{
                  fontSize: 12,
                  color: "var(--text-muted)",
                  textTransform: "uppercase",
                  marginBottom: 8,
                }}
              >
                Formas de Pago
              </h4>
              {doc.formas_de_pago && doc.formas_de_pago.length > 0 ? (
                <div style={{ fontSize: 13, color: "var(--text-primary)" }}>
                  {doc.formas_de_pago.join(", ")}
                </div>
              ) : (
                <div style={{ fontSize: 13, color: "var(--text-muted)" }}>
                  No disponible
                </div>
              )}
            </div>

            <div style={{ gridColumn: "1 / -1" }}>
              <h4
                style={{
                  fontSize: 12,
                  color: "var(--text-muted)",
                  textTransform: "uppercase",
                  marginBottom: 8,
                }}
              >
                Enfermedades Tratadas
              </h4>
              {doc.principales_enfermedades_tratadas &&
                doc.principales_enfermedades_tratadas.length > 0 ? (
                <div className="flex flex-col gap-2">
                  <div
                    ref={diseasesContainerRef}
                    className="flex flex-wrap gap-2 overflow-hidden transition-[max-height] duration-500 ease-in-out"
                    style={{
                      maxHeight: expandedDiseases ? "1000px" : "82px",
                    }}
                  >
                    {doc.principales_enfermedades_tratadas.map((enfermedad, idx) => (
                      <Badge
                        key={idx}
                        variant="gray"
                        className="border-[var(--glass-border)] text-[var(--text-primary)] hover:border-royalBlue-500/50 transition-colors"
                      >
                        {enfermedad}
                      </Badge>
                    ))}
                  </div>
                  {showDiseasesButton && (
                    <button
                      onClick={() => setExpandedDiseases(!expandedDiseases)}
                      className="self-start mt-1 text-xs font-semibold text-royalBlue-400 hover:text-royalBlue-300 transition-colors flex items-center gap-1 cursor-pointer bg-transparent border-none p-0 outline-none"
                    >
                      {expandedDiseases ? (
                        <>
                          Ver menos <IconArrowUp className="text-sm" />
                        </>
                      ) : (
                        <>
                          Ver más <IconArrowDown className="text-sm" />
                        </>
                      )}
                    </button>
                  )}
                </div>
              ) : (
                <div style={{ fontSize: 13, color: "var(--text-muted)" }}>
                  No disponible
                </div>
              )}
            </div>

            {doc.experiencia && (
              <div style={{ gridColumn: "1 / -1" }}>
                <h4
                  style={{
                    fontSize: 12,
                    color: "var(--text-muted)",
                    textTransform: "uppercase",
                    marginBottom: 8,
                  }}
                >
                  Experiencia
                </h4>
                <p
                  style={{
                    fontSize: 13,
                    color: "var(--text-primary)",
                    lineHeight: 1.5,
                    margin: 0,
                    whiteSpace: "pre-line",
                  }}
                >
                  {doc.experiencia}
                </p>
              </div>
            )}
          </div>
        </Section>

        {/* Direcciones */}
        <Section
          title={
            <>
              <IconMap /> Direcciones
            </>
          }
        >
          {doc.direcciones && doc.direcciones.length > 0 ? (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                gap: 16,
              }}
            >
              {doc.direcciones.map((dir, i) => {
                const mapUrl =
                  dir.maps ||
                  (dir.lat && dir.lng
                    ? `https://www.google.com/maps/search/?api=1&query=${dir.lat},${dir.lng}`
                    : null);
                return (
                  <div key={i} className="glass-card" style={{ padding: 16 }}>
                    <div
                      style={{
                        fontSize: 13,
                        fontWeight: 600,
                        color: "var(--text-primary)",
                        marginBottom: 6,
                      }}
                    >
                      {dir.nombre || "Consultorio"}
                    </div>
                    <div
                      style={{
                        fontSize: 12,
                        color: "var(--text-muted)",
                        marginBottom: 12,
                        lineHeight: 1.4,
                      }}
                    >
                      {dir.calle || dir.texto}
                      <br />
                      {dir.ciudad && `${dir.ciudad}, `}
                      {dir.estado} {dir.codigo_postal}
                    </div>
                    {mapUrl && (
                      <a
                        href={mapUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hover:opacity-80"
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 4,
                          fontSize: 11,
                          color: "#10b981",
                          textDecoration: "none",
                        }}
                      >
                        <IconMap /> Ver en Google Maps
                      </a>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div style={{ fontSize: 13, color: "var(--text-muted)" }}>
              No hay direcciones registradas.
            </div>
          )}
        </Section>

        {/* Servicios */}
        <Section
          title={
            <>
              <IconMoney /> Servicios y Precios
            </>
          }
        >
          {doc.servicios_y_precios && doc.servicios_y_precios.length > 0 ? (
            <div className="flex flex-col gap-2">
              <div
                ref={servicesContainerRef}
                className="glass-card transition-[max-height] duration-500 ease-in-out"
                style={{
                  overflow: "hidden",
                  border: "1px solid var(--glass-border)",
                  maxHeight: doc.servicios_y_precios.length > 10
                    ? (expandedServices ? `${servicesContainerRef.current?.scrollHeight || 1000}px` : `${servicesHeightLimit}px`)
                    : "none",
                }}
              >
                {doc.servicios_y_precios.map((s, i) => {
                  const isExtra = i >= 10;
                  return (
                    <div
                      key={i}
                      className="transition-all duration-500 ease-in-out"
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        padding: "12px 16px",
                        borderBottom:
                          i < doc.servicios_y_precios.length - 1
                            ? "1px solid var(--glass-border)"
                            : "none",
                        opacity: isExtra && !expandedServices ? 0 : 1,
                        transform: isExtra && !expandedServices ? "translateY(-10px)" : "translateY(0)",
                        pointerEvents: isExtra && !expandedServices ? "none" : "auto",
                      }}
                    >
                      <div style={{ fontSize: 13, color: "var(--text-primary)" }}>
                        {s.servicio}
                      </div>
                      <div
                        style={{
                          fontSize: 13,
                          fontWeight: 600,
                          color: s.precio
                            ? "var(--text-primary)"
                            : "var(--text-muted)",
                        }}
                      >
                        {s.precio || "Precio no especificado"}
                      </div>
                    </div>
                  );
                })}
              </div>
              {doc.servicios_y_precios.length > 10 && (
                <button
                  onClick={() => setExpandedServices(!expandedServices)}
                  className="self-center mt-2 text-xs font-semibold text-royalBlue-400 hover:text-royalBlue-300 transition-colors flex items-center gap-1 cursor-pointer bg-transparent border-none p-0 outline-none"
                >
                  {expandedServices ? (
                    <>
                      Ver menos <IconArrowUp className="text-sm" />
                    </>
                  ) : (
                    <>
                      Ver más <IconArrowDown className="text-sm" />
                    </>
                  )}
                </button>
              )}
            </div>
          ) : (
            <div style={{ fontSize: 13, color: "var(--text-muted)" }}>
              No hay servicios registrados.
            </div>
          )}
        </Section>

        {/* Opiniones (Infinite scroll) */}
        <section className="relative p-6 mb-6">
          <div
            className="absolute inset-0 pointer-events-none rounded-2xl glass-card"
            style={{
              maskImage:
                "linear-gradient(to bottom, black 70%, transparent 100%)",
              WebkitMaskImage:
                "linear-gradient(to bottom, black 70%, transparent 100%)",
              border: "1px solid var(--glass-border)",
              zIndex: -1,
            }}
          />
          {/* Titulo y contador de opiniones */}
          <div className="flex justify-between">
            <h2 className="text-base font-semibold text-[var(--text-primary)] mb-4 flex items-center gap-2">
              <IconCalendar /> Opiniones ({fmt(data.total_opiniones_bd)})
            </h2>
            <span className="text-sm text-[var(--text-muted)]">
              Mostrando {opinions.length}/{data.total_opiniones_bd}
            </span>
          </div>

          {opError ? (
            <div className="text-center py-6 text-red-500">
              <p className="text-[13px] mb-3">{opError}</p>
              <Button
                variant="secondary"
                onClick={() => loadOpinions(opPage, opinions.length === 0)}
                className="text-xs"
              >
                <IconRefresh className="mr-1.5" /> Reintentar
              </Button>
            </div>
          ) : opinions.length === 0 && !opLoading ? (
            <div className="text-[13px] text-[var(--text-muted)] text-center py-6">
              No hay opiniones en la base de datos para este especialista.
            </div>
          ) : (
            <div className="relative -mx-3 p-3">
              <div
                className="opiniones-scroll-container custom-scrollbar pr-2 flex flex-col gap-3 overflow-y-auto"
                style={{ maxHeight: "500px" }}
              >
                {opinions.map((op, i) => {
                  const isLast = i === opinions.length - 1;
                  return (
                    <div
                      key={op.opinion_id || op._id}
                      ref={isLast ? lastOpinionElementRef : null}
                      className="glass-card p-4 border border-[var(--glass-border)]"
                    >
                      <div className="flex justify-between items-start mb-2 flex-wrap gap-2">
                        <div className="flex items-center gap-2.5">
                          <div className="w-7 h-7 rounded-full bg-[var(--glass-bg)] border border-[var(--glass-border)] flex items-center justify-center text-[var(--text-muted)] text-xs font-bold">
                            {op.autor ? op.autor.charAt(0).toUpperCase() : "A"}
                          </div>
                          <div>
                            <div className="text-[13px] font-semibold text-[var(--text-primary)]">
                              {op.autor || "Anónimo"}
                            </div>
                            <div className="flex gap-2 flex-wrap text-[11px] text-[var(--text-muted)]">
                              {fmtFecha(op.fecha_publicacion)}

                              {op.tipo_verificacion && (
                                <span className="text-[10px] text-emerald-500 flex items-center gap-1">
                                  <IconCheck /> {op.tipo_verificacion}
                                </span>
                              )}
                              {op.servicio_consultado && (
                                <span className="text-[10px] text-[var(--text-muted)]">
                                  Servicio: {op.servicio_consultado}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-1 bg-amber-500/10 px-2 py-1 rounded-full">
                          <IconStar className="text-amber-500 text-xs" />
                          <span className="text-xs font-semibold text-amber-300">
                            {op.rating}
                          </span>
                        </div>
                      </div>

                      <p className="text-[13px] text-[var(--text-primary)] leading-relaxed mb-3">
                        {op.texto || "Sin comentario."}
                      </p>
                    </div>
                  );
                })}

                {opLoading && (
                  <div className="text-center py-5">
                    <div className="w-6 h-6 border-2 border-[var(--color-primary-200)] border-t-[var(--color-primary-500)] rounded-full animate-spin mx-auto" />
                  </div>
                )}

                {!opHasMore && opinions.length > 0 && (
                  <div className="text-center text-xs text-[var(--text-muted)] py-4 animate-bounce-once">
                    No hay más opiniones.
                  </div>
                )}

                {opHasMore && !opLoading && (
                  <div className="text-center mt-2">
                    <Button
                      variant="ghost"
                      onClick={() => loadOpinions(opPage + 1)}
                      className="text-xs"
                    >
                      Cargar más opiniones
                    </Button>
                  </div>
                )}
              </div>
            </div>
          )}
        </section>
      </div>

      <ConfirmModal
        isOpen={deleteModal}
        onClose={() => setDeleteModal(false)}
        onConfirm={handleDelete}
        loading={actionLoading}
        title="Eliminar Especialista"
        message={`¿Estás seguro de que deseas eliminar a ${normalizeName(doc.nombre)}? Esta operación eliminará el perfil, análisis y opiniones, y no se puede deshacer.`}
        confirmText="Eliminar permanentemente"
        cancelText="Cancelar"
      />

      <ConfirmModal
        isOpen={analysisModal}
        onClose={() => setAnalysisModal(false)}
        onConfirm={handleAnalyze}
        loading={actionLoading}
        title="Generar Análisis IA"
        message={`¿Generar un nuevo análisis para este especialista? El sistema usará automáticamente el primer proveedor disponible (Ollama → LM Studio → Gemini → Groq). Esto reemplazará el análisis actual si existe.`}
        confirmText="Iniciar Análisis"
        cancelText="Cancelar"
        variant="primary"
        icon={<IconBrain className="text-xl" />}
      />

      <style>{`
        @keyframes spin { 100% { transform: rotate(360deg); } }
        @keyframes bounce-once { 
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-5px); }
        }
        @media (prefers-reduced-motion: reduce) {
          * { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; transition-duration: 0.01ms !important; scroll-behavior: auto !important; }
        }
      `}</style>
      <Footer />
    </PageWrapper>
  );
}
