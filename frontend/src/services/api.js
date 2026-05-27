/**
 * api.js — Capa de servicios de MedRec.
 * Todas las funciones simulan llamadas al backend con delay de 800ms.
 * Para migrar a API real, reemplazar los imports mock por fetch().
 */

import mockSpecialists from './mock/mockSpecialists.json';
import mockUser from './mock/mockUser.json';
import mockHistory from './mock/mockHistory.json';

/** Delay configurable para simular latencia del backend */
const API_DELAY = 800;

/**
 * Utilidad que envuelve un valor en un Promise con delay.
 * @param {*} data — Datos a devolver.
 * @param {number} [delay=API_DELAY] — Milisegundos de espera.
 * @returns {Promise<*>}
 */
const withDelay = (data, delay = API_DELAY) =>
  new Promise((resolve) => setTimeout(() => resolve(data), delay));

/* ──────────────────────────────────────────────
   Especialistas
   ────────────────────────────────────────────── */

/**
 * Busca especialistas aplicando filtros opcionales.
 * @param {{ especialidad?: string, ciudad?: string, precioMin?: number, precioMax?: number, atiendeNinos?: boolean, atiendeAdultos?: boolean, minOpiniones?: number }} filtros
 * @returns {Promise<{ fuente: string, total: number, especialidad: string, ciudad: string, especialistas: Array }>}
 */
export async function searchSpecialists(filtros = {}) {
  let results = [...mockSpecialists];

  if (filtros.especialidad) {
    const esp = filtros.especialidad.toLowerCase();
    results = results.filter((e) =>
      e.especialidad.toLowerCase().includes(esp)
    );
  }

  if (filtros.ciudad) {
    const city = filtros.ciudad.toLowerCase();
    results = results.filter((e) =>
      e.ciudad.toLowerCase().includes(city)
    );
  }

  if (filtros.precioMin != null) {
    results = results.filter((e) =>
      e.servicios.some((s) => s.precio_desde >= filtros.precioMin)
    );
  }

  if (filtros.precioMax != null) {
    results = results.filter((e) =>
      e.servicios.some((s) => s.precio_desde <= filtros.precioMax)
    );
  }

  if (filtros.atiendeNinos) {
    results = results.filter((e) => e.pacientes.atiende_ninos);
  }

  if (filtros.atiendeAdultos) {
    results = results.filter((e) => e.pacientes.atiende_adultos);
  }

  if (filtros.minOpiniones != null && filtros.minOpiniones > 0) {
    results = results.filter((e) => e.total_opiniones >= filtros.minOpiniones);
  }

  const response = {
    fuente: 'mock',
    total: results.length,
    especialidad: filtros.especialidad || '',
    ciudad: filtros.ciudad || '',
    especialistas: results,
  };

  return withDelay(response);
}

/**
 * Obtiene un especialista por su ID.
 * @param {string} id — ID del especialista (_id).
 * @returns {Promise<Object|null>}
 */
export async function getSpecialistById(id) {
  const specialist = mockSpecialists.find((e) => e._id === id) || null;
  return withDelay(specialist);
}

/* ──────────────────────────────────────────────
   Chatbot
   ────────────────────────────────────────────── */

/** Mapa de palabras clave → especialidad */
const SPECIALTY_KEYWORDS = {
  'muela': 'Dentista',
  'diente': 'Dentista',
  'dental': 'Dentista',
  'dentista': 'Dentista',
  'endodoncia': 'Endodoncia',
  'endodoncista': 'Endodoncia',
  'conducto': 'Endodoncia',
  'corazón': 'Cardiología',
  'cardiólogo': 'Cardiología',
  'cardiología': 'Cardiología',
  'presión': 'Cardiología',
  'pecho': 'Cardiología',
  'piel': 'Dermatología',
  'dermatólogo': 'Dermatología',
  'dermatología': 'Dermatología',
  'acné': 'Dermatología',
  'manchas': 'Dermatología',
  'hueso': 'Ortopedia',
  'rodilla': 'Ortopedia',
  'ortopedista': 'Ortopedia',
  'ortopedia': 'Ortopedia',
  'fractura': 'Ortopedia',
  'columna': 'Ortopedia',
  'espalda': 'Ortopedia',
};

