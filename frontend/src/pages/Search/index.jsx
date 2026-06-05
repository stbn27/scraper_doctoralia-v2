import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
    RiSearchLine,
    RiRobot2Line,
    RiEmotionSadLine,
} from 'react-icons/ri';

import { PageWrapper } from '@/components/layout/PageWrapper';
import { BubbleBackground } from '@/components/layout/BubbleBackground';
import { Navbar } from '@/components/layout/Navbar';
import { SearchSidebar } from '@/components/search/SearchSidebar';
import { SpecialistCard } from '@/components/shared/SpecialistCard';
import { SkeletonCard } from '@/components/ui/SkeletonCard';
import { Button } from '@/components/ui/Button';
import { useToast } from '@/hooks/useToast';
import { searchSpecialists } from '@/services/api';
import img1 from '@/assets/doctors/doctor1.svg';

function createInitialFilters(searchParams) {
    return {
        especialidad: searchParams.get('especialidad') || searchParams.get('q') || '',
        ciudad: searchParams.get('ciudad') || '',
        atiendeNinos: false,
        atiendeAdultos: false,
        atiendeAdolescentes: false,
        orden: searchParams.get('orden') || 'puntuacion',
        soloAnalizados: searchParams.get('solo_analizados') === 'true',
        confiabilidad: searchParams.get('confiabilidad') || '',
    };
}

function hasSearchIntent(filters) {
    return Boolean(
        filters.especialidad ||
        filters.ciudad ||
        filters.atiendeNinos ||
        filters.atiendeAdultos ||
        filters.atiendeAdolescentes ||
        filters.confiabilidad ||
        filters.soloAnalizados
    );
}

function normalizeApiResults(response) {
    if (Array.isArray(response)) {
        return response;
    }

    if (Array.isArray(response?.results)) {
        return response.results;
    }

    if (Array.isArray(response?.especialistas)) {
        return response.especialistas;
    }

    if (Array.isArray(response?.favoritos)) {
        return response.favoritos;
    }

    return [];
}

function getSpecialistId(specialist) {
    return specialist.doctoralia_id || specialist._id || specialist.id;
}

/**
 * Search — Vista principal de búsqueda de especialistas.
 *
 * Esta pantalla permite:
 * - Buscar con filtros tradicionales.
 * - Buscar usando el chat médico.
 * - Mostrar resultados filtrados.
 * - Evitar cargar todos los especialistas cuando no hay intención de búsqueda.
 */
export default function Search() {
    const [searchParams, setSearchParams] = useSearchParams();
    const { addToast } = useToast();

    const [filters, setFilters] = useState(() => createInitialFilters(searchParams));
    const [specialists, setSpecialists] = useState([]);
    const [loading, setLoading] = useState(false);
    const [hasSearched, setHasSearched] = useState(false);

    const updateUrlParams = useCallback(
        (nextFilters) => {
            const params = new URLSearchParams();

            if (nextFilters.especialidad) {
                params.set('especialidad', nextFilters.especialidad);
            }

            if (nextFilters.ciudad) {
                params.set('ciudad', nextFilters.ciudad);
            }

            if (nextFilters.orden) {
                params.set('orden', nextFilters.orden);
            }

            if (nextFilters.soloAnalizados) {
                params.set('solo_analizados', 'true');
            }

            if (nextFilters.confiabilidad) {
                params.set('confiabilidad', nextFilters.confiabilidad);
            }

            setSearchParams(params);
        },
        [setSearchParams]
    );

    const doSearch = useCallback(
        async (nextFilters) => {
            if (!hasSearchIntent(nextFilters)) {
                setSpecialists([]);
                setLoading(false);
                setHasSearched(false);
                return;
            }

            setLoading(true);
            setHasSearched(true);

            try {
                const response = await searchSpecialists(nextFilters);
                const results = normalizeApiResults(response);

                setSpecialists(results);
                updateUrlParams(nextFilters);
            } catch (error) {
                console.error('Error al buscar especialistas:', error);

                addToast({
                    type: 'error',
                    message: 'Error al cargar especialistas.',
                });

                setSpecialists([]);
            } finally {
                setLoading(false);
            }
        },
        [addToast, updateUrlParams]
    );

    const applyFilters = useCallback(() => {
        doSearch(filters);
    }, [doSearch, filters]);

    const clearFilters = useCallback(() => {
        const clearedFilters = {
            especialidad: '',
            ciudad: '',
            atiendeNinos: false,
            atiendeAdultos: false,
            atiendeAdolescentes: false,
            orden: 'puntuacion',
            soloAnalizados: false,
            confiabilidad: '',
        };

        setFilters(clearedFilters);
        setSpecialists([]);
        setLoading(false);
        setHasSearched(false);
        setSearchParams({});
    }, [setSearchParams]);

    const handleChatDetected = useCallback(
        (detectedData) => {
            const nextFilters = {
                ...filters,
                especialidad: detectedData?.especialidad ?? filters.especialidad,
                ciudad: detectedData?.ciudad ?? filters.ciudad,
            };

            setFilters(nextFilters);

            if (detectedData?.ready) {
                doSearch(nextFilters);
            }
        },
        [doSearch, filters]
    );

    const sortedSpecialists = useMemo(() => {
        return [...specialists].sort((a, b) => {
            switch (filters.orden) {
                case 'puntuacion':
                    return (
                        (b.puntuacion_recomendacion ?? b.score_recomendacion ?? 0) -
                        (a.puntuacion_recomendacion ?? a.score_recomendacion ?? 0)
                    );

                case 'rating':
                    return (b.rating_global ?? 0) - (a.rating_global ?? 0);

                case 'opiniones':
                    return (b.total_opiniones ?? 0) - (a.total_opiniones ?? 0);

                default:
                    return 0;
            }
        });
    }, [specialists, filters.orden]);

    useEffect(() => {
        const initialFilters = createInitialFilters(searchParams);

        setFilters(initialFilters);

        if (hasSearchIntent(initialFilters)) {
            doSearch(initialFilters);
        }
    }, []);

    const showInitialState = !loading && !hasSearched;
    const showEmptyState = !loading && hasSearched && sortedSpecialists.length === 0;
    const showResults = !loading && sortedSpecialists.length > 0;

    return (
        <PageWrapper name="search" className="relative">
            <BubbleBackground />
            <Navbar />

            <div className="relative z-10 mx-auto max-w-7xl px-4 pb-8 pt-20 sm:px-6 lg:px-8">
                <div className="flex flex-col gap-6 lg:flex-row">
                    <SearchSidebar
                        filters={filters}
                        onFiltersChange={setFilters}
                        onSearch={applyFilters}
                        onClear={clearFilters}
                        onChatDetected={handleChatDetected}
                    />

                    <main className="min-w-0 flex-1">
                        <section className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                            <div>
                                <h1 className="text-2xl font-semibold">
                                    Búsqueda de especialistas
                                </h1>

                                <p
                                    className="mt-1 text-sm"
                                    style={{ color: 'var(--text-muted)' }}
                                >
                                    Usa el chat o los filtros para encontrar especialistas médicos.
                                </p>
                            </div>

                            {hasSearched && (
                                <div
                                    className="rounded-full border border-black/10 px-4 py-2 text-sm dark:border-white/10"
                                    style={{ color: 'var(--text-muted)' }}
                                >
                                    {loading
                                        ? 'Buscando...'
                                        : `${sortedSpecialists.length} especialista${sortedSpecialists.length !== 1 ? 's' : ''
                                        } encontrado${sortedSpecialists.length !== 1 ? 's' : ''
                                        }`}
                                </div>
                            )}
                        </section>

                        {showInitialState && (
                            <InitialSearchState />
                        )}

                        {loading && (
                            <LoadingResults />
                        )}

                        {showResults && (
                            <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                                {sortedSpecialists.map((specialist) => (
                                    <SpecialistCard
                                        key={getSpecialistId(specialist)}
                                        specialist={specialist}
                                    />
                                ))}
                            </section>
                        )}

                        {showEmptyState && (
                            <EmptyResultsState onClear={clearFilters} />
                        )}
                    </main>
                </div>
            </div>
        </PageWrapper>
    );
}

