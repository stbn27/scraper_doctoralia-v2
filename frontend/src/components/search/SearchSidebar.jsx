import React, { useState } from 'react';
import { RiChat3Line, RiSearchLine } from 'react-icons/ri';

import { ChatPanel } from '@/components/shared/ChatPanel';
import { TraditionalSearchForm } from '@/components/search/TraditionalSearchForm';

export function SearchSidebar({
    filters,
    onFiltersChange,
    onSearch,
    onClear,
    onChatDetected,
    specialties,
    cities,
    catalogsLoading,
}) {
    const [mode, setMode] = useState('traditional');

    const isChatMode = mode === 'chat';

    return (
        // ${isChatMode ? 'w-full lg:w-[430px]' : 'w-full lg:w-[320px]'}
        <aside
            className={`glass-card shrink-0 overflow-hidden transition-all duration-300 ease-out lg:sticky lg:top-24 lg:self-start w-full lg:w-80`}
        >
            <div className="border-b border-black/10 p-4 dark:border-white/10">

                <p className="mt-1 text-sm" style={{ color: 'var(--text-muted)' }}>
                    Encuentra especialistas según tu necesidad médica.
                </p>

                <div className="mt-4 grid grid-cols-2 gap-2 rounded-2xl bg-black/5 p-1 dark:bg-white/5">
                    <button
                        type="button"
                        onClick={() => setMode('traditional')}
                        className={`flex items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition-all ${mode === 'traditional'
                            ? 'bg-royalBlue-600 text-white shadow-lg'
                            : 'hover:bg-black/10 dark:hover:bg-white/10'
                            }`}
                    >
                        <RiSearchLine />
                        Tradicional
                    </button>

                    <button
                        type="button"
                        onClick={() => setMode('chat')}
                        className={`flex items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition-all ${mode === 'chat'
                            ? 'bg-royalBlue-600 text-white shadow-lg'
                            : 'hover:bg-black/10 dark:hover:bg-white/10'
                            }`}
                    >
                        <RiChat3Line />
                        Chat
                    </button>
                </div>
            </div>

            <div className="relative">
                {isChatMode ? (
                    <div className="h-[620px]">
                        {<ChatPanel
                            compact
                            onDetectedChange={onChatDetected}
                        />}
                    </div>
                ) : (
                    <div className="p-4">
                        <TraditionalSearchForm
                            filters={filters}
                            onFiltersChange={onFiltersChange}
                            onSearch={onSearch}
                            onClear={onClear}
                            specialties={specialties}
                            cities={cities}
                            catalogsLoading={catalogsLoading}
                        />
                    </div>
                )}
            </div>
        </aside>
    );
}