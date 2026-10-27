const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const test = require('node:test');
const source = fs.readFileSync(__dirname + '/static/websiteFunctions/syncMaster.js', 'utf8');
function setup() {
    const requests = [], timers = [], handlers = {}, progress = {style: {}};
    const scope = {$on: (name, callback) => handlers[name] = callback};
    const timeout = callback => { timers.push(callback); return callback; };
    timeout.cancel = callback => timers.splice(timers.indexOf(callback), 1);
    vm.runInNewContext(source, {
        app: {controller: (name, callback) => callback(scope, {post: (url, data, config) =>
            ({then: (resolve, reject) => requests.push({url, data, config, resolve, reject})})}, timeout)},
        document: {cookie: 'csrftoken=fixture', getElementById: id => id === 'childDomain'
            ? {textContent: 'stage.example'} : progress}, window: {location: {reload: () => {}}}
    });
    return {scope, requests, timers, handlers, progress};
}
test('confirmation and selection gate sync and prevent duplicate submission', () => {
    const t = setup(); t.scope.startSyncing(); assert.equal(t.requests.length, 0);
    t.scope.confirmed = true; t.scope.startSyncing(); assert.equal(t.requests.length, 0);
    t.scope.dbCheck = true; t.scope.startSyncing(); t.scope.startSyncing();
    assert.equal(t.requests.length, 1); assert.equal(t.requests[0].data.confirmed, true);
    assert.equal(t.requests[0].config.headers['X-CSRFToken'], 'fixture');
});
test('polls only returned status path and retains recovery location', () => {
    const t = setup(); Object.assign(t.scope, {confirmed: true, dbCheck: true}); t.scope.startSyncing();
    t.requests[0].resolve({data: {status: 1, tempStatusPath: '/home/cyberpanel/123'}});
    assert.equal(t.requests[1].data.statusFile, '/home/cyberpanel/123');
    t.requests[1].resolve({data: {abort: 0, currentStatus: 'Backing up', installationProgress: 15}});
    assert.equal(t.progress.style.width, '15%'); t.timers.shift()();
    t.requests[2].resolve({data: {abort: 1, installStatus: 1, installationProgress: 100,
        currentStatus: 'Completed. Recovery backup: /private-backup/fixture'}});
    assert.match(t.scope.currentStatus, /private-backup\/fixture/);
    assert.equal(t.scope.goBackDisable, false); assert.equal(t.timers.length, 0);
});
test('lost start response never resubmits a potentially active deployment', () => {
    const t = setup(); Object.assign(t.scope, {confirmed: true, dbCheck: true}); t.scope.startSyncing();
    t.requests[0].reject(); t.scope.startSyncing();
    assert.equal(t.requests.length, 1); assert.match(t.scope.syncError, /may still be running/);
});
test('lost poll and backend failures do not falsely report completion', () => {
    for (const failure of ['network', 'backend']) {
        const t = setup(); Object.assign(t.scope, {confirmed: true, dbCheck: true}); t.scope.startSyncing();
        t.requests[0].resolve({data: {status: 1, tempStatusPath: '/home/cyberpanel/123'}});
        if (failure === 'network') t.requests[1].reject();
        else t.requests[1].resolve({data: {abort: 1, installStatus: 0, error_message: ['Backup failed']}});
        assert.ok(t.scope.syncError); assert.equal(t.scope.goBackDisable, true);
        assert.equal(t.timers.length, 0); t.scope.startSyncing(); assert.equal(t.requests.length, 2);
    }
});
test('page explicitly loads its controller and warns about production changes', () => {
    const template = fs.readFileSync(__dirname + '/templates/websiteFunctions/syncMaster.html', 'utf8');
    assert.match(template, /block module_scripts/); assert.match(template, /websiteFunctions\/syncMaster.js/);
    assert.match(template, /ng-controller="syncWebsite"/); assert.match(template, /ng-model="confirmed"/);
    assert.match(template, /backup is required before changes start/);
});