function InitialSearchState() {
    return (
        <section className="glass-card overflow-hidden p-8 sm:p-10">
            <div className="mx-auto max-w-2xl text-center">
                <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-royalBlue-600 text-white shadow-lg shadow-royalBlue-600/30">
                    <RiRobot2Line className="text-3xl" />
                </div>

                <h2 className="mt-6 text-2xl font-semibold">
                    Encuentra especialistas recomendados
                </h2>

                <p
                    className="mt-3 text-sm leading-relaxed sm:text-base"
                    style={{ color: 'var(--text-muted)' }}
                >
                    Describe tu molestia en el chat o usa la búsqueda tradicional por
                    especialidad, ciudad y tipo de paciente. El sistema te ayudará a
                    encontrar médicos evaluados con base en opiniones y análisis de
                    recomendación.
                </p>

                <img
                    src={img1}
                    alt="Ilustración de búsqueda de especialistas"
                    className="mx-auto mt-6 max-h-64 object-contain"
                />

                <div className="mt-6 flex flex-wrap justify-center gap-2">
                    <SuggestionChip text="Dolor de muela" />
                    <SuggestionChip text="Dermatólogo en CDMX" />
                    <SuggestionChip text="Cardiólogo" />
                    <SuggestionChip text="Especialista para niños" />
                </div>
            </div>
        </section>
    );
}

function SuggestionChip({ text }) {
    return (
        <span className="rounded-full border border-royalBlue-400/60 px-4 py-1.5 text-sm text-royalBlue-500 dark:text-royalBlue-300">
            {text}
        </span>
    );
}

function LoadingResults() {
    return (
        <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 6 }).map((_, index) => (
                <SkeletonCard key={index} />
            ))}
        </section>
    );
}

function EmptyResultsState({ onClear }) {
    return (
        <section className="glass-card p-10 text-center">
            <RiEmotionSadLine
                className="mx-auto mb-4 text-5xl"
                style={{ color: 'var(--text-muted)' }}
            />

            <h2 className="text-xl font-semibold">
                No encontramos especialistas para tu búsqueda.
            </h2>

            <p
                className="mx-auto mt-2 max-w-md text-sm"
                style={{ color: 'var(--text-muted)' }}
            >
                Intenta modificar la especialidad, ciudad o los filtros de análisis.
            </p>

            <div className="mt-6 flex justify-center">
                <Button variant="outline" onClick={onClear}>
                    <RiSearchLine />
                    Nueva búsqueda
                </Button>
            </div>
        </section>
    );
}