/** Ciudades reconocidas */
const CITY_KEYWORDS = [
  'ciudad de méxico', 'cdmx', 'méxico', 'guadalajara', 'monterrey',
  'puebla', 'tijuana', 'león', 'mérida', 'querétaro',
];

/**
 * Procesa un mensaje del chatbot y devuelve la respuesta del asistente.
 * Analiza keywords para detectar especialidad y ciudad.
 * @param {Array<{ role: string, content: string }>} history — Historial de mensajes.
 * @returns {Promise<{ role: string, content: string, especialidad?: string, ciudad?: string, ready?: boolean }>}
 */
export async function chatMessage(history) {
  const lastMsg = history[history.length - 1]?.content?.toLowerCase() || '';

  // Revisar si ya se detectó especialidad en mensajes previos
  let detectedSpecialty = null;
  let detectedCity = null;

  // Buscar en todo el historial
  for (const msg of history) {
    const text = msg.content.toLowerCase();

    // Buscar especialidad
    if (!detectedSpecialty) {
      for (const [keyword, specialty] of Object.entries(SPECIALTY_KEYWORDS)) {
        if (text.includes(keyword)) {
          detectedSpecialty = specialty;
          break;
        }
      }
    }

    // Buscar ciudad
    if (!detectedCity) {
      for (const city of CITY_KEYWORDS) {
        if (text.includes(city)) {
          detectedCity = city.charAt(0).toUpperCase() + city.slice(1);
          // Normalizar CDMX
          if (detectedCity === 'Cdmx') detectedCity = 'Ciudad de México';
          if (detectedCity === 'México') detectedCity = 'Ciudad de México';
          break;
        }
      }
    }
  }

  let response;

  if (detectedSpecialty && detectedCity) {
    response = {
      role: 'assistant',
      content: `Perfecto. Voy a buscarte especialistas de ${detectedSpecialty} en ${detectedCity}. ¿Listo para ver los resultados?`,
      especialidad: detectedSpecialty,
      ciudad: detectedCity,
      ready: true,
    };
  } else if (detectedSpecialty && !detectedCity) {
    response = {
      role: 'assistant',
      content: `Entendido, parece que necesitas un/a ${detectedSpecialty}. ¿En qué ciudad te encuentras?`,
      especialidad: detectedSpecialty,
    };
  } else if (!detectedSpecialty && detectedCity) {
    response = {
      role: 'assistant',
      content: `Bien, estás en ${detectedCity}. ¿Qué tipo de especialista necesitas o qué síntomas tienes?`,
      ciudad: detectedCity,
    };
  } else {
    response = {
      role: 'assistant',
      content: '¿Puedes darme más detalles? Por ejemplo: ¿qué síntomas tienes o qué especialidad necesitas?',
    };
  }

  return withDelay(response, 600);
}

/* ──────────────────────────────────────────────
   Favoritos
   ────────────────────────────────────────────── */

/** Favoritos en memoria (simula persistencia) */
let userFavorites = [...(mockUser.favoritos || [])];

/**
 * Obtiene la lista de IDs de favoritos del usuario.
 * @returns {Promise<string[]>}
 */
export async function getFavorites() {
  return withDelay([...userFavorites]);
}

/**
 * Obtiene los especialistas favoritos completos.
 * @returns {Promise<Object[]>}
 */
export async function getFavoriteSpecialists() {
  const favs = mockSpecialists.filter((e) => userFavorites.includes(e._id));
  return withDelay(favs);
}

/**
 * Agrega un especialista a favoritos.
 * @param {string} id — ID del especialista.
 * @returns {Promise<{ success: boolean }>}
 */
export async function addFavorite(id) {
  if (!userFavorites.includes(id)) {
    userFavorites.push(id);
  }
  return withDelay({ success: true });
}

