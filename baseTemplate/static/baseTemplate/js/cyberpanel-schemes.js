/* Apply saved appearance before paint, including on standalone tools. */
(function () {
    'use strict';
    var schemes = ['evergreen', 'ocean', 'cloud', 'violet', 'slate'];
    var root = document.documentElement;
    var selected = 'evergreen';
    try {
        var saved = localStorage.getItem('cyberPanelColorScheme');
        if (schemes.indexOf(saved) !== -1) selected = saved;
        root.setAttribute('data-theme', localStorage.getItem('cyberPanelTheme') === 'dark' ? 'dark' : 'light');
    } catch (e) { /* Storage may be disabled; appearance still works for this page. */ }
    root.setAttribute('data-color-scheme', selected);
    document.addEventListener('DOMContentLoaded', function () {
        var trigger = document.getElementById('cp-appearance-trigger');
        var panel = document.getElementById('cp-appearance-panel');
        if (!trigger || !panel) return;
        var choices = panel.querySelectorAll('[data-scheme]');
        function sync() {
            choices.forEach(function (button) { button.setAttribute('aria-pressed', button.dataset.scheme === selected ? 'true' : 'false'); });
        }
        function close() { panel.hidden = true; trigger.setAttribute('aria-expanded', 'false'); }
        trigger.addEventListener('click', function () {
            panel.hidden = !panel.hidden;
            trigger.setAttribute('aria-expanded', String(!panel.hidden));
        });
        choices.forEach(function (button) {
            button.addEventListener('click', function () {
                selected = button.dataset.scheme;
                root.setAttribute('data-color-scheme', selected);
                try { localStorage.setItem('cyberPanelColorScheme', selected); } catch (e) {}
                sync();
            });
        });
        document.addEventListener('click', function (event) { if (!panel.contains(event.target) && !trigger.contains(event.target)) close(); });
        document.addEventListener('keydown', function (event) { if (event.key === 'Escape' && !panel.hidden) { close(); trigger.focus(); } });
        window.addEventListener('storage', function (event) {
            if (event.key === 'cyberPanelColorScheme') { selected = schemes.indexOf(event.newValue) !== -1 ? event.newValue : 'evergreen'; root.setAttribute('data-color-scheme', selected); sync(); }
        });
        sync();
    });
})();
