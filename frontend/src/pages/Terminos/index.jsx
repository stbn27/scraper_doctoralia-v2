import React from 'react';
import { PageWrapper } from '@/components/layout/PageWrapper';
import { BubbleBackground } from '@/components/layout/BubbleBackground';
import { Navbar } from '@/components/layout/Navbar';
import { Footer } from '@/components/layout/Footer';

/**
 * Secciones del documento legal de Términos y Condiciones de Uso.
 */
const SECCIONES_TERMINOS = [
  {
    id: 'proposito-academico',
    numero: '1',
    titulo: 'Propósito Académico y Sin Fines de Lucro',
    contenido: [
      'Este sistema web ha sido desarrollado exclusivamente con fines académicos y educativos. No tiene carácter comercial ni persigue ningún beneficio económico. Su objetivo es demostrar capacidades técnicas de desarrollo de software y explorar conceptos de inteligencia artificial aplicada a la salud.',
    ],
  },
  {
    id: 'origen-veracidad',
    numero: '2',
    titulo: 'Origen y Veracidad de la Información',
    contenido: [
      'La información presentada en esta plataforma ha sido obtenida de perfiles públicos disponibles en "doctoralia.mx". Es importante destacar que:',
    ],
    puntos: [
      'La información puede no estar actualizada, ya que depende de fuentes externas.',
      'No nos responsabilizamos por la exactitud, vigencia o integridad de los datos mostrados.',
      'Se recomienda a los usuarios verificar directamente con los especialistas cualquier dato relevante antes de tomar decisiones.',
    ],
  },
  {
    id: 'limitacion-chatbot',
    numero: '3',
    titulo: 'Limitación de Responsabilidad del Asistente Virtual (Chatbot)',
    contenido: [
      'El sistema incorpora un asistente virtual impulsado por inteligencia artificial que puede:',
    ],
    puntos: [
      'Generar sugerencias o recomendaciones basadas en el análisis de texto proporcionado por el usuario.',
      'Cometer errores, omisiones o interpretaciones incorrectas debido a las limitaciones propias del modelo de IA.',
    ],
    subcontenido: 'Por lo tanto, el(los) desarrollador(es) del sistema no se hacen responsables por:',
    subpuntos: [
      'Decisiones médicas tomadas basadas en las sugerencias del chatbot.',
      'Interpretaciones erróneas de los síntomas o necesidades del usuario.',
      'Recomendaciones de especialistas que no se ajusten a las necesidades reales del usuario.',
    ],
  },
  {
    id: 'naturaleza-recomendaciones',
    numero: '4',
    titulo: 'Naturaleza de las Recomendaciones',
    contenido: [
      'Las recomendaciones generadas por el sistema:',
    ],
    puntos: [
      'NO constituyen un diagnóstico médico ni reemplazan la consulta profesional con un especialista.',
      'NO garantizan que el especialista sugerido sea el más adecuado para el caso particular del usuario.',
      'NO pretenden menospreciar, desacreditar ni comparar negativamente el trabajo de ningún profesional de la salud.',
    ],
    conclusion: 'El usuario debe considerar que la elección final de un especialista es su responsabilidad exclusiva.',
  },
  {
    id: 'privacidad-datos',
    numero: '5',
    titulo: 'Privacidad y Manejo de Datos',
    contenido: [
      'Este sistema:',
    ],
    puntos: [
      'No almacena información personal sensible del usuario en bases de datos.',
      'Procesa temporalmente los datos ingresados únicamente para generar respuestas contextuales.',
      'No comparte ni comercializa con terceros la información proporcionada por los usuarios.',
    ],
  },
  {
    id: 'uso-aceptable',
    numero: '6',
    titulo: 'Uso Aceptable',
    contenido: [
      'El usuario se compromete a:',
    ],
    puntos: [
      'Utilizar el sistema de manera ética y responsable.',
      'No emplear la plataforma para fines ilegales o malintencionados.',
      'No intentar manipular, vulnerar o alterar el funcionamiento del sistema.',
    ],
  },
  {
    id: 'disponibilidad-servicio',
    numero: '7',
    titulo: 'Disponibilidad del Servicio',
    contenido: [
      'El sistema se encuentra en fase de desarrollo y pruebas, por lo que:',
    ],
    puntos: [
      'Puede presentar interrupciones, caídas o fallos inesperados.',
      'No se garantiza su disponibilidad continua ni ininterrumpida.',
      'Nos reservamos el derecho de modificar, suspender o descontinuar el servicio en cualquier momento.',
    ],
  },
  {
    id: 'actualizacion-terminos',
    numero: '8',
    titulo: 'Actualización de los Términos',
    contenido: [
      'Estos términos y condiciones pueden ser actualizados periódicamente. Es responsabilidad del usuario revisarlos antes de cada uso del sistema.',
    ],
  },
  {
    id: 'contacto-soporte',
    numero: '9',
    titulo: 'Contacto y Soporte',
    contenido: [
      'Para cualquier duda, comentario o reporte de fallos, el usuario puede ponerse en contacto con los desarrolladores a través de los canales habilitados dentro de la plataforma.',
    ],
  },
];