/**
 * Elimina un especialista de favoritos.
 * @param {string} id — ID del especialista.
 * @returns {Promise<{ success: boolean }>}
 */
export async function removeFavorite(id) {
  userFavorites = userFavorites.filter((fid) => fid !== id);
  return withDelay({ success: true });
}

/**
 * Verifica si un especialista está en favoritos.
 * @param {string} id — ID del especialista.
 * @returns {boolean}
 */
export function isFavorite(id) {
  return userFavorites.includes(id);
}

/* ──────────────────────────────────────────────
   Historial
   ────────────────────────────────────────────── */

/**
 * Obtiene el historial de búsquedas del usuario.
 * @param {{ especialidad?: string, fechaDesde?: string, fechaHasta?: string }} filtros
 * @returns {Promise<Array>}
 */
export async function getSearchHistory(filtros = {}) {
  let results = [...mockHistory];

  if (filtros.especialidad) {
    results = results.filter((h) =>
      h.especialidad.toLowerCase().includes(filtros.especialidad.toLowerCase())
    );
  }

  if (filtros.fechaDesde) {
    results = results.filter((h) => new Date(h.fecha) >= new Date(filtros.fechaDesde));
  }

  if (filtros.fechaHasta) {
    results = results.filter((h) => new Date(h.fecha) <= new Date(filtros.fechaHasta));
  }

  return withDelay(results);
}

/* ──────────────────────────────────────────────
   Resumen de reseñas (mock PLN)
   ────────────────────────────────────────────── */

/** Reseñas mock simulando un resumen PLN */
const MOCK_REVIEWS = {
  '6a13b0c47fd1ef789ffab5bc': 'Los pacientes destacan la precisión del diagnóstico y el trato amable de la Dra. Aquino. La mayoría reporta alivio del dolor desde la primera sesión. Se valora especialmente su paciencia para explicar los procedimientos.',
  '7b24c1d58ge2fg890ggbc6cd': 'El Dr. Ramírez es reconocido por su profesionalismo y puntualidad. Los pacientes mencionan que sus explicaciones son claras y detalladas. Se destaca la calidad del equipo diagnóstico en su consultorio.',
  '8c35d2e69hf3gh901hhcd7de': 'La Dra. Hernández recibe elogios por su atención personalizada y seguimiento post-consulta. Varios pacientes han mejorado significativamente con sus tratamientos de acné y rosácea.',
  '9d46e3f70ig4hi012iide8ef': 'El Dr. Fuentes es valorado por su experiencia en lesiones deportivas. Algunos pacientes mencionan tiempos de espera largos, pero califican positivamente los resultados de sus tratamientos.',
  '0e57f4g81jh5ij123jjef9fg': 'La Dra. López es muy popular entre familias por su trato cálido con niños y adultos. Los pacientes destacan la limpieza del consultorio y precios accesibles.',
  '1f68g5h92ki6jk234kkfg0gh': 'El Dr. Vargas es reconocido como uno de los mejores cardiólogos de la zona. Los pacientes confían en su diagnóstico preciso y recomiendan ampliamente sus servicios.',
  '2g79h6i03lj7kl345llgh1hi': 'Pocos pacientes han dejado reseñas, pero los que lo han hecho valoran la amabilidad de la Dra. Martínez y el ambiente tranquilo de su consultorio.',
  '3h80i7j14mk8lm456mmhi2ij': 'El Dr. Aguilar es recomendado por atletas y deportistas. Su enfoque conservador es valorado, aunque algunos pacientes desean más opciones quirúrgicas disponibles.',
};

/**
 * Obtiene el resumen de reseñas simulado (PLN) para un especialista.
 * @param {string} id — ID del especialista.
 * @returns {Promise<string>}
 */
export async function getReviewSummary(id) {
  const summary = MOCK_REVIEWS[id] || 'Sin reseñas disponibles para este especialista.';
  return withDelay(summary, 500);
}
