/**
 * File Manager theme toggle. Shares cyberPanelTheme with the main CyberPanel shell.
 */
(function (global) {
    'use strict';

    var STORAGE_KEY = 'cyberPanelTheme';

    function normalizeTheme(value) {
        return value === 'dark' ? 'dark' : 'light';
    }

    function readStoredTheme() {
        try {
            return normalizeTheme(global.localStorage.getItem(STORAGE_KEY));
        } catch (e) {
            return 'light';
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
                global.localStorage.setItem(STORAGE_KEY, theme);
            } catch (e) {}
        }

        var toggle = global.document.getElementById('fm-theme-toggle');
        var icon = global.document.getElementById('fm-theme-icon');
        if (toggle) {
            toggle.setAttribute('aria-pressed', theme === 'dark' ? 'true' : 'false');
            toggle.setAttribute('title', theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
            toggle.setAttribute('aria-label', theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
        }
        if (icon) {
            icon.className = theme === 'dark' ? 'fa fa-sun-o' : 'fa fa-moon-o';
        }
    }

    function toggleTheme() {
        var current = normalizeTheme(
            global.document.documentElement.getAttribute('data-theme') || readStoredTheme()
        );
        applyTheme(current === 'dark' ? 'light' : 'dark');
    }

    function init() {
        applyTheme(readStoredTheme(), { skipStore: true });
        var toggle = global.document.getElementById('fm-theme-toggle');
        if (toggle && !toggle._fmThemeBound) {
            toggle._fmThemeBound = true;
            toggle.addEventListener('click', function (ev) {
                ev.preventDefault();
                toggleTheme();
            });
        }
    }

    if (global.document.readyState === 'loading') {
        global.document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    global.CyberPanelFileManagerTheme = {
        apply: applyTheme,
        toggle: toggleTheme,
        get: function () {
            return normalizeTheme(
                global.document.documentElement.getAttribute('data-theme') || readStoredTheme()
            );
        }
    };
})(window);
