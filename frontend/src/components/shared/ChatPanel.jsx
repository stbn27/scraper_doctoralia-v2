import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { RiRobot2Line, RiSendPlaneLine, RiSearchLine, RiMapPinLine } from 'react-icons/ri';
import { Button } from '@/components/ui/Button';
import { chatMessage } from '@/services/api';

const INITIAL_MESSAGE = {
        role: 'assistant',
        content:
                '¡Hola! Soy tu asistente médico. Cuéntame: ¿qué molestia tienes o qué tipo de especialista estás buscando?',
};

export function ChatPanel({ className = '', compact = false, onDetectedChange }) {
        const navigate = useNavigate();
        const [messages, setMessages] = useState([INITIAL_MESSAGE]);
        const [input, setInput] = useState('');
        const [isTyping, setIsTyping] = useState(false);
        const [detectedData, setDetectedData] = useState({ especialidad: null, ciudad: null, ready: false });
        const [currentSuggestions, setCurrentSuggestions] = useState(['Dentista', 'Cardiólogo', 'Dermatólogo', 'Ortopedista']);
        const [showLocationBtn, setShowLocationBtn] = useState(false);
        const [userLocations, setUserLocations] = useState([]);
        const messagesEndRef = useRef(null);
        const textareaRef = useRef(null);
        const scrollContainerRef = useRef(null);
        const detectedDataRef = useRef(detectedData);

        useEffect(() => {
                detectedDataRef.current = detectedData;
        }, [detectedData]);

        const scrollToBottom = useCallback(() => {
                if (scrollContainerRef.current) {
                        scrollContainerRef.current.scrollTo({
                                top: scrollContainerRef.current.scrollHeight,
                                behavior: 'smooth'
                        });
                }
        }, []);

        useEffect(() => {
                scrollToBottom();
        }, [messages, isTyping, scrollToBottom]);

        useEffect(() => {
                if (!isTyping) {
                        textareaRef.current?.focus();
                }
        }, [isTyping]);

        const sendMessage = useCallback(
                async (text) => {
                        if (!text.trim() || isTyping) return;

                        const userMsg = { role: 'user', content: text.trim() };
                        const newHistory = [...messages, userMsg];
                        setMessages(newHistory);
                        setInput('');
                        setUserLocations([]);
                        setIsTyping(true);

                        if (textareaRef.current) textareaRef.current.style.height = 'auto';

                        try {
                                const response = await chatMessage(newHistory);

                                const responseMessages = (response.respuesta && response.respuesta.length > 0)
                                        ? response.respuesta.map(msg => ({ role: 'assistant', content: msg }))
                                        : [{ role: 'assistant', content: response.content }];

                                setMessages((prev) => [...prev, ...responseMessages]);

                                if (response.suggestions && response.suggestions.length > 0) {
                                        setCurrentSuggestions(response.suggestions);
                                }

                                if (response.ubicaciones_usuario && response.ubicaciones_usuario.length > 0) {
                                        setUserLocations(response.ubicaciones_usuario);
                                } else {
                                        setUserLocations([]);
                                }

                                if (response.sql && (response.sql.includes('UBICACION_USUARIO') || response.sql.includes('LOCATION_USER'))) {
                                        setShowLocationBtn(true);
                                } else {
                                        setShowLocationBtn(false);
                                }

                                const rawCiudad = response?.ciudad ?? detectedDataRef.current.ciudad;
                                const cleanCiudad = rawCiudad ? rawCiudad.split(',')[0].trim() : null;

                                const next = {
                                        especialidad: response?.especialidad ?? detectedDataRef.current.especialidad,
                                        ciudad: cleanCiudad,
                                        ready: Boolean(response?.ready || detectedDataRef.current.ready),
                                };
                                setDetectedData(next);
                                onDetectedChange?.(next);
                        } catch (error) {
                                setMessages((prev) => [
                                        ...prev,
                                        { role: 'assistant', content: 'Lo siento, hubo un error. ¿Puedes intentar de nuevo?' },
                                ]);
                        } finally {
                                setIsTyping(false);
                        }
                },
                [isTyping, messages, onDetectedChange]
        );

        const handleKeyDown = (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        sendMessage(input);
                }
        };

        const handleTextareaInput = (e) => {
                setInput(e.target.value);
                e.target.style.height = 'auto';
                e.target.style.height = Math.min(e.target.scrollHeight, 80) + 'px';
        };

        const showChips = currentSuggestions && currentSuggestions.length > 0 && !detectedData.especialidad;

        return (
                <div className={`flex h-full min-h-0 flex-col ${className}`}>
                        <div className="flex items-center justify-between p-4 border-b border-black/10 dark:border-white/10 shrink-0">
                                <div className="flex items-center gap-3">
                                        <div className="w-9 h-9 rounded-lg bg-royalBlue-700 flex items-center justify-center">
                                                <RiRobot2Line className="text-sm text-royalBlue-300" />
                                        </div>
                                        <div>
                                                <h1 className="text-base font-semibold">MedRec</h1>
                                                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                                                        Asistente de búsqueda médica
                                                </p>
                                        </div>
                                </div>
                                <div className="flex items-center gap-2">
                                        <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse-dot" />
                                        <span className="text-xs text-emerald-400">En línea</span>
                                </div>
                        </div>

                        <div
                                ref={scrollContainerRef}
                                className={`flex-1 min-h-0 overflow-y-auto ${compact ? 'p-3 space-y-3' : 'p-4 space-y-4'}`}
                        >
                                {messages.map((msg, i) => (
                                        <MessageBubble key={i} message={msg} />
                                ))}

                                {isTyping && (
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

                                {detectedData.ready && !isTyping && (
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
                                                                        if (detectedData.especialidad) params.set('especialidad', detectedData.especialidad);
                                                                        if (detectedData.ciudad) {
                                                                                const firstPart = detectedData.ciudad.split(',')[0].trim();
                                                                                params.set('ciudad', firstPart);
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

                                <div ref={messagesEndRef} />
                        </div>

                        {showChips && (
                                <div className="px-4 pb-2 shrink-0 flex flex-wrap gap-2">
                                        {currentSuggestions.map((chip, idx) => (
                                                <button
                                                        key={`${chip}-${idx}`}
                                                        onClick={() => sendMessage(chip)}
                                                        className="border border-royalBlue-400/80 dark:border-royalBlue-400/50 text-royalBlue-500 dark:text-royalBlue-300 rounded-full px-3 py-1 text-xs hover:bg-royalBlue-600/20 transition-all duration-200 hover:scale-105 press-effect"
                                                >
                                                        {chip}
                                                </button>
                                        ))}
                                </div>
                        )}

                        {userLocations && userLocations.length > 0 && !isTyping && (
                                <div className="px-4 pb-4 shrink-0 flex flex-col gap-3 w-full">
                                        {userLocations.slice(0, 3).map((loc, idx) => (
                                                <button
                                                        key={`user-loc-${idx}`}
                                                        onClick={() => {
                                                                sendMessage(`Mi ubicación es ${loc}`);
                                                                setUserLocations([]);
                                                        }}
                                                        className="w-full bg-royalBlue-900/60 hover:bg-royalBlue-800/80 text-neutral-light/90 border border-royalBlue-500/30 rounded-xl px-4 py-3 transition-all duration-200 flex flex-col items-start press-effect backdrop-blur-sm shadow-sm"
                                                >
                                                        <span className="text-sm font-semibold leading-tight flex items-center gap-2 mb-1">
                                                                <RiMapPinLine className="text-royalBlue-300" />
                                                                Usar mi ubicación registrada
                                                        </span>
                                                        <span className="text-xs opacity-75 leading-tight">{loc}</span>
                                                </button>
                                        ))}
                                </div>
                        )}

                        {showLocationBtn && (!userLocations || userLocations.length === 0) && !isTyping && (
                                <div className="px-4 pb-2 shrink-0 flex">
                                        <button
                                                onClick={() => {
                                                        const user = localStorage.getItem('medrec_user');
                                                        let userCity = null;
                                                        if (user) {
                                                                try {
                                                                        const parsed = JSON.parse(user);
                                                                        userCity = parsed?.direccion_principal?.ciudad || parsed?.direccion_principal?.estado;
                                                                } catch (e) { }
                                                        }
                                                        if (userCity) {
                                                                sendMessage(`Mi ubicación es ${userCity}`);
                                                        } else {
                                                                setMessages(prev => [...prev, { role: 'assistant', content: 'No pude encontrar una ubicación en tu perfil. ¿Puedes escribirla por favor?' }]);
                                                        }
                                                        setShowLocationBtn(false);
                                                }}
                                                className="bg-royalBlue-600 text-white rounded-full px-4 py-1.5 text-xs hover:bg-royalBlue-700 transition-all duration-200 flex items-center gap-1 press-effect"
                                        >
                                                <RiSearchLine className="text-xs" />
                                                Usar mi ubicación registrada
                                        </button>
                                </div>
                        )}

                        <div className="p-4 border-t border-white/10 shrink-0">
                                <div className="flex items-end gap-2">
                                        <textarea
                                                ref={textareaRef}
                                                value={input}
                                                onChange={handleTextareaInput}
                                                onKeyDown={handleKeyDown}
                                                placeholder="Escribe tu mensaje…"
                                                rows={1}
                                                className="glass-input flex-1 px-4 py-2.5 text-sm resize-none"
                                                style={{ maxHeight: '80px' }}
                                        />
                                        <button
                                                onClick={() => sendMessage(input)}
                                                disabled={!input.trim() || isTyping}
                                                className="p-2.5 rounded-xl bg-royalBlue-600 hover:bg-royalBlue-700 text-white transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed press-effect"
                                                aria-label="Enviar mensaje"
                                        >
                                                <RiSendPlaneLine className="text-xl" />
                                        </button>
                                </div>
                        </div>
                </div>
        );
}

function MessageBubble({ message }) {
        const isAssistant = message.role === 'assistant';

        return (
                <div className={`flex items-end gap-2 ${isAssistant ? '' : 'flex-row-reverse'}`}>
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${isAssistant ? 'bg-royalBlue-700' : 'bg-royalBlue-700/90'}`}>
                                {isAssistant ? (
                                        <RiRobot2Line className="text-sm text-royalBlue-300" />
                                ) : (
                                        <span className="text-xs font-semibold text-white">Tú</span>
                                )}
                        </div>

                        <div className={`max-w-[80%] px-4 py-2.5 text-sm leading-relaxed backdrop-blur ${isAssistant ? 'glass-card-chat' : 'bg-royalBlue-700/80 text-white dark:bg-royalBlue-600/80 rounded-2xl rounded-tr-none'}`}>
                                {message.content}
                        </div>
                </div>
        );
}

export default ChatPanel;
