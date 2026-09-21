/* Verify the standalone shell initializes its module before mailbox consumers.
 * Run with: node webmail/test_standalone_bootstrap.js
 */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = __dirname;
const shell = fs.readFileSync(path.join(root, 'templates/webmail/base.html'), 'utf8');
const mailbox = fs.readFileSync(path.join(root, 'templates/webmail/index.html'), 'utf8');
// Substitute the actual content block, rather than assuming script order.
const documentSource = shell.replace('{% block content %}{% endblock %}', mailbox);
const scripts = Array.from(documentSource.matchAll(/<script\b([^>]*)>/g), match => match[1]);
const bootstrapIndex = scripts.findIndex(source => source.includes('webmail/standalone.js'));
const controllerIndex = scripts.findIndex(source => source.includes('webmail/webmail.js'));
assert.ok(bootstrapIndex >= 0 && controllerIndex > bootstrapIndex);
assert.doesNotMatch(scripts[bootstrapIndex], /\b(?:async|defer)\b/);

const modules = new Map();
const registrations = [];
const attrs = {}, handlers = {};
const button = {
    firstElementChild: {},
    setAttribute(name, value) { attrs[name] = value; },
    addEventListener(name, callback) { handlers[name] = callback; },
};
const context = vm.createContext({
    angular: {
        module(name, dependencies) {
            if (dependencies) {
                modules.set(name, {
                    config(config) { config[1]({startSymbol() {}, endSymbol() {}}); },
                    filter(name) { registrations.push(['filter', name]); },
                    directive(name) { registrations.push(['directive', name]); },
                    controller(name) { registrations.push(['controller', name]); },
                });
            }
            assert.ok(modules.has(name), 'Angular module must exist before use');
            return modules.get(name);
        },
    },
    document: {
        cookie: 'other=1; csrftoken=token%2Bvalue',
        documentElement: {setAttribute(name, value) { attrs[name] = value; }},
        getElementById() { return button; },
        addEventListener(name, callback) { handlers[name] = callback; },
    },
    localStorage: {
        getItem(key) { assert.equal(key, 'cyberPanelTheme'); return 'dark'; },
        setItem(key, value) { assert.equal(key, 'cyberPanelTheme'); assert.equal(value, 'light'); },
    },
});
for (const script of scripts) {
    const asset = script.match(/webmail\/(standalone|webmail)\.js/);
    if (asset) vm.runInContext(fs.readFileSync(path.join(root, 'static', asset[0]), 'utf8'), context);
}
assert.ok(registrations.some(item => item[0] === 'controller' && item[1] === 'webmailCtrl'));
assert.equal(context.getCookie('csrftoken'), 'token+value');
handlers.DOMContentLoaded();
assert.equal(attrs['data-theme'], 'dark');
assert.equal(attrs['aria-pressed'], 'true');
handlers.click();
assert.equal(attrs['data-theme'], 'light');
assert.equal(attrs['aria-pressed'], 'false');
// The controller's detail modes must all reveal the pane on narrow screens.
// A read-only selector previously left compose/settings/contacts invisible.
const classExpression = mailbox.match(/class="webmail-container" ng-class="([^"]+)"/)[1];
const css = fs.readFileSync(path.join(root, 'static/webmail/webmail.css'), 'utf8');
const mobileCss = css.slice(css.indexOf('@media (max-width: 768px)'));
const visiblePaneRule = mobileCss.match(/\.webmail-container\.([\w-]+)\s+\.wm-detail-pane\s*\{([^}]+)\}/);
assert.ok(visiblePaneRule && /display:\s*block/.test(visiblePaneRule[2]));
for (const mode of ['read', 'compose', 'contacts', 'rules', 'settings']) {
    const classes = vm.runInNewContext('(' + classExpression + ')', {viewMode: mode});
    assert.equal(classes[visiblePaneRule[1]], true, mode + ' must reveal the mobile pane');
}
const inboxClasses = vm.runInNewContext('(' + classExpression + ')', {viewMode: 'list'});
assert.equal(inboxClasses[visiblePaneRule[1]], false, 'Inbox keeps the detail pane closed');
console.log('Standalone module, CSRF, theme and mobile detail visibility checks passed.');
