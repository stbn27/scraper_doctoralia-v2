import React, { useCallback, useEffect, useState } from 'react';
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
import { useAuth } from '@/hooks/useAuth';
import { searchSpecialists, guardarBusquedaHistorial } from '@/services/api';
import { useCatalogs } from '@/hooks/useCatalogs';
import img1 from '@/assets/doctors/doctor1.svg';

const DEFAULT_FILTERS = {
    especialidad: '',
    ciudad: '',
    tipoPaciente: 'todos',
    orden: 'puntuacion_desc',
    confiabilidad: '',
    soloAnalizados: false,
    page: 1,
    limit: 12,
};

function createInitialFilters(searchParams) {
    return {
        especialidad: searchParams.get('especialidad') || searchParams.get('q') || '',
        ciudad: searchParams.get('ciudad') || '',
        tipoPaciente: searchParams.get('tipoPaciente') || 'todos',
        orden: searchParams.get('orden') || 'puntuacion_desc',
        soloAnalizados: searchParams.get('solo_analizados') === 'true',
        confiabilidad: searchParams.get('confiabilidad') || '',
        page: Number(searchParams.get('page')) || 1,
        limit: Number(searchParams.get('limit')) || 12,
    };
}

function hasSearchIntent(filters) {
    return Boolean(
        filters.especialidad ||
        filters.ciudad ||
        (filters.tipoPaciente && filters.tipoPaciente !== 'todos') ||
        filters.confiabilidad ||
        filters.soloAnalizados
    );
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
    const { user } = useAuth();
    const { specialties, cities, loading: catalogsLoading } = useCatalogs();

    const [filters, setFilters] = useState(() => createInitialFilters(searchParams));
    const [specialists, setSpecialists] = useState([]);
    const [loading, setLoading] = useState(false);
    const [hasSearched, setHasSearched] = useState(false);
    const [pagination, setPagination] = useState({ total: 0, page: 1, limit: 12, pages: 0 });

    const updateUrlParams = useCallback(
        (nextFilters) => {
            const params = new URLSearchParams();

            if (nextFilters.especialidad) {
                params.set('especialidad', nextFilters.especialidad);
            }

            if (nextFilters.ciudad) {
                params.set('ciudad', nextFilters.ciudad);
            }

            if (nextFilters.tipoPaciente && nextFilters.tipoPaciente !== 'todos') {
                params.set('tipoPaciente', nextFilters.tipoPaciente);
            }

            if (nextFilters.orden && nextFilters.orden !== 'puntuacion_desc') {
                params.set('orden', nextFilters.orden);
            }

            if (nextFilters.soloAnalizados) {
                params.set('solo_analizados', 'true');
            }

            if (nextFilters.confiabilidad) {
                params.set('confiabilidad', nextFilters.confiabilidad);
            }

            if (nextFilters.page && nextFilters.page > 1) {
                params.set('page', String(nextFilters.page));
            }

            setSearchParams(params, { replace: true });
        },
        [setSearchParams]
    );

    const doSearch = useCallback(
        async (nextFilters) => {
            if (!hasSearchIntent(nextFilters)) {
                setSpecialists([]);
                setPagination({ total: 0, page: 1, limit: 12, pages: 0 });
                setLoading(false);
                setHasSearched(false);
                return;
            }

            setLoading(true);
            setHasSearched(true);

            try {
                const response = await searchSpecialists(nextFilters);

                console.log('[Search] Respuesta del backend:', response);

                setSpecialists(response.results);
                setPagination({
                    total: response.total,
                    page: response.page,
                    limit: response.limit,
                    pages: response.pages,
                });
                updateUrlParams(nextFilters);

                if (user) {
                    try {
                        await guardarBusquedaHistorial({
                            especialidad: nextFilters.especialidad || null,
                            ubicacion: nextFilters.ciudad || null,
                            consulta_texto: null,
                            filtros: {
                                especialidad: nextFilters.especialidad || null,
                                ciudad: nextFilters.ciudad || null,
                                orden: nextFilters.orden || 'puntuacion_desc',
                                solo_analizados: nextFilters.soloAnalizados || false,
                                confiabilidad: nextFilters.confiabilidad || null,
                            },
                            origen: 'tradicional',
                            total_resultados: response.total
                        });
                    } catch (historyErr) {
                        console.error('[Search] Error guardando historial:', historyErr);
                    }
                }
            } catch (error) {
                console.error('Error al buscar especialistas:', error);

                addToast({
                    type: 'error',
                    message: 'Error al cargar especialistas.',
                });

                setSpecialists([]);
                setPagination({ total: 0, page: 1, limit: 12, pages: 0 });
            } finally {
                setLoading(false);
            }
        },
        [addToast, updateUrlParams, user]
    );

    const applyFilters = useCallback(() => {
        doSearch({ ...filters, page: 1 });
    }, [doSearch, filters]);

    const handlePageChange = useCallback((newPage) => {
        if (newPage < 1 || newPage > pagination.pages) return;
        const updated = { ...filters, page: newPage };
        setFilters(updated);
        doSearch(updated);
    }, [filters, pagination.pages, doSearch]);

    const clearFilters = useCallback(() => {
        setFilters(DEFAULT_FILTERS);
        setSpecialists([]);
        setPagination({ total: 0, page: 1, limit: 12, pages: 0 });
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

    // El backend ya ordena, no necesitamos sort local.
    // Pero mantenemos la referencia para que el resto del código funcione.
    const sortedSpecialists = specialists;

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

    const renderPagination = () => {
        const { page, pages } = pagination;
        if (pages <= 1) return null;

        const pageNumbers = [];
        const maxVisible = 5;
        let startPage = Math.max(1, page - 2);
        let endPage = Math.min(pages, startPage + maxVisible - 1);

        if (endPage - startPage + 1 < maxVisible) {
            startPage = Math.max(1, endPage - maxVisible + 1);
        }

        for (let i = startPage; i <= endPage; i++) {
            pageNumbers.push(i);
        }

        return (
            <div className="mt-8 flex items-center justify-center gap-1.5 flex-wrap">
                <Button
                    variant="outline"
                    onClick={() => handlePageChange(page - 1)}
                    disabled={page === 1}
                    className="px-3 py-1.5 text-xs rounded-xl"
                >
                    Anterior
                </Button>

                {startPage > 1 && (
                    <>
                        <button
                            onClick={() => handlePageChange(1)}
                            className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-colors ${page === 1
                                    ? 'bg-royalBlue-600 text-white'
                                    : 'hover:bg-white/10 text-slate-300'
                                }`}
                        >
                            1
                        </button>
                        {startPage > 2 && <span className="text-slate-500 text-xs px-1 select-none">...</span>}
                    </>
                )}

                {pageNumbers.map(num => (
                    <button
                        key={num}
                        onClick={() => handlePageChange(num)}
                        className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-colors ${page === num
                                ? 'bg-royalBlue-600 text-white'
                                : 'hover:bg-white/10 text-slate-300'
                            }`}
                    >
                        {num}
                    </button>
                ))}

                {endPage < pages && (
                    <>
                        {endPage < pages - 1 && <span className="text-slate-500 text-xs px-1 select-none">...</span>}
                        <button
                            onClick={() => handlePageChange(pages)}
                            className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-colors ${page === pages
                                    ? 'bg-royalBlue-600 text-white'
                                    : 'hover:bg-white/10 text-slate-300'
                                }`}
                        >
                            {pages}
                        </button>
                    </>
                )}

                <Button
                    variant="outline"
                    onClick={() => handlePageChange(page + 1)}
                    disabled={page === pages}
                    className="px-3 py-1.5 text-xs rounded-xl"
                >
                    Siguiente
                </Button>
            </div>
        );
    };

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
                        specialties={specialties}
                        cities={cities}
                        catalogsLoading={catalogsLoading}
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
                                        : `${pagination.total} especialista${pagination.total !== 1 ? 's' : ''
                                        } encontrado${pagination.total !== 1 ? 's' : ''
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
                            <>
                                <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
                                    {sortedSpecialists.map((specialist, idx) => (
                                        <SpecialistCard
                                            key={getSpecialistId(specialist)}
                                            specialist={specialist}
                                            index={idx}
                                        />
                                    ))}
                                </section>
                                {renderPagination()}
                            </>
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