(() => {
    const tapCards = document.querySelectorAll('[data-tap-nav]');
    if (!tapCards.length) return;

    const isCoarsePointer = window.matchMedia('(pointer: coarse)').matches;
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const navDelayMs = prefersReduced ? 0 : 130;

    tapCards.forEach((card) => {
        const reset = () => {
            card.classList.remove('is-pressed');
        };

        card.addEventListener('pointerdown', () => {
            card.classList.add('is-pressed');
        });

        card.addEventListener('pointerup', reset);
        card.addEventListener('pointercancel', reset);
        card.addEventListener('pointerleave', reset);

        card.addEventListener('click', (event) => {
            if (!isCoarsePointer) return;

            const href = card.getAttribute('href');
            if (!href) return;

            event.preventDefault();
            card.classList.add('is-pressed');
            card.classList.add('is-loading');

            setTimeout(() => {
                window.location.href = href;
            }, navDelayMs);
        });
    });
})();
