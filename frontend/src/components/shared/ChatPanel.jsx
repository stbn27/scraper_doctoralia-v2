/**
 * ChatPanel.jsx — Panel de chat del asistente médico MedRec.
 *
 * Características:
 * - Verifica disponibilidad de LLM local al montar el componente.
 * - Si no hay LLM local, muestra un modal para ingresar token externo.
 * - Detecta el idioma del usuario y responde en el mismo idioma.
 * - Valida especialidad y ciudad contra la base de datos antes de mostrar resultados.
 * - Soporta código postal como ubicación.
 *
 * Props:
 * @param {string}   [className='']        - Clases CSS adicionales para el contenedor.
 * @param {boolean}  [compact=false]       - Modo compacto con menos padding.
 * @param {Function} [onDetectedChange]    - Callback cuando cambia la especialidad/ciudad detectada.
 */

import React, { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  RiRobot2Line,
  RiSendPlaneLine,
  RiSearchLine,
  RiMapPinLine,
  RiKeyLine,
  RiCloseLine,
} from "react-icons/ri";
import { Button } from "@/components/ui/Button";
import {
  enviarMensajeChat,
  verificarEstadoLLM,
  guardarTokenExterno,
  leerTokenExterno,
} from "@/services/chat.api";

const MENSAJE_INICIAL = {
  role: "assistant",
  content:
    "¡Hola! Soy tu asistente médico. Cuéntame: ¿qué molestia tienes o qué tipo de especialista estás buscando?",
};

// ---------------------------------------------------------------------------
// Componente modal para ingresar token externo
// ---------------------------------------------------------------------------

/**
 * ModalTokenExterno — solicita al usuario un API key cuando no hay LLM local.
 *
 * @param {Function} onConfirmar - Callback con (token, proveedor) al confirmar.
 * @param {Function} onCerrar   - Callback al cancelar.
 */
