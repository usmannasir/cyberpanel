/**
 * CyberPanel theme toggle (v2.4.8+ shell). Syncs data-theme, helper classes, and shell repaint.
 */
(function (global) {
    'use strict';

    function normalizeTheme(value) {
        return value === 'dark' ? 'dark' : 'light';
    }

    function readStoredTheme() {
        try {
            return normalizeTheme(global.localStorage.getItem('cyberPanelTheme'));
        } catch (e) {
            return 'light';
        }
    }

    function repaintShell() {
        var sidebar = global.document.getElementById('sidebar');
        var header = global.document.getElementById('header');
        if (sidebar) {
            sidebar.style.removeProperty('background-color');
            sidebar.style.removeProperty('background');
            void sidebar.offsetHeight;
        }
        if (header) {
            header.style.removeProperty('background-color');
            void header.offsetHeight;
        }
    }

    function applyTheme(theme, options) {
        options = options || {};
        theme = normalizeTheme(theme);
        var root = global.document.documentElement;
        root.setAttribute('data-theme', theme);
        root.classList.toggle('cp-theme-dark', theme === 'dark');
        root.classList.toggle('cp-theme-light', theme === 'light');
        root.style.colorScheme = theme;

        if (!options.skipStore) {
            try {
                global.localStorage.setItem('cyberPanelTheme', theme);
            } catch (e) { /* private mode */ }
        }

        if (!options.skipRepaint) {
            repaintShell();
        }

        var icon = global.document.getElementById('theme-icon');
        if (icon) {
            icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        }
        var toggle = global.document.getElementById('theme-toggle');
        if (toggle) {
            toggle.setAttribute('aria-pressed', theme === 'dark' ? 'true' : 'false');
        }

        if (!options.silent) {
            try {
                global.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: theme } }));
            } catch (e) { /* IE */ }
        }

        return theme;
    }

    function toggleTheme() {
        var current = global.document.documentElement.getAttribute('data-theme');
        var next = normalizeTheme(current) === 'dark' ? 'light' : 'dark';
        return applyTheme(next);
    }

    function initThemeToggle() {
        applyTheme(readStoredTheme(), { skipStore: true, silent: true });
        var toggle = global.document.getElementById('theme-toggle');
        if (toggle && toggle.getAttribute('data-cp-theme-bound') !== '1') {
            toggle.setAttribute('data-cp-theme-bound', '1');
            toggle.addEventListener('click', function (ev) {
                ev.preventDefault();
                toggleTheme();
            });
        }
    }

    global.CyberPanelTheme = {
        normalizeTheme: normalizeTheme,
        readStoredTheme: readStoredTheme,
        applyTheme: applyTheme,
        toggleTheme: toggleTheme,
        initThemeToggle: initThemeToggle
    };

    if (global.document.readyState === 'loading') {
        global.document.addEventListener('DOMContentLoaded', initThemeToggle);
    } else {
        initThemeToggle();
    }
})(window);
