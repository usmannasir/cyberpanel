/* Execute the actual controller with deferred HTTP responses; no browser/network. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, 'static/webmail/webmail.js'), 'utf8');

function harness() {
    let controller;
    const requests = [], notices = [];
    const scope = {};
    const sandbox = {
        app: {filter() {}, directive() {}, controller(name, parts) { controller = parts.at(-1); }},
        getCookie: () => 'test-token',
        PNotify: function(value) { notices.push(value); },
        console: {error() {}},
        setInterval() { throw Error('Unexpected timer'); }, clearInterval() {},
        document: {}, window: {},
    };
    vm.runInNewContext(source, sandbox, {filename: 'webmail.js'});
    const http = {post(url, payload) {
        const request = {url, payload}; requests.push(request);
        return {then(success, failure) { request.success = success; request.failure = failure; }};
    }};
    controller(scope, http, {trustAsHtml: value => value}, callback => callback());
    scope.currentEmail = 'fixture@example.com';
    const respond = (request, data) => request.success({data});
    const listData = (uid = 1) => ({status: 1, messages: [{uid, selected: true}], total: 1, pages: 1});
    function load(uid = 1) {
        scope.loadMessages(); respond(requests.at(-1), listData(uid));
        return scope.messages[0];
    }
    function open(uid = 1) {
        const msg = load(uid);
        scope.openMessage(msg);
        respond(requests.at(-1), {status: 1, message: {uid, body_text: 'Disposable fixture'}});
        return scope.openMsg;
    }
    return {scope, requests, notices, respond, load, open, listData};
}

for (const action of ['bulk', 'single']) {
    test(action + ' delete exposes status-0 errors and preserves the current message', () => {
        const h = harness(), s = h.scope;
        const msg = action === 'single' ? h.open() : h.load();
        const previous = s.openMsg, count = h.requests.length;
        action === 'single' ? s.deleteMsg(msg) : s.bulkDelete();
        assert.equal(s.deletingMessages, true);
        h.respond(h.requests.at(-1), {status: 0, error_message: 'Refresh source and Trash.'});
        assert.equal(s.deletingMessages, false);
        assert.equal(s.openMsg, previous);
        assert.equal(h.requests.length, count + 1);
        assert.equal(h.notices.at(-1).text, 'Refresh source and Trash.');
        assert.equal(h.notices.at(-1).type, 'error');
    });
    test(action + ' delete exposes transport uncertainty without retrying', () => {
        const h = harness(), s = h.scope;
        const msg = action === 'single' ? h.open() : h.load();
        const previous = s.openMsg, count = h.requests.length;
        action === 'single' ? s.deleteMsg(msg) : s.bulkDelete();
        h.requests.at(-1).failure({status: 502});
        assert.equal(s.deletingMessages, false);
        assert.equal(s.openMsg, previous);
        assert.equal(h.requests.length, count + 1);
        assert.match(h.notices.at(-1).text, /could not be confirmed.*Trash/);
    });
    test(action + ' delete suppresses double clicks and reloads after confirmed success', () => {
        const h = harness(), s = h.scope;
        const msg = action === 'single' ? h.open() : h.load();
        const count = h.requests.length;
        action === 'single' ? s.deleteMsg(msg) : s.bulkDelete();
        s.bulkDelete(); s.deleteMsg(msg);
        assert.equal(h.requests.length, count + 1);
        const request = h.requests.at(-1);
        assert.deepEqual(JSON.parse(JSON.stringify(request.payload)), {folder: 'INBOX', uids: [1], fromAccount: 'fixture@example.com'});
        h.respond(request, {status: 1});
        assert.equal(s.deletingMessages, false);
        assert.equal(s.openMsg, null);
        assert.deepEqual(h.requests.slice(-2).map(r => r.url), ['/webmail/api/listMessages', '/webmail/api/listFolders']);
    });
}

test('empty selection and in-progress message loads cannot delete', () => {
    const h = harness(), s = h.scope;
    s.bulkDelete(); assert.equal(h.requests.length, 0);
    const msg = h.load(); s.loadMessages();
    const count = h.requests.length;
    s.bulkDelete(); s.deleteMsg(msg);
    assert.equal(h.requests.length, count);
});

test('old folder and account contexts are refused for bulk and single delete', () => {
    for (const field of ['currentFolder', 'currentEmail']) {
        const h = harness(), s = h.scope, msg = h.open();
        s[field] = 'different';
        const count = h.requests.length;
        s.deleteMsg(msg); s.bulkDelete();
        assert.equal(h.requests.length, count);
        assert.equal(h.notices.length, 2);
        assert.match(h.notices[0].text, /folder or account changed/);
    }
});

test('late folder list responses cannot install stale deletable rows', () => {
    const h = harness(), s = h.scope;
    s.loadMessages(); const old = h.requests.at(-1);
    s.selectFolder('Trash'); const current = h.requests.at(-1);
    h.respond(old, h.listData(12));
    assert.equal(s.messages.length, 0);
    assert.equal(s.loading, true);
    h.respond(current, h.listData(42));
    s.bulkDelete();
    assert.equal(h.requests.at(-1).payload.folder, 'Trash');
    assert.equal(h.requests.at(-1).payload.uids[0], 42);
});

test('late account responses and out-of-order list requests are ignored', () => {
    const h = harness(), s = h.scope;
    s.loadMessages(); const old = h.requests.at(-1);
    s.currentEmail = 'other@example.com'; s.loadMessages(); const current = h.requests.at(-1);
    h.respond(current, h.listData(2)); h.respond(old, h.listData(1));
    assert.equal(s.messages[0].uid, 2);
    s.loadMessages(); const first = h.requests.at(-1);
    s.loadMessages(); const last = h.requests.at(-1);
    h.respond(last, h.listData(4)); h.respond(first, h.listData(3));
    assert.equal(s.messages[0].uid, 4);
});

test('late open-message response cannot target an old message in a new folder', () => {
    const h = harness(), s = h.scope, msg = h.load();
    s.openMessage(msg); const old = h.requests.at(-1);
    s.selectFolder('Trash');
    h.respond(old, {status: 1, message: {uid: 1}});
    assert.equal(s.openMsg, null);
    assert.equal(s.viewMode, 'list');
});

test('late successful deletion does not close a message opened in another folder', () => {
    const h = harness(), s = h.scope, msg = h.open();
    s.deleteMsg(msg); const old = h.requests.at(-1);
    s.selectFolder('Trash'); h.respond(h.requests.at(-1), h.listData(2));
    s.openMessage(s.messages[0]); h.respond(h.requests.at(-1), {status: 1, message: {uid: 2}});
    const current = s.openMsg, count = h.requests.length;
    h.respond(old, {status: 1});
    assert.equal(s.openMsg, current);
    assert.equal(h.requests.length, count);
});

test('search results keep their original context and block delete while fetching', () => {
    const h = harness(), s = h.scope;
    h.load(); s.searchQuery = 'fixture'; s.searchMessages();
    h.respond(h.requests.at(-1), {status: 1, uids: [2]});
    assert.equal(s.loading, true);
    const request = h.requests.at(-1), count = h.requests.length;
    s.bulkDelete(); assert.equal(h.requests.length, count);
    assert.equal(request.payload.folder, 'INBOX');
    assert.equal(request.payload.fromAccount, 'fixture@example.com');
    h.respond(request, h.listData(2));
    s.bulkDelete(); assert.equal(h.requests.at(-1).payload.uids[0], 2);
});

test('search response after folder change does not fetch old UIDs in the new folder', () => {
    const h = harness(), s = h.scope;
    s.searchQuery = 'fixture'; s.searchMessages(); const old = h.requests.at(-1);
    s.selectFolder('Trash'); const count = h.requests.length;
    h.respond(old, {status: 1, uids: [1]});
    assert.equal(h.requests.length, count);
    assert.equal(s.loading, true);
});

test('both native delete controls are disabled during deletion and loading', () => {
    const template = fs.readFileSync(path.join(__dirname, 'templates/webmail/index.html'), 'utf8');
    for (const action of ['bulkDelete()', 'deleteMsg(openMsg)']) {
        const button = template.split('<button').find(part => part.split('>')[0].includes('ng-click="' + action + '"'));
        assert.match(button.split('>')[0], /ng-disabled="deletingMessages \|\| movingMessages \|\| loading"/);
    }
});

function loadedPair(h) {
    h.scope.loadMessages();
    h.respond(h.requests.at(-1), {status: 1, messages: [{uid: 1, selected: true}, {uid: 2, selected: true}], total: 2, pages: 1});
}

test('bulk Move receives the explicit child-scope destination and both selected UIDs', () => {
    const h = harness(), s = h.scope;
    loadedPair(h);
    s.bulkMove({name: 'INBOX.Archive'});
    const request = h.requests.at(-1);
    assert.equal(request.url, '/webmail/api/moveMessages');
    assert.deepEqual(JSON.parse(JSON.stringify(request.payload)), {folder: 'INBOX', uids: [1, 2], targetFolder: 'INBOX.Archive', fromAccount: 'fixture@example.com'});
    assert.equal(s.movingMessages, true);
});

for (const failure of ['status', 'http']) {
    test('bulk Move ' + failure + ' failure remains visible without reloading or retry', () => {
        const h = harness(), s = h.scope;
        loadedPair(h); s.showMoveDropdown = true;
        const before = s.messages, count = h.requests.length;
        s.bulkMove('INBOX.Archive');
        if (failure === 'status') h.respond(h.requests.at(-1), {status: 0, error_message: 'Destination unavailable.'});
        else h.requests.at(-1).failure({status: 502});
        assert.equal(s.movingMessages, false);
        assert.equal(s.messages, before);
        assert.equal(s.showMoveDropdown, true);
        assert.equal(h.requests.length, count + 1);
        assert.equal(h.notices.at(-1).type, 'error');
    });
}

test('Move and Delete exclude overlapping submissions', () => {
    const h = harness(), s = h.scope;
    loadedPair(h); s.bulkMove('INBOX.Archive');
    const count = h.requests.length;
    s.bulkMove('Trash'); s.bulkDelete(); s.deleteMsg(s.messages[0]);
    assert.equal(h.requests.length, count);
    h.respond(h.requests.at(-1), {status: 0});
    s.bulkDelete(); const next = h.requests.length;
    s.bulkMove('Trash');
    assert.equal(h.requests.length, next);
});

test('Move requires a fresh message context and a different destination', () => {
    const h = harness(), s = h.scope;
    loadedPair(h); const count = h.requests.length;
    s.bulkMove('INBOX'); s.currentFolder = 'Trash'; s.bulkMove('INBOX.Archive');
    assert.equal(h.requests.length, count);
    assert.equal(h.notices.length, 2);
});

test('late Move success does not clear destination state in another folder', () => {
    const h = harness(), s = h.scope;
    loadedPair(h); s.bulkMove('INBOX.Archive'); const request = h.requests.at(-1);
    s.currentFolder = 'Trash'; s.showMoveDropdown = true; s.moveTarget = 'INBOX';
    const count = h.requests.length;
    h.respond(request, {status: 1});
    assert.equal(s.movingMessages, false);
    assert.equal(s.showMoveDropdown, true);
    assert.equal(s.moveTarget, 'INBOX');
    assert.equal(h.requests.length, count);
});

test('native Move selector passes its selected target to the parent controller', () => {
    const template = fs.readFileSync(path.join(__dirname, 'templates/webmail/index.html'), 'utf8');
    assert.match(template, /ng-model="moveTarget" ng-change="bulkMove\(moveTarget\)"/);
});

for (const action of ['single', 'bulk', 'move']) {
    for (const folderFirst of [false, true]) {
        test(action + ' refresh preserves selection when folder counts return ' + (folderFirst ? 'first' : 'last'), () => {
            const h = harness(), s = h.scope;
            if (action === 'single') s.deleteMsg(h.open('1'));
            else { h.load('1'); action === 'bulk' ? s.bulkDelete() : s.bulkMove('INBOX.Archive'); }
            h.respond(h.requests.at(-1), {status: 1});
            const list = h.requests.at(-2), folders = h.requests.at(-1), count = h.requests.length;
            assert.equal(list.url, '/webmail/api/listMessages');
            assert.equal(folders.url, '/webmail/api/listFolders');
            assert.equal(s.loading, true);
            if (folderFirst) {
                h.respond(folders, {status: 1, folders: [{name: 'INBOX', unread_count: 2}]});
                assert.equal(h.requests.length, count, 'Folder counts must not schedule a second message replacement');
            }
            h.respond(list, {status: 1, messages: [{uid: '2'}, {uid: '3'}], total: 2, pages: 1});
            const messages = s.messages;
            messages[0].selected = true;
            if (!folderFirst) h.respond(folders, {status: 1, folders: [{name: 'INBOX', unread_count: 2}]});
            assert.equal(h.requests.length, count, 'Folder counts must not schedule a second message replacement');
            assert.equal(s.messages, messages);
            assert.equal(s.messages[0].selected, true);
            assert.equal(s.folders[0].unread_count, 2);
            s.bulkDelete();
            assert.deepEqual(JSON.parse(JSON.stringify(h.requests.at(-1).payload.uids)), ['2']);
        });
    }
}

test('normal folder loading still requests the selected message list', () => {
    const h = harness(), s = h.scope;
    s.loadFolders(); const count = h.requests.length;
    h.respond(h.requests.at(-1), {status: 1, folders: [{name: 'INBOX'}]});
    assert.equal(h.requests.length, count + 1);
    assert.equal(h.requests.at(-1).url, '/webmail/api/listMessages');
});