function ModalTokenExterno({ onConfirmar, onCerrar }) {
  const [token, setToken] = useState("");
  const [proveedor, setProveedor] = useState("gemini");
  const [error, setError] = useState("");

  const manejarConfirmar = () => {
    const trimmed = token.trim();
    if (!trimmed || trimmed.length < 10) {
      setError("Por favor ingresa un token válido (mínimo 10 caracteres).");
      return;
    }
    onConfirmar(trimmed, proveedor);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="bg-[#16181d] border border-white/10 rounded-2xl p-6 w-full max-w-md mx-4 shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <RiKeyLine className="text-royalBlue-400 text-xl" />
            <h2 className="text-base font-semibold text-white">
              Se requiere API Key
            </h2>
          </div>
          <button
            onClick={onCerrar}
            className="text-white/40 hover:text-white/80 transition-colors"
            aria-label="Cerrar"
          >
            <RiCloseLine className="text-xl" />
          </button>
        </div>

        <p className="text-sm text-white/60 mb-5 leading-relaxed">
          No hay ningún modelo de IA local disponible en este momento (LM Studio
          / Ollama). Puedes continuar usando un proveedor externo ingresando tu
          API key.
        </p>

        <div className="space-y-4">
          <div>
            <label className="text-xs font-medium text-white/60 mb-1.5 block">
              Proveedor
            </label>
            <select
              value={proveedor}
              onChange={(e) => setProveedor(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-royalBlue-500"
            >
              <option value="gemini">Google Gemini</option>
              <option value="groq">Groq</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-medium text-white/60 mb-1.5 block">
              API Key de {proveedor === "gemini" ? "Google Gemini" : "Groq"}
            </label>
            <input
              type="password"
              value={token}
              onChange={(e) => {
                setToken(e.target.value);
                setError("");
              }}
              placeholder={proveedor === "gemini" ? "AIza..." : "gsk_..."}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder-white/30 focus:outline-none focus:border-royalBlue-500"
            />
            {error && <p className="text-xs text-red-400 mt-1">{error}</p>}
          </div>

          <p className="text-xs text-white/40 leading-relaxed">
            Tu API key se guarda solo en este dispositivo y se envía de forma
            segura al servidor local.
          </p>

          <div className="flex gap-3 pt-2">
            <button
              onClick={onCerrar}
              className="flex-1 border border-white/10 rounded-xl py-2 text-sm text-white/60 hover:bg-white/5 transition-colors"
            >
              Cancelar
            </button>
            <button
              onClick={manejarConfirmar}
              className="flex-1 bg-royalBlue-600 hover:bg-royalBlue-700 text-white rounded-xl py-2 text-sm font-medium transition-colors"
            >
              Usar este proveedor
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Burbuja de mensaje individual
// ---------------------------------------------------------------------------

/**
 * BurbujaMensaje — renderiza un mensaje del chat con estilos diferenciados.
 *
 * @param {{ role: string, content: string }} message - Mensaje a renderizar.
 */
function BurbujaMensaje({ message }) {
  const esAsistente = message.role === "assistant";

  return (
    <div
      className={`flex items-end gap-2 ${
        esAsistente ? "" : "flex-row-reverse"
      }`}
    >
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
          esAsistente ? "bg-royalBlue-700" : "bg-royalBlue-700/90"
        }`}
      >
        {esAsistente ? (
          <RiRobot2Line className="text-sm text-royalBlue-300" />
        ) : (
          <span className="text-xs font-semibold text-white">Tú</span>
        )}
      </div>

      <div
        className={`max-w-[80%] px-4 py-2.5 text-sm leading-relaxed backdrop-blur ${
          esAsistente
            ? "glass-card-chat"
            : "bg-royalBlue-700/80 text-white dark:bg-royalBlue-600/80 rounded-2xl rounded-tr-none"
        }`}
      >
        {message.content}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Componente principal ChatPanel
// ---------------------------------------------------------------------------

export function ChatPanel({
  className = "",
  compact = false,
  onDetectedChange,
}) {
  const navigate = useNavigate();
  const [mensajes, setMensajes] = useState([MENSAJE_INICIAL]);
  const [input, setInput] = useState("");
  const [estaEscribiendo, setEstaEscribiendo] = useState(false);
  const [datosDetectados, setDatosDetectados] = useState({
    especialidad: null,
    ciudad: null,
    ready: false,
  });
  const [sugerenciasActuales, setSugerenciasActuales] = useState([
    "Dentista",
    "Cardiólogo",
    "Dermatólogo",
    "Ortopedista",
  ]);
  const [mostrarBtnUbicacion, setMostrarBtnUbicacion] = useState(false);
  const [ubicacionesUsuario, setUbicacionesUsuario] = useState([]);
  const [mostrarModalToken, setMostrarModalToken] = useState(false);
  const [estadoLLM, setEstadoLLM] = useState(null);

  const finMensajesRef = useRef(null);
  const textareaRef = useRef(null);
  const contenedorScrollRef = useRef(null);
  const datosDetectadosRef = useRef(datosDetectados);

  // Mantener ref sincronizado
  useEffect(() => {
    datosDetectadosRef.current = datosDetectados;
  }, [datosDetectados]);

  // Scroll al fondo cuando llegan mensajes nuevos
  const scrollAlFondo = useCallback(() => {
    if (contenedorScrollRef.current) {
      contenedorScrollRef.current.scrollTo({
        top: contenedorScrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, []);

  useEffect(() => {
    scrollAlFondo();
  }, [mensajes, estaEscribiendo, scrollAlFondo]);

  // Foco en textarea cuando termina de escribir
  useEffect(() => {
    if (!estaEscribiendo) {
      textareaRef.current?.focus();
    }
  }, [estaEscribiendo]);

  // Verificar estado LLM al montar
  useEffect(() => {
    verificarEstadoLLM().then((estado) => {
      setEstadoLLM(estado);
      // Si se requiere token y no hay uno guardado, mostrar modal inmediatamente
      if (estado.requiere_token) {
        const { token } = leerTokenExterno();
        if (!token) {
          setMostrarModalToken(true);
        }
      }
    });
  }, []);

  /**
   * Envía un mensaje al backend y procesa la respuesta.
   * Si el backend responde 402, solicita token externo al usuario.
   *
   * @param {string} texto - Texto a enviar.
   */
  const enviarMensaje = useCallback(
    async (texto) => {
      if (!texto.trim() || estaEscribiendo) return;

      const mensajeUsuario = { role: "user", content: texto.trim() };
      const nuevoHistorial = [...mensajes, mensajeUsuario];
      setMensajes(nuevoHistorial);
      setInput("");
      setUbicacionesUsuario([]);
      setEstaEscribiendo(true);

      if (textareaRef.current) textareaRef.current.style.height = "auto";

      try {
        const respuesta = await enviarMensajeChat(nuevoHistorial);

        const mensajesRespuesta =
          respuesta.respuesta && respuesta.respuesta.length > 0
            ? respuesta.respuesta.map((msg) => ({
                role: "assistant",
                content: msg,
              }))
            : [{ role: "assistant", content: respuesta.content }];

        setMensajes((prev) => [...prev, ...mensajesRespuesta]);

        if (respuesta.suggestions && respuesta.suggestions.length > 0) {
          setSugerenciasActuales(respuesta.suggestions);
        }

        if (
          respuesta.ubicaciones_usuario &&
          respuesta.ubicaciones_usuario.length > 0
        ) {
          setUbicacionesUsuario(respuesta.ubicaciones_usuario);
        } else {
          setUbicacionesUsuario([]);
        }

        if (
          respuesta.sql &&
          (respuesta.sql.includes("UBICACION_USUARIO") ||
            respuesta.sql.includes("LOCATION_USER"))
        ) {
          setMostrarBtnUbicacion(true);
        } else {
          setMostrarBtnUbicacion(false);
        }

        // Preservar ciudad: tomar solo la primera parte (antes de la coma)
        const ciudadRaw =
          respuesta?.ciudad ?? datosDetectadosRef.current.ciudad;
        const ciudadLimpia = ciudadRaw ? ciudadRaw.split(",")[0].trim() : null;

        const siguientesDatos = {
          especialidad:
            respuesta?.especialidad ?? datosDetectadosRef.current.especialidad,
          ciudad: ciudadLimpia,
          ready: Boolean(respuesta?.ready || datosDetectadosRef.current.ready),
        };
        setDatosDetectados(siguientesDatos);
        onDetectedChange?.(siguientesDatos);
      } catch (error) {
        // El backend no tiene LLM local disponible → solicitar token
        if (error?.requiere_token) {
          setMostrarModalToken(true);
          setMensajes((prev) => [
            ...prev,
            {
              role: "assistant",
              content:
                "No hay un modelo de IA local activo. Por favor, ingresa tu API key para continuar.",
            },
          ]);
        } else {
          setMensajes((prev) => [
            ...prev,
            {
              role: "assistant",
              content: "Lo siento, hubo un error. ¿Puedes intentar de nuevo?",
            },
          ]);
        }
      } finally {
        setEstaEscribiendo(false);
      }
    },
    [estaEscribiendo, mensajes, onDetectedChange]
  );

  /**
   * Maneja la confirmación del token externo desde el modal.
   *
   * @param {string} token    - API key ingresado.
   * @param {string} proveedor - Proveedor seleccionado.
   */
  const manejarTokenConfirmado = (token, proveedor) => {
    guardarTokenExterno(token, proveedor);
    setMostrarModalToken(false);
    setEstadoLLM((prev) => ({ ...prev, requiere_token: false }));
    setMensajes((prev) => [
      ...prev,
      {
        role: "assistant",
        content: `✓ Token de ${
          proveedor === "gemini" ? "Google Gemini" : "Groq"
        } guardado. ¡Puedes continuar!`,
      },
    ]);
  };

  const manejarTecla = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      enviarMensaje(input);
    }
  };

  const manejarCambioTextarea = (e) => {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 80) + "px";
  };

  const mostrarChips =
    sugerenciasActuales &&
    sugerenciasActuales.length > 0 &&
    !datosDetectados.especialidad;

  return (
    <>
      {mostrarModalToken && (
        <ModalTokenExterno
          onConfirmar={manejarTokenConfirmado}
          onCerrar={() => setMostrarModalToken(false)}
        />
      )}

      <div className={`flex h-full min-h-0 flex-col ${className}`}>
        {/* Cabecera */}
        <div className="flex items-center justify-between p-4 border-b border-black/10 dark:border-white/10 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-royalBlue-700 flex items-center justify-center">
              <RiRobot2Line className="text-sm text-royalBlue-300" />
            </div>
            <div>
              <h1 className="text-base font-semibold">MedRec</h1>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                Asistente de búsqueda médica
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse-dot" />
            <span className="text-xs text-emerald-400">En línea</span>
          </div>
        </div>

        {/* Área de mensajes */}
        <div
          ref={contenedorScrollRef}
          className={`flex-1 min-h-0 overflow-y-auto ${
            compact ? "p-3 space-y-3" : "p-4 space-y-4"
          }`}
        >
          {mensajes.map((msg, i) => (
            <BurbujaMensaje key={i} message={msg} />
          ))}

          {/* Indicador de escritura */}
          {estaEscribiendo && (
            <div className="flex items-end gap-2">
              <div className="w-8 h-8 rounded-full bg-royalBlue-700 flex items-center justify-center shrink-0">
                <RiRobot2Line className="text-sm text-royalBlue-300" />
              </div>
              <div className="bg-royalBlue-900/60 backdrop-blur rounded-2xl rounded-tl-none px-4 py-3">
                <div className="flex gap-1.5">
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                </div>
              </div>
            </div>
          )}

          {/* Botón de búsqueda — solo cuando AMBOS especialidad Y ciudad están confirmados */}
          {datosDetectados.ready && datosDetectados.especialidad && datosDetectados.ciudad && !estaEscribiendo && (
            <div className="flex items-end gap-2">
              <div className="w-8 h-8 rounded-full bg-royalBlue-700 flex items-center justify-center shrink-0">
                <RiRobot2Line className="text-sm text-royalBlue-300" />
              </div>
              <div className="flex-1">
                <Button
                  variant="primary"
                  fullWidth
                  icon={<RiSearchLine />}
                  onClick={() => {
                    const params = new URLSearchParams();
                    if (datosDetectados.especialidad)
                      params.set("especialidad", datosDetectados.especialidad);
                    if (datosDetectados.ciudad) {
                      const primero = datosDetectados.ciudad
                        .split(",")[0]
                        .trim();
                      params.set("ciudad", primero);
                    }
                    navigate(`/busqueda?${params.toString()}`);
                  }}
                  className="rounded-xl py-3 text-base"
                >
                  Ver especialistas
                </Button>
              </div>
            </div>
          )}

          <div ref={finMensajesRef} />
        </div>

        {/* Chips de sugerencias de especialidad */}
        {mostrarChips && (
          <div className="px-4 pb-2 shrink-0 flex flex-wrap gap-2">
            {sugerenciasActuales.map((chip, idx) => (
              <button
                key={`${chip}-${idx}`}
                onClick={() => enviarMensaje(chip)}
                className="border border-royalBlue-400/80 dark:border-royalBlue-400/50 text-royalBlue-500 dark:text-royalBlue-300 rounded-full px-3 py-1 text-xs hover:bg-royalBlue-600/20 transition-all duration-200 hover:scale-105 press-effect"
              >
                {chip}
              </button>
            ))}
          </div>
        )}

        {/* Botones de ubicación registrada del usuario */}
        {ubicacionesUsuario &&
          ubicacionesUsuario.length > 0 &&
          !estaEscribiendo && (
            <div className="px-4 pb-4 shrink-0 flex flex-col gap-3 w-full">
              {ubicacionesUsuario.slice(0, 3).map((loc, idx) => (
                <button
                  key={`user-loc-${idx}`}
                  onClick={() => {
                    enviarMensaje(`Mi ubicación es ${loc}`);
                    setUbicacionesUsuario([]);
                  }}
                  className="w-full bg-royalBlue-900/60 hover:bg-royalBlue-800/80 text-neutral-light/90 border border-royalBlue-500/30 rounded-xl px-4 py-3 transition-all duration-200 flex flex-col items-start press-effect backdrop-blur-sm shadow-sm"
                >
                  <span className="text-sm font-semibold leading-tight flex items-center gap-2 mb-1">
                    <RiMapPinLine className="text-royalBlue-300" />
                    Usar mi ubicación registrada
                  </span>
                  <span className="text-xs opacity-75 leading-tight">
                    {loc}
                  </span>
                </button>
              ))}
            </div>
          )}

        {/* Botón único de ubicación (sin lista de ubicaciones registradas) */}
        {mostrarBtnUbicacion &&
          (!ubicacionesUsuario || ubicacionesUsuario.length === 0) &&
          !estaEscribiendo && (
            <div className="px-4 pb-2 shrink-0 flex">
              <button
                onClick={() => {
                  const userRaw = localStorage.getItem("medrec_user");
                  let ciudadUsuario = null;
                  if (userRaw) {
                    try {
                      const parsed = JSON.parse(userRaw);
                      ciudadUsuario =
                        parsed?.direccion_principal?.ciudad ||
                        parsed?.direccion_principal?.estado;
                    } catch (_) {}
                  }
                  if (ciudadUsuario) {
                    enviarMensaje(`Mi ubicación es ${ciudadUsuario}`);
                  } else {
                    setMensajes((prev) => [
                      ...prev,
                      {
                        role: "assistant",
                        content:
                          "No pude encontrar una ubicación en tu perfil. ¿Puedes escribirla por favor?",
                      },
                    ]);
                  }
                  setMostrarBtnUbicacion(false);
                }}
                className="bg-royalBlue-600 text-white rounded-full px-4 py-1.5 text-xs hover:bg-royalBlue-700 transition-all duration-200 flex items-center gap-1 press-effect"
              >
                <RiSearchLine className="text-xs" />
                Usar mi ubicación registrada
              </button>
            </div>
          )}

        {/* Botón para cambiar token externo */}
        {estadoLLM && estadoLLM.requiere_token && (
          <div className="px-4 pb-1 shrink-0 flex justify-end">
            <button
              onClick={() => setMostrarModalToken(true)}
              className="text-xs text-royalBlue-400 hover:text-royalBlue-300 flex items-center gap-1 transition-colors"
            >
              <RiKeyLine className="text-xs" />
              Cambiar API key
            </button>
          </div>
        )}

        {/* Área de entrada de texto */}
        <div className="p-4 border-t border-white/10 shrink-0">
          <div className="flex items-end gap-2">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={manejarCambioTextarea}
              onKeyDown={manejarTecla}
              placeholder="Escribe tu mensaje…"
              rows={1}
              className="glass-input flex-1 px-4 py-2.5 text-sm resize-none"
              style={{ maxHeight: "80px" }}
            />
            <button
              onClick={() => enviarMensaje(input)}
              disabled={!input.trim() || estaEscribiendo}
              className="p-2.5 rounded-xl bg-royalBlue-600 hover:bg-royalBlue-700 text-white transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed press-effect"
              aria-label="Enviar mensaje"
            >
              <RiSendPlaneLine className="text-xl" />
            </button>
          </div>
        </div>
        {/* Indicador de proveedor LLM activo */}
        {estadoLLM && (
          <span className="text-[0.4rem] dark:text-white/40 text-black/40 mr-1 w-full flex justify-end pe-3">
            Respuesta de:
            {estadoLLM.lmstudio
              ? "LM Studio"
              : estadoLLM.ollama
              ? "Ollama"
              : "Externo"}
          </span>
        )}
      </div>
    </>
  );
}

export default ChatPanel;
