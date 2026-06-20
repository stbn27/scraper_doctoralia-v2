import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { BubbleBackground } from '@/components/layout/BubbleBackground';
import { PageWrapper } from '@/components/layout/PageWrapper';
import ChatPanel from '@/components/shared/ChatPanel';
import InlineLogin from '@/components/shared/InlineLogin';

/** Mensaje inicial del asistente */
const INITIAL_MESSAGE = {
  role: 'assistant',
  content: '¡Hola! Soy tu asistente médico. Cuéntame: ¿qué molestia tienes o qué tipo de especialista estás buscando?',
};

/** Chips de sugerencias rápidas */
const QUICK_CHIPS = ['Dentista', 'Cardiólogo', 'Dermatólogo', 'Ortopedista'];

/**
 * Home — Pantalla de chatbot conversacional multi-turno.
 * Detecta especialidad y ciudad para redirigir a resultados.
 */
export default function Home() {
  const navigate = useNavigate();
  const [viewMode, setViewMode] = useState('login'); // 'chat' | 'login'

  return (
    <PageWrapper name="home" className="relative">
      <BubbleBackground />

      <div className="relative z-10 min-h-screen flex items-center justify-center gap-5 p-4 overflow-hidden">

        {/* CHAT */}
        <div className="order-2 w-full max-w-[700px]">
          <div className="glass-card relative h-[85vh] min-h-[640px] overflow-hidden">
            <div
              className={`absolute inset-0 transition-all duration-300 ease-out ${viewMode === 'chat' ? 'opacity-100 translate-y-0 pointer-events-auto' : 'opacity-0 translate-y-4 pointer-events-none'}`}
            >
              <ChatPanel className="h-full" compact={false} />
            </div>

            <div
              className={`absolute inset-0 flex items-center justify-center p-6 transition-all duration-300 ease-out ${viewMode === 'login' ? 'opacity-100 translate-y-0 pointer-events-auto' : 'opacity-0 -translate-y-4 pointer-events-none'}`}
            >
              <InlineLogin onSuccess={() => navigate('/busqueda')} />
            </div>
          </div>
        </div>

        {/* PRESENTACION */}
        <div className="flex-1 order-1 justify-center p-6 hidden md:flex flex-col items-center w-full max-w-[600px] gap-4">

          <h1 className='font-secondary text-5xl font-bold'>
            Bienvenido a <span className="text-royalBlue-500">MedRec</span>
          </h1>

          <p className='text-2xl'>Cuentanos que tienes y te podemos recomendar a los mejores especialistas médicos, cerca de tu <span className="text-royalBlue-500">zona</span></p>
          <p className='text-2xl'>O si prefieres, inicia sesión para poder guardar tus preferencias y recibir recomendaciones personalizadas.</p>
          <button
            // onClick={() => setViewMode((v) => (v === 'chat' ? 'login' : 'chat'))}
            onClick={() => navigate('/busqueda')}
            aria-label="Iniciar sesión"
            className="self-start bg-royalBlue-600 dark:bg-royalBlue-950/30 hover:bg-royalBlue-700 dark:hover:bg-royalBlue-900/30 text-white py-2 px-8 rounded-2xl transition-colors duration-200 text-lg press-effect backdrop-blur-md border border-royalBlue-500/60 dark:border-royalBlue-950/30 shadow-lg shadow-black/10">
            {/* {viewMode === 'chat' ? 'Iniciar sesión' : 'Busca especialista'} */}
            Busca especialista
          </button>
        </div>

      </div>
    </PageWrapper>
  );
}
