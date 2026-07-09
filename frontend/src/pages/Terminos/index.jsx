import React from 'react';
import {
  RiShieldCheckLine,
  RiGraduationCapLine,
  RiDatabaseLine,
  RiRobot2Line,
  RiStethoscopeLine,
  RiLockPasswordLine,
  RiCheckDoubleLine,
  RiServerLine,
  RiRefreshLine,
  RiCustomerService2Line,
} from 'react-icons/ri';
import { PageWrapper } from '@/components/layout/PageWrapper';
import { BubbleBackground } from '@/components/layout/BubbleBackground';
import { Navbar } from '@/components/layout/Navbar';
import { Footer } from '@/components/layout/Footer';

/**
 * Secciones de los Términos y Condiciones de Uso del sistema MedRec.
 */
const SECCIONES_TERMINOS = [
  {
    id: 'proposito-academico',
    numero: '1',
    titulo: 'Propósito Académico y Sin Fines de Lucro',
    icono: RiGraduationCapLine,
    contenido: [
      'Este sistema web ha sido desarrollado exclusivamente con fines académicos y educativos. No tiene carácter comercial ni persigue ningún beneficio económico. Su objetivo es demostrar capacidades técnicas de desarrollo de software y explorar conceptos de inteligencia artificial aplicada a la salud.',
    ],
  },
  {
    id: 'origen-veracidad',
    numero: '2',
    titulo: 'Origen y Veracidad de la Información',
    icono: RiDatabaseLine,
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
    icono: RiRobot2Line,
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
    icono: RiStethoscopeLine,
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
    icono: RiLockPasswordLine,
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
    icono: RiCheckDoubleLine,
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
    icono: RiServerLine,
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
    icono: RiRefreshLine,
    contenido: [
      'Estos términos y condiciones pueden ser actualizados periódicamente. Es responsabilidad del usuario revisarlos antes de cada uso del sistema.',
    ],
  },
  {
    id: 'contacto-soporte',
    numero: '9',
    titulo: 'Contacto y Soporte',
    icono: RiCustomerService2Line,
    contenido: [
      'Para cualquier duda, comentario o reporte de fallos, el usuario puede ponerse en contacto con los desarrolladores a través de los canales habilitados dentro de la plataforma.',
    ],
  },
];

/**
 * Terminos — Página de Términos y Condiciones de Uso del sistema MedRec.
 *
 * Muestra las directrices legales, propósito académico, limitaciones del asistente virtual
 * y manejo de privacidad con coherencia visual al resto de la plataforma.
 *
 * @returns {React.JSX.Element} Componente de la página de Términos y Condiciones.
 */
export default function Terminos() {
  return (
    <PageWrapper name="terminos" className="relative">
      <BubbleBackground />
      <Navbar />

      <main className="relative z-10 mx-auto max-w-4xl px-4 pb-16 pt-24 sm:px-6 lg:px-8">
        {/* Encabezado Principal */}
        <header className="glass-card mb-8 p-6 sm:p-10 text-center relative overflow-hidden border border-white/10 dark:border-white/10 shadow-xl">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-royalBlue-600/20 text-royalBlue-500 dark:text-royalBlue-400 border border-royalBlue-500/30 shadow-inner mb-4">
            <RiShieldCheckLine className="text-3xl" />
          </div>

          <h1 className="text-3xl sm:text-4xl font-bold font-secondary tracking-tight">
            Términos y Condiciones de Uso
          </h1>

          <p
            className="mt-3 text-sm sm:text-base max-w-2xl mx-auto leading-relaxed"
            style={{ color: 'var(--text-muted)' }}
          >
            Consulta las condiciones generales que regulan el acceso, el uso ético y las limitaciones
            técnicas de la plataforma académica MedRec y su asistente de inteligencia artificial.
          </p>
        </header>

        {/* Secciones de Contenido */}
        <div className="flex flex-col gap-6">
          {SECCIONES_TERMINOS.map((seccion) => {
            const IconoSeccion = seccion.icono;
            return (
              <section
                key={seccion.id}
                id={seccion.id}
                className="glass-card p-6 sm:p-8 transition-all duration-300 hover:border-royalBlue-500/40 border border-transparent"
              >
                <div className="flex items-start gap-4 mb-4">
                  <div className="flex-shrink-0 flex h-11 w-11 items-center justify-center rounded-xl bg-royalBlue-600/10 dark:bg-royalBlue-500/20 text-royalBlue-600 dark:text-royalBlue-400 font-semibold text-base border border-royalBlue-500/20">
                    <IconoSeccion className="text-xl" />
                  </div>
                  <div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-royalBlue-500 dark:text-royalBlue-400">
                      Sección {seccion.numero}
                    </span>
                    <h2 className="text-xl sm:text-2xl font-semibold mt-0.5">
                      {seccion.titulo}
                    </h2>
                  </div>
                </div>

                <div className="space-y-3 pl-0 sm:pl-15 text-sm sm:text-base leading-relaxed">
                  {seccion.contenido && seccion.contenido.map((parrafo, idx) => (
                    <p key={idx} className="leading-relaxed">
                      {parrafo}
                    </p>
                  ))}

                  {seccion.puntos && (
                    <ul className="list-disc list-inside space-y-2 mt-3 pl-2" style={{ color: 'var(--text-muted)' }}>
                      {seccion.puntos.map((punto, idx) => (
                        <li key={idx} className="leading-relaxed">
                          <span className="text-slate-800 dark:text-slate-200">{punto}</span>
                        </li>
                      ))}
                    </ul>
                  )}

                  {seccion.subcontenido && (
                    <p className="mt-4 font-medium pt-2 text-slate-800 dark:text-slate-200">
                      {seccion.subcontenido}
                    </p>
                  )}

                  {seccion.subpuntos && (
                    <ul className="list-disc list-inside space-y-2 mt-2 pl-2" style={{ color: 'var(--text-muted)' }}>
                      {seccion.subpuntos.map((subpunto, idx) => (
                        <li key={idx} className="leading-relaxed">
                          <span className="text-slate-800 dark:text-slate-200">{subpunto}</span>
                        </li>
                      ))}
                    </ul>
                  )}

                  {seccion.conclusion && (
                    <p className="mt-4 pt-2 border-t border-black/5 dark:border-white/5 font-medium text-slate-800 dark:text-slate-200">
                      {seccion.conclusion}
                    </p>
                  )}
                </div>
              </section>
            );
          })}
        </div>

        {/* Pie de página con versión y fecha */}
        <footer className="mt-12 text-center text-xs sm:text-sm pt-6 border-t border-black/10 dark:border-white/10" style={{ color: 'var(--text-muted)' }}>
          <p className="font-medium">
            Última actualización: julio de 2026
          </p>
          <p className="mt-1 text-xs">
            Plataforma MedRec — Desarrollo exclusivo para fines académicos y educativos.
          </p>
        </footer>
      </main>

      <Footer />
    </PageWrapper>
  );
}
