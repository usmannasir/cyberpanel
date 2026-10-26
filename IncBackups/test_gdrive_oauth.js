'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(__dirname + '/static/IncBackups/IncBackups.js', 'utf8');
const template = fs.readFileSync(__dirname + '/templates/IncBackups/ConfigureV2Backup.html', 'utf8');
assert.match(template, /block module_scripts/);
assert.match(template, /IncBackups\/IncBackups\.js.*gdrive-public-1/);
assert.match(template, /ng-disabled="!gdriveAvailable \|\| gdriveSetupPending"/);
assert.ok(!template.includes('ng-change="selectwebsite()"'), 'no undefined website-change handler');
const start = source.indexOf("app.controller('ConfigureV2Backup'");
const end = source.indexOf("app.controller('ScheduleV2Backup'", start);
assert.ok(start > 0 && end > start);
function fixture(blocked = false, enabled = true) {
    const calls = [], notices = [];
    const popup = {opener: {}, location: {}, closed: false, close() { this.closed = true; }};
    let success, failure, capabilitySuccess, capabilityFailure;
    const scope = {selwebsite: 'owned.example', accountName: 'qa-drive',
        client_id: 'synthetic.apps.googleusercontent.com', client_secret: 'SYNTHETIC-SECRET'};
    vm.runInNewContext(source.slice(start, end), {
        app: {controller(name, factory) {
            assert.equal(name, 'ConfigureV2Backup');
            factory(scope, {
                get(url) {assert.equal(url, '/IncrementalBackups/GDriveSetupStatus');
                    return {then(ok,bad) {capabilitySuccess=ok;capabilityFailure=bad;}};},
                post(...args) { calls.push(args); return {then(ok, bad) { success = ok; failure = bad; }}; }
            }, {});
        }},
        window: {open(url) {assert.equal(url, 'about:blank'); return blocked ? null : popup;}},
        getCookie(name) { assert.equal(name, 'csrftoken'); return 'synthetic-csrf'; },
        PNotify: function(options) { notices.push(options); }, URL,
    });
    if (enabled !== null) capabilitySuccess({data:{status:1,enabled}});
    return {scope, calls, popup, notices, success(data) {success({data});}, failure() {failure();},
        status(data) {capabilitySuccess({data});}, statusFailure() {capabilityFailure();}};
}
for (const enabled of [false, null]) {
    const disabled = fixture(false, enabled);
    disabled.scope.setupAccount();
    assert.equal(disabled.calls.length, 0, 'disabled or unchecked setup never registers');
}
for (const data of [{status:1,enabled:'true'},{status:0,enabled:true},null]) {
    const disabled = fixture(false,null); disabled.status(data); disabled.scope.setupAccount();
    assert.equal(disabled.calls.length,0,'malformed capability fails closed');
}
const unavailable = fixture(false,null); unavailable.statusFailure(); unavailable.scope.setupAccount();
assert.equal(unavailable.calls.length,0);
let f = fixture();
f.scope.setupAccount();
f.scope.setupAccount();
assert.equal(f.calls.length, 1, 'double click suppressed');
assert.equal(f.calls[0][0], '/IncrementalBackups/BeginV2GDriveSetup');
assert.equal(f.calls[0][1].client_secret, 'SYNTHETIC-SECRET');
assert.equal(f.calls[0][2].headers['X-CSRFToken'], 'synthetic-csrf');
assert.equal(f.popup.opener, null);
f.success({status: 1, authorization_url: 'https://platform.example.test/gDrive/v2/start?handoff=' + 'a'.repeat(43)});
assert.ok(!f.popup.location.href.includes('SYNTHETIC'));
assert.equal(f.scope.gdriveSetupPending, false);
assert.equal(f.scope.client_secret, '');
for (const value of [undefined, {status: 0, error_message: 'SYNTHETIC-SECRET'},
    {status: 1, authorization_url: 'http://example.test/gDrive?handoff='+'a'.repeat(43)},
    {status: 1, authorization_url: 'https://example.test/gDrive?handoff='+'a'.repeat(43)+'&client_secret=SYNTHETIC'},
    {status: 1, authorization_url: 'https://user:password@example.test/gDrive?handoff='+'a'.repeat(43)}]) {
    f = fixture(); f.scope.setupAccount(); f.success(value);
    assert.equal(f.popup.closed, true);
    assert.equal(f.scope.gdriveSetupPending, false);
    assert.equal(f.scope.client_secret, '');
    assert.equal(f.notices.length, 1);
    assert.ok(!JSON.stringify(f.notices).includes('SYNTHETIC'));
}
f = fixture(); f.scope.setupAccount(); f.failure();
assert.equal(f.popup.closed, true);
f.scope.setupAccount();
assert.equal(f.calls.length, 2, 'retry enabled after failure');
f = fixture(true); f.scope.setupAccount();
assert.equal(f.calls.length, 0, 'blocked popup must not register a handoff');
assert.equal(f.notices.length, 1);
console.log('OK: POST-only credentials, CSRF header, popup isolation, duplicate guard, URL validation, errors and retry');
