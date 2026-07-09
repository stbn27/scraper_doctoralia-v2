/**
 * chat.api.js — Capa de servicios del chatbot médico.
 *
 * Maneja la comunicación con los endpoints de interpretación del LLM,
 * incluyendo la verificación de proveedores disponibles y el envío
 * de tokens externos cuando no hay LLM local.
 */

import { realizarPeticion } from './api';

// Clave de localStorage para el token externo del usuario
const CLAVE_TOKEN_EXTERNO = 'medrec_llm_token_externo';
const CLAVE_PROVEEDOR_EXTERNO = 'medrec_llm_proveedor_externo';

/**
 * Lee el token externo guardado por el usuario en localStorage.
 * @returns {{ token: string|null, proveedor: string|null }}
 */
export function leerTokenExterno() {
  try {
    const token = window.localStorage.getItem(CLAVE_TOKEN_EXTERNO) || null;
    const proveedor = window.localStorage.getItem(CLAVE_PROVEEDOR_EXTERNO) || 'gemini';
    return { token, proveedor };
  } catch {
    return { token: null, proveedor: null };
  }
}

/**
 * Guarda el token externo del usuario en localStorage.
 * @param {string} token - API key del proveedor externo.
 * @param {string} [proveedor='gemini'] - Nombre del proveedor ('gemini' o 'groq').
 */
export function guardarTokenExterno(token, proveedor = 'gemini') {
  try {
    window.localStorage.setItem(CLAVE_TOKEN_EXTERNO, token.trim());
    window.localStorage.setItem(CLAVE_PROVEEDOR_EXTERNO, proveedor);
  } catch { /* silencioso */ }
}

/**
 * Elimina el token externo guardado.
 */
export function limpiarTokenExterno() {
  try {
    window.localStorage.removeItem(CLAVE_TOKEN_EXTERNO);
    window.localStorage.removeItem(CLAVE_PROVEEDOR_EXTERNO);
  } catch { /* silencioso */ }
}

/**
 * Verifica el estado de los proveedores LLM disponibles en el backend.
 *
 * @returns {Promise<{
 *   lmstudio: boolean,
 *   ollama: boolean,
 *   externo_disponible: boolean,
 *   requiere_token: boolean
 * }>}
 */
export async function verificarEstadoLLM() {
  try {
    const datos = await realizarPeticion('/chat/estado');
    return datos || { lmstudio: false, ollama: false, externo_disponible: false, requiere_token: true };
  } catch {
    return { lmstudio: false, ollama: false, externo_disponible: false, requiere_token: true };
  }
}

/**
 * Envía el historial del chat al backend para interpretación médica.
 *
 * Si el backend responde 402 (no hay LLM local), relanza el error
 * con la bandera `requiere_token: true` para que el componente
 * ChatPanel pueda solicitar el token al usuario.
 *
 * @param {Array<{role: string, content: string}>} historial - Historial de mensajes del chat.
 * @returns {Promise<Object>} Respuesta normalizada del LLM.
 *
 * @example
 * const respuesta = await enviarMensajeChat(historial);
 * if (respuesta.ready) { // redirigir a búsqueda }
 */
export async function enviarMensajeChat(historial = []) {
  const mensajes = Array.isArray(historial)
    ? historial
      .filter((msg) => msg?.role && typeof msg?.content === 'string')
      .map(({ role, content }) => ({ role, content }))
    : [];

  const consulta = mensajes[mensajes.length - 1]?.content?.trim() ?? '';

  if (!consulta) {
    throw new Error('No hay mensaje para enviar al chat');
  }

  const tokenInfo = leerTokenExterno();
  const hayToken = window.localStorage.getItem('medrec_token');
  const endpoint = hayToken ? '/chat/interpretar/auth' : '/chat/interpretar';

  const cuerpo = {
    consulta,
    messages: mensajes,
    provider: 'auto',
    auto_search: false,
    ...(tokenInfo.token && {
      token_externo: tokenInfo.token,
      proveedor_externo: tokenInfo.proveedor,
    }),
  };

  let datos;
  try {
    datos = await realizarPeticion(endpoint, {
      method: 'POST',
      body: JSON.stringify(cuerpo),
    });
  } catch (error) {
    // HTTP 402: no hay LLM local disponible
    if (error?.message?.includes('402') || error?.status === 402) {
      const err = new Error('No hay LLM local disponible.');
      err.requiere_token = true;
      throw err;
    }
    throw error;
  }

  const filtros = datos?.filtros ?? {};

  return {
    role: 'assistant',
    content: datos?.mensaje ?? 'No pude procesar tu mensaje.',
    respuesta: Array.isArray(datos?.respuesta)
      ? datos.respuesta
      : ['Lo siento, hubo un error procesando el mensaje.'],
    especialidad: filtros?.especialidad ?? null,
    ciudad: filtros?.ubicacion ?? null,
    filtros,
    sql: datos?.sql ?? null,
    ready: Boolean(datos?.ready),
    suggestions: Array.isArray(datos?.sugerencias) ? datos.sugerencias : [],
    ubicaciones_usuario: Array.isArray(datos?.ubicaciones_usuario)
      ? datos.ubicaciones_usuario
      : [],
  };
}
