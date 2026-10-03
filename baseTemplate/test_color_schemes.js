const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const script = fs.readFileSync(path.join(__dirname, 'static/baseTemplate/js/cyberpanel-schemes.js'), 'utf8');
for (const scheme of ['bright', 'apple']) {
    for (const dark of [false, true]) {
        const store = new Map([['cyberPanelColorScheme', scheme], ['cyberPanelTheme', dark ? 'dark' : 'light']]);
        const attributes = {};
        const events = {};
        function element() {
            return {dataset: {}, hidden: true, events: {}, attributes: {},
                setAttribute(k, v) { this.attributes[k] = v; },
                addEventListener(k, callback) { this.events[k] = callback; },
                contains() { return false; }, focus() {}};
        }
        const choices = ['evergreen', 'bright', 'apple'].map(name => { const e = element(); e.dataset.scheme = name; return e; });
        const trigger = element(); const panel = element(); panel.querySelectorAll = () => choices;
        const windowEvents = {};
        vm.runInNewContext(script, {
            document: {documentElement: {setAttribute(k, v) { attributes[k] = v; }},
                addEventListener(k, cb) { events[k] = cb; },
                getElementById(id) { return id === 'cp-appearance-trigger' ? trigger : panel; }},
            localStorage: {getItem(k) { return store.get(k); }, setItem(k, v) { store.set(k, v); }},
            window: {addEventListener(k, cb) { windowEvents[k] = cb; }}
        });
        assert.equal(attributes['data-color-scheme'], scheme);
        assert.equal(attributes['data-theme'], dark ? 'dark' : 'light');
        events.DOMContentLoaded();
        assert.equal(choices.find(c => c.dataset.scheme === scheme).attributes['aria-pressed'], 'true');
        const target = scheme === 'bright' ? 'apple' : 'bright';
        choices.find(c => c.dataset.scheme === target).events.click();
        assert.equal(store.get('cyberPanelColorScheme'), target);
        assert.equal(attributes['data-color-scheme'], target);
        windowEvents.storage({key: 'cyberPanelColorScheme', newValue: scheme});
        assert.equal(attributes['data-color-scheme'], scheme);
    }
}
console.log('New schemes restore, select, persist and sync in light and dark modes.');
