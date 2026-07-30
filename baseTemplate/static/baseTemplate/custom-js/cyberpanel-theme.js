/**
 * CyberPanel theme toggle (v2.4.8+ shell). Syncs data-theme, helper classes, and shell repaint.
 * Theme flips disable CSS transitions for one paint so the huge dark stylesheet does not animate.
 */
(function (global) {
    'use strict';

    var switchingTimer = null;
    var isSwitching = false;

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

    function clearShellInlineStyles() {
        var sidebar = global.document.getElementById('sidebar');
        var header = global.document.getElementById('header');
        if (sidebar) {
            sidebar.style.removeProperty('background-color');
            sidebar.style.removeProperty('background');
        }
        if (header) {
            header.style.removeProperty('background-color');
        }
    }

    function endThemeSwitching(root) {
        if (switchingTimer) {
            global.clearTimeout(switchingTimer);
            switchingTimer = null;
        }
        root.classList.remove('cp-theme-switching');
        isSwitching = false;
    }

    function beginThemeSwitching(root) {
        isSwitching = true;
        root.classList.add('cp-theme-switching');
        if (switchingTimer) {
            global.clearTimeout(switchingTimer);
        }
        // Keep transitions off until after the browser paints the new theme.
        global.requestAnimationFrame(function () {
            global.requestAnimationFrame(function () {
                endThemeSwitching(root);
            });
        });
        // Fallback if rAF is delayed/throttled in background tabs.
        switchingTimer = global.setTimeout(function () {
            endThemeSwitching(root);
        }, 120);
    }

    function applyTheme(theme, options) {
        options = options || {};
        theme = normalizeTheme(theme);
        var root = global.document.documentElement;
        var current = normalizeTheme(root.getAttribute('data-theme'));
        var themeChanged = current !== theme;

        if (themeChanged && !options.skipSwitchGuard) {
            beginThemeSwitching(root);
        }

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
            // Clear stale inline backgrounds without forced layout thrashing.
            clearShellInlineStyles();
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
        if (isSwitching) {
            return normalizeTheme(global.document.documentElement.getAttribute('data-theme'));
        }
        var current = global.document.documentElement.getAttribute('data-theme');
        var next = normalizeTheme(current) === 'dark' ? 'light' : 'dark';
        return applyTheme(next);
    }

    function initThemeToggle() {
        applyTheme(readStoredTheme(), { skipStore: true, silent: true, skipSwitchGuard: true });
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
