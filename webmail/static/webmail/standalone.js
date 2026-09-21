/* Mailbox sessions have their own shell; do not load panel controllers. */
var app = angular.module('CyberCP', []);
app.config(['$interpolateProvider', function ($interpolateProvider) {
    $interpolateProvider.startSymbol('{$');
    $interpolateProvider.endSymbol('$}');
}]);
function getCookie(name) {
    var cookies = document.cookie ? document.cookie.split(';') : [];
    for (var i = 0; i < cookies.length; i++) {
        var cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === name + '=') {
            return decodeURIComponent(cookie.substring(name.length + 1));
        }
    }
    return null;
}
(function () {
    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        var button = document.getElementById('wm-theme-toggle');
        if (button) {
            button.setAttribute('aria-pressed', theme === 'dark' ? 'true' : 'false');
            button.firstElementChild.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        }
    }
    var theme = 'light';
    try { theme = localStorage.getItem('cyberPanelTheme') === 'dark' ? 'dark' : 'light'; } catch (error) {}
    applyTheme(theme);
    document.addEventListener('DOMContentLoaded', function () {
        applyTheme(theme);
        document.getElementById('wm-theme-toggle').addEventListener('click', function () {
            theme = theme === 'dark' ? 'light' : 'dark';
            applyTheme(theme);
            try { localStorage.setItem('cyberPanelTheme', theme); } catch (error) {}
        });
    });
}());
