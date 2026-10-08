"use strict";
(() => {
    const key = 'localauthor.appearance';
    const choices = new Set(['system', 'light', 'dark']);
    const system = matchMedia('(prefers-color-scheme: dark)');
    let choice = 'system';
    try {
        const saved = localStorage.getItem(key);
        if (choices.has(saved)) choice = saved;
    } catch { /* A blocked preference store must not prevent opening the UI. */ }
    function render() {
        document.documentElement.dataset.theme = choice === 'system' ? (system.matches ? 'dark' : 'light') : choice;
        for (const input of document.querySelectorAll('[data-appearance]')) input.value = choice;
    }
    for (const input of document.querySelectorAll('[data-appearance]')) {
        input.addEventListener('change', () => {
            if (!choices.has(input.value)) return;
            choice = input.value;
            try { localStorage.setItem(key, choice); } catch { /* Keep the selected theme for this page. */ }
            render();
        });
    }
    system.addEventListener('change', render);
    render();
})();