/**
 * Terminos — Página de Términos y Condiciones de Uso de MedRec.
 *
 * Implementa un diseño formal, limpio y profesional con tipografía seria,
 * separadores sutiles, espaciado generoso y animaciones de entrada al scroll.
 *
 * @returns {React.JSX.Element} Página de Términos y Condiciones.
 */
export default function Terminos() {
  return (
    <PageWrapper name="terminos" className="relative">
      <BubbleBackground />
      <Navbar />

      <main className="relative z-10 mx-auto max-w-4xl px-4 pb-24 pt-28 sm:px-6 lg:px-8 font-primary">
        {/* Encabezado del Documento */}
        <header className="scroll-reveal pb-12 border-b border-black/10 dark:border-white/10">
          <p className="text-xs sm:text-sm font-semibold uppercase tracking-widest text-royalBlue-600 dark:text-royalBlue-400 mb-3">
            Documento Legal y Normativa
          </p>

          <h1 className="text-3xl sm:text-5xl font-bold tracking-tight text-slate-900 dark:text-white">
            Términos y Condiciones de Uso
          </h1>

          <p
            className="mt-4 text-base sm:text-lg leading-relaxed max-w-3xl"
            style={{ color: 'var(--text-muted)' }}
          >
            El presente documento establece las condiciones generales que regulan el acceso,
            el uso ético y las limitaciones técnicas de la plataforma académica MedRec
            y su asistente virtual médico de inteligencia artificial.
          </p>
        </header>

        {/* Lista de Secciones con Animación al Scroll */}
        <div className="divide-y divide-black/10 dark:divide-white/10">
          {SECCIONES_TERMINOS.map((seccion) => (
            <section
              key={seccion.id}
              id={seccion.id}
              className="scroll-reveal py-10 sm:py-14 space-y-4"
            >
              <div className="flex flex-col sm:flex-row sm:items-baseline gap-2 sm:gap-6">
                <span className="text-base sm:text-lg font-bold font-numbers tracking-wider text-royalBlue-600 dark:text-royalBlue-400 w-12 flex-shrink-0">
                  {seccion.numero.padStart(2, '0')}.
                </span>

                <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
                  {seccion.titulo}
                </h2>
              </div>

              <div className="sm:pl-18 space-y-4 text-base leading-relaxed">
                {seccion.contenido.map((parrafo, idx) => (
                  <p
                    key={idx}
                    className="leading-relaxed"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    {parrafo}
                  </p>
                ))}

                {seccion.puntos && (
                  <ul className="list-disc list-outside ml-5 space-y-2 pt-1" style={{ color: 'var(--text-muted)' }}>
                    {seccion.puntos.map((punto, idx) => (
                      <li key={idx} className="leading-relaxed pl-1">
                        <span className="text-slate-800 dark:text-slate-200">{punto}</span>
                      </li>
                    ))}
                  </ul>
                )}

                {seccion.subcontenido && (
                  <p className="font-medium pt-3 text-slate-800 dark:text-slate-200">
                    {seccion.subcontenido}
                  </p>
                )}

                {seccion.subpuntos && (
                  <ul className="list-disc list-outside ml-5 space-y-2 pt-1" style={{ color: 'var(--text-muted)' }}>
                    {seccion.subpuntos.map((subpunto, idx) => (
                      <li key={idx} className="leading-relaxed pl-1">
                        <span className="text-slate-800 dark:text-slate-200">{subpunto}</span>
                      </li>
                    ))}
                  </ul>
                )}

                {seccion.conclusion && (
                  <p className="mt-6 pt-4 border-t border-black/5 dark:border-white/5 font-medium text-slate-800 dark:text-slate-200">
                    {seccion.conclusion}
                  </p>
                )}
              </div>
            </section>
          ))}
        </div>

        {/* Pie de Documento con Fecha de Actualización */}
        <footer className="scroll-reveal mt-16 pt-8 border-t border-black/10 dark:border-white/10 text-center text-xs sm:text-sm" style={{ color: 'var(--text-muted)' }}>
          <p className="font-semibold text-slate-800 dark:text-slate-200">
            Última actualización: julio de 2026
          </p>
          <p className="mt-1">
            Plataforma MedRec — Desarrollo de software sin fines de lucro para investigación y fines académicos.
          </p>
        </footer>
      </main>

      <Footer />
    </PageWrapper>
  );
}
