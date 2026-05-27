import { useEffect, useRef } from 'react';

/**
 * Hook que observa elementos con la clase 'scroll-reveal' y les añade
 * la clase 'visible' cuando entran al viewport.
 * Usa IntersectionObserver para un scroll-trigger eficiente.
 * @param {{ threshold?: number, rootMargin?: string }} options
 * @example
 * useScrollTrigger(); // Aplica automáticamente al montar el componente
 * // En el JSX: <div className="scroll-reveal">...</div>
 */
export function useScrollTrigger(options = {}) {
  const observerRef = useRef(null);

  useEffect(() => {
    const { threshold = 0.1, rootMargin = '0px 0px -50px 0px' } = options;

    observerRef.current = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observerRef.current?.unobserve(entry.target);
          }
        });
      },
      { threshold, rootMargin }
    );

    const elements = document.querySelectorAll('.scroll-reveal');
    elements.forEach((el) => observerRef.current?.observe(el));

    return () => {
      observerRef.current?.disconnect();
    };
  }, []);
}
