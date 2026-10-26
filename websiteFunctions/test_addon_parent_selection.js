const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');

for (const relative of ['websiteFunctions/static/websiteFunctions/websiteFunctions.js', 'static/websiteFunctions/websiteFunctions.js']) {
    const source = fs.readFileSync(path.join(__dirname, '..', relative), 'utf8');
    const start = source.indexOf("app.controller('websitePages',");
    const code = source.slice(start, source.indexOf("app.controller('suspendWebsiteControl',", start));
    function setup(existingParent = '') {
        let controller;
        const requests = [], scope = {$on: () => {}};
        const jquery = () => ({text: () => existingParent, html: () => 'alpha.example', hide: () => {}, show: () => {}, fadeIn: () => {}, fadeOut: () => {}});
        const context = {app: {controller: (name, callback) => { controller = callback; }}, $: jquery,
            getCookie: () => 'fixture-csrf', console: {log: () => {}}};
        vm.runInNewContext(code, context);
        const http = {post: (url, data) => { requests.push({url, data}); return {then: () => {}}; }};
        controller(scope, http, () => {}, {});
        return {scope, requests};
    }
    test(relative + ': addon requires an explicitly selected parent', () => {
        const t = setup(); t.scope.websitetype = 'Addon Domain'; t.scope.WebsiteType();
        assert.equal(t.scope.webselection, false);
        assert.equal(t.scope.DomainCreateForm, true);
        assert.equal(t.scope.masterDomain, '');
        t.scope.createDomain(); assert.equal(t.requests.length, 0);
    });
    test(relative + ': changing type retains and submits the selected parent', () => {
        const t = setup(); t.scope.websitetype = 'Sub Domain'; t.scope.WebsiteType();
        t.scope.masterDomain = 'zeta.example'; t.scope.WebsiteSelection();
        for (const type of ['Addon Domain', 'Sub Domain', 'Addon Domain']) {
            t.scope.websitetype = type; t.scope.WebsiteType();
            assert.equal(t.scope.masterDomain, 'zeta.example');
            assert.equal(t.scope.webselection, false); assert.equal(t.scope.DomainCreateForm, false);
        }
        t.scope.domainNameCreate = 'addon.example'; t.scope.docRootPath = 'public_html/addon'; t.scope.phpSelection = 'PHP 8.3';
        t.scope.createDomain(); assert.equal(t.requests.length, 1);
        assert.equal(t.requests[0].url, '/websites/submitDomainCreation');
        assert.equal(t.requests[0].data.masterDomain, 'zeta.example');
    });
    test(relative + ': clearing the parent prevents any creation request', () => {
        const t = setup(); t.scope.websitetype = 'Addon Domain'; t.scope.WebsiteType();
        t.scope.masterDomain = 'zeta.example'; t.scope.WebsiteSelection();
        t.scope.masterDomain = ''; t.scope.WebsiteSelection();
        assert.equal(t.scope.DomainCreateForm, true);
        t.scope.createDomain(); assert.equal(t.requests.length, 0);
    });
    test(relative + ': existing site page keeps its fixed parent context', () => {
        const t = setup('zeta.example');
        t.scope.domainNameCreate = 'child.zeta.example'; t.scope.createDomain();
        assert.equal(t.requests[0].data.masterDomain, 'zeta.example');
    });
}
