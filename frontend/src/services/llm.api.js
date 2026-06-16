import { realizarPeticion } from './api';

/**
 * Obtener todos los tokens LLM guardados por el usuario
 */
export async function listarTokensLLM() {
  return realizarPeticion('/usuarios/me/tokens');
}

/**
 * Guardar o actualizar un token LLM
 * @param {string} modelo - Ej. 'deepseek', 'gemini'
 * @param {string} token - El api key
 */
export async function guardarTokenLLM(modelo, token) {
  return realizarPeticion('/usuarios/me/tokens', {
    method: 'POST',
    body: JSON.stringify({ modelo, token })
  });
}

/**
 * Eliminar un token LLM
 * @param {string} modelo 
 */
export async function eliminarTokenLLM(modelo) {
  return realizarPeticion(`/usuarios/me/tokens/${modelo}`, {
    method: 'DELETE'
  });
}

/**
 * Ejecutar scraping y análisis avanzado
 * @param {Object} data - { url, max_opinions, scrape_only, analyze, model }
 */
export async function scrapeAnalyze(data) {
  return realizarPeticion('/especialistas/avanzada/scrape-analyze', {
    method: 'POST',
    body: JSON.stringify(data)
  });
}
