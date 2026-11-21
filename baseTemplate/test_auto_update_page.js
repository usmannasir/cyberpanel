'use strict';
// The Version Management controller shows and saves automatic update settings.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');

const source = fs.readFileSync(path.join(__dirname, 'static/baseTemplate/custom-js/system-status.js'), 'utf8');
const STATE = {settings: {mode: 'install', hour: 4, email: 'admin@example.com'},
               release: {version: '3.0', build: 10, commit: 'a'.repeat(40)}, checked: 1795253405,
               checked_text: '21 Nov 2026 09:30 UTC', error: '',
               summary: 'Version 3.0.10 will be installed automatically at 04:00 server time.',
               server_time: '02:10', timezone: 'UTC'};
const flush = async () => { for (let i = 0; i < 6; i++) await Promise.resolve(); };

function page(answer) {
    const start = source.indexOf("app.controller('autoUpdateSettings'");
    const end = source.indexOf("app.controller('versionManagment'", start);
    assert.ok(start >= 0 && end > start);
    let controller;
    const posts = [];
    const context = {app: {controller(name, fn) { assert.equal(name, 'autoUpdateSettings'); controller = fn; }},
                     getCookie: () => 'csrf-token', Date, String};
    vm.runInNewContext(source.slice(start, end), context, {filename: 'system-status.js'});
    const scope = {};
    const http = {post(url, data, config) {
        posts.push({url, data: JSON.parse(JSON.stringify(data)), config});
        return answer(data);
    }};
    controller(scope, http);
    return {scope, posts};
}

test('settings and state are loaded from the server when the card is shown', async () => {
    const p = page(async () => ({data: {status: 1, autoUpdate: STATE}}));
    assert.equal(p.scope.autoUpdate.mode, 'off');
    assert.equal(p.scope.autoUpdateBusy, true);
    await flush();
    assert.deepEqual(p.posts.map(post => [post.url, post.data]), [['/base/autoUpdate', {action: 'status'}]]);
    assert.equal(p.posts[0].config.headers['X-CSRFToken'], 'csrf-token');
    assert.deepEqual(JSON.parse(JSON.stringify(p.scope.autoUpdate)), STATE.settings);
    assert.equal(p.scope.autoUpdateState.summary, STATE.summary);
    assert.equal(p.scope.autoUpdateState.releaseLabel, '3.0.10 (aaaaaaaaaaaa)');
    assert.equal(p.scope.autoUpdateState.serverTime, '02:10 UTC');
    assert.equal(p.scope.autoUpdateState.checkedLabel, '21 Nov 2026 09:30 UTC');
    assert.equal(p.scope.autoUpdateBusy, false);
    assert.equal(p.scope.autoUpdateLoaded, true);
    assert.equal(p.scope.autoUpdateHours.length, 24);
    assert.deepEqual(JSON.parse(JSON.stringify(p.scope.autoUpdateHours[4])), {value: 4, label: '04:00'});
});

test('the card has its own controller and the upgrade controller asks nothing about it', () => {
    const upgrade = source.slice(source.indexOf("app.controller('versionManagment'"),
                                 source.indexOf("app.controller('designtheme'"));
    assert.ok(!upgrade.includes('autoUpdate'));
    const template = fs.readFileSync(path.join(__dirname, 'templates/baseTemplate/versionManagment.html'), 'utf8');
    assert.equal((template.match(/ng-controller="autoUpdateSettings"/g) || []).length, 1);
    assert.match(template, /id="autoUpdateCard" ng-controller="autoUpdateSettings"/);
});

test('save sends exactly the three settings and shows the stored result', async () => {
    const p = page(async (data) => ({data: {status: 1, autoUpdate: data.action === 'save'
        ? Object.assign({}, STATE, {settings: {mode: data.mode, hour: data.hour, email: data.email}}) : STATE}}));
    await flush();
    p.scope.autoUpdate = {mode: 'notify', hour: 7, email: undefined};
    p.scope.saveAutoUpdate();
    await flush();
    assert.deepEqual(p.posts[1].data, {action: 'save', mode: 'notify', hour: 7, email: ''});
    assert.equal(p.scope.autoUpdateSaved, true);
    assert.equal(p.scope.autoUpdate.mode, 'notify');
    p.scope.checkAutoUpdate();
    await flush();
    assert.deepEqual(p.posts[2].data, {action: 'check'});
    assert.equal(p.scope.autoUpdateSaved, false);
});

test('a refusal or a lost connection is shown and the form stays usable', async () => {
    let p = page(async (data) => data.action === 'save'
        ? {data: {status: 0, error_message: 'Enter one valid e-mail address, or none.'}}
        : {data: {status: 1, autoUpdate: STATE}});
    await flush();
    p.scope.autoUpdate.email = 'not an address';
    p.scope.saveAutoUpdate();
    await flush();
    assert.equal(p.scope.autoUpdateError, 'Enter one valid e-mail address, or none.');
    assert.equal(p.scope.autoUpdateSaved, false);
    assert.equal(p.scope.autoUpdateBusy, false);
    assert.equal(p.scope.autoUpdate.email, 'not an address');
    p = page(async () => { throw new Error('offline'); });
    await flush();
    assert.match(p.scope.autoUpdateError, /could not be reached/);
    assert.equal(p.scope.autoUpdateBusy, false);
    p = page(async () => ({data: 'unexpected'}));
    await flush();
    assert.equal(p.scope.autoUpdateError, 'Automatic update settings are unavailable.');
});
