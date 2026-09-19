/* Exercise the actual controller and directives without network or mail delivery. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, 'static/webmail/webmail.js'), 'utf8');

function harness() {
    let controller;
    const directives = {}, requests = [], commands = [], editor = {innerHTML: ''};
    const scope = {$on() {}, $evalAsync(callback) { callback(); }};
    const sandbox = {
        app: {filter() {}, directive(name, factory) { directives[name] = factory; },
            controller(name, parts) { controller = parts.at(-1); }},
        getCookie: () => 'token', PNotify: function() {}, console,
        document: {getElementById: () => editor, execCommand: (...args) => commands.push(args)},
        window: {}, setInterval: () => 1, clearInterval() {},
        angular: {identity: value => value, copy: value => JSON.parse(JSON.stringify(value))},
        FormData: class { constructor() { this.fields = []; } append(...args) { this.fields.push(args); } },
        prompt: () => sandbox.url
    };
    vm.runInNewContext(source, sandbox);
    const http = {post(url, payload) {
        const req = {url, payload}; requests.push(req);
        return {then(success, failure) { req.success = data => success({data}); req.failure = failure; }};
    }};
    controller(scope, http, {trustAsHtml: value => value}, callback => callback());
    scope.currentEmail = 'user@example.com';
    return {scope, directives, editor, requests, commands, sandbox};
}

function element() {
    let html = '';
    const handlers = {}, classes = new Set();
    return {handlers, classes,
        on(events, callback) { for (const e of events.split(' ')) handlers[e] = callback; },
        off(events) { for (const e of events.split(' ')) delete handlers[e]; },
        addClass(c) { classes.add(c); }, removeClass(c) { classes.delete(c); },
        html(value) { if (value !== undefined) html = value; return html; }
    };
}

for (const action of ['composeNew', 'replyTo', 'replyAll', 'forwardMsg', 'composeToContact']) {
    test(action + ' inserts one saved signature before quoted mail', () => {
        const h = harness();
        h.scope.safeSignatureHtml = '<b>Saved signature</b>';
        h.scope.openMsg = {from: 'sender@example.com', to: 'user@example.com',
            subject: 'Hi', date: '<unsafe>', body_text: 'Original message'};
        h.scope[action]({email_address: 'contact@example.com'});
        assert.equal(h.editor.innerHTML.split('Saved signature').length - 1, 1);
        if (['replyTo', 'replyAll', 'forwardMsg'].includes(action)) {
            assert.ok(h.editor.innerHTML.indexOf('Saved signature') < h.editor.innerHTML.indexOf('Original message'));
            assert.match(h.editor.innerHTML, /&lt;unsafe&gt;/);
        }
        h.scope.updateComposeBody();
        assert.equal(h.scope.compose.body, h.editor.innerHTML);
    });
}

test('file drops on editor or composer attach every file and use multipart sending', () => {
    const h = harness(), el = element();
    let cleanup;
    h.scope.$on = (name, fn) => { cleanup = fn; };
    h.directives.wmFileDrop().link(h.scope, el);
    const files = [{name: 'one.pdf', size: 22}, {name: 'two.png', size: 33}];
    let prevented = 0, stopped = 0;
    const event = {dataTransfer: {types: ['Files'], files},
        preventDefault() { prevented++; }, stopPropagation() { stopped++; }};
    el.handlers.dragenter(event);
    el.handlers.dragenter(event);
    el.handlers.dragleave(event);
    assert.ok(el.classes.has('wm-drag-over'));
    el.handlers.dragover(event);
    assert.equal(event.dataTransfer.dropEffect, 'copy');
    el.handlers.drop(event);
    assert.equal(stopped, 1);
    assert.equal(prevented, 5);
    assert.equal(el.classes.size, 0);
    assert.equal(h.scope.compose.files[0], files[0]);
    assert.equal(h.scope.compose.files[1], files[1]);
    h.scope.compose.to = 'recipient@example.com';
    h.scope.sendMessage();
    const request = h.requests.at(-1);
    assert.equal(request.url, '/webmail/api/sendMessage');
    assert.equal(request.payload.fields.find(f => f[0] === 'attachment_0')[1], files[0]);
    assert.equal(request.payload.fields.find(f => f[0] === 'attachment_1')[1], files[1]);
    cleanup();
    assert.deepEqual(el.handlers, {});
});

test('text drags retain native editing behavior and do not add attachments', () => {
    const h = harness(), el = element();
    h.directives.wmFileDrop().link(h.scope, el);
    const event = {dataTransfer: {types: ['text/plain'], files: []}, preventDefault() { throw Error('blocked text drag'); }};
    el.handlers.dragover(event); el.handlers.drop(event);
    assert.equal(h.scope.compose.files.length, 0);
});

test('file selection snapshots FileList before the input is reset', () => {
    const h = harness();
    const pending = [];
    h.scope.$evalAsync = fn => pending.push(fn);
    const file = {name: 'file.txt'}, files = [file];
    h.scope.addFiles(files);
    files.length = 0;
    pending[0]();
    assert.equal(h.scope.compose.files[0], file);
});

test('signature editor renders saved HTML, updates ngModel and pastes only text', () => {
    const h = harness(), el = element();
    let cleanup, value;
    h.scope.$on = (name, fn) => { cleanup = fn; };
    const model = {$viewValue: '<b>Saved</b>', $setViewValue(v) { value = v; }};
    h.directives.wmSignatureEditor().link(h.scope, el, {}, model);
    model.$render(); assert.equal(el.html(), '<b>Saved</b>');
    el.html('<i>Edited</i>'); el.handlers.input(); assert.equal(value, '<i>Edited</i>');
    let prevented = false;
    el.handlers.paste({preventDefault() { prevented = true; }, clipboardData: {
        getData(type) { assert.equal(type, 'text/plain'); return '<img onerror=attack()>'; }
    }});
    assert.ok(prevented);
    assert.deepEqual(h.commands.at(-1), ['insertText', false, '<img onerror=attack()>']);
    cleanup(); assert.deepEqual(el.handlers, {});
});

test('link formatting refuses executable URL schemes', () => {
    const h = harness();
    for (const url of ['javascript:alert(1)', 'data:text/html,boom', 'vbscript:boom']) {
        h.sandbox.url = url; h.scope.insertLink();
    }
    assert.equal(h.commands.length, 0);
    h.sandbox.url = 'https://example.com'; h.scope.insertLink();
    assert.deepEqual(h.commands[0], ['createLink', false, 'https://example.com']);
});

test('late settings for another account cannot replace its signature', () => {
    const h = harness();
    h.scope.loadSettings(); const request = h.requests.at(-1);
    h.scope.currentEmail = 'other@example.com'; h.scope.safeSignatureHtml = '<b>Other</b>';
    request.success({status: 1, settings: {signatureHtml: 'Old account'}});
    assert.equal(h.scope.safeSignatureHtml, '<b>Other</b>');
});

test('settings save installs the sanitized server response as the compose signature', () => {
    const h = harness();
    h.scope.wmSettings = {signatureHtml: '<b>Safe</b><script>bad()</script>'};
    h.scope.saveSettings();
    h.requests.at(-1).success({status: 1, signatureHtml: '<b>Safe</b>'});
    assert.equal(h.scope.wmSettings.signatureHtml, '<b>Safe</b>');
    assert.equal(h.scope.safeSignatureHtml, '<b>Safe</b>');
});
