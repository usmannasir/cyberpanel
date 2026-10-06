const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const test = require('node:test');
const source = fs.readFileSync(__dirname + '/static/websiteFunctions/websiteFunctions.js', 'utf8');
const start = source.indexOf('    // Production sync owns its status path;');
const code = source.slice(start, source.indexOf('    $scope.CreateBackup = function', start));
function setup() {
    const requests = [], timers = [], handlers = {};
    const scope = { $on: (name, callback) => handlers[name] = callback };
    const timeout = callback => { timers.push(callback); return callback; };
    timeout.cancel = callback => { const i = timers.indexOf(callback); if (i >= 0) timers.splice(i, 1); };
    const context = { $scope: scope, $timeout: timeout, DeploytoProductionID: 2,
        getCookie: () => 'csrf', statusFile: '/backup/unrelated',
        $: selector => ({ html: () => '1', on: (name, callback) => handlers[name] = callback, off: () => {} }),
        $http: { post: (url, data, config) => ({ then: (resolve, reject) => requests.push({url, data, config, resolve, reject}) }) }
    };
    vm.runInNewContext(code, context);
    return {scope, requests, timers, handlers};
}
test('confirmation gates deployment and double clicks send only one request', () => {
    const t = setup(); t.scope.FinalDeployToProduction(); assert.equal(t.requests.length, 0);
    t.scope.productionSync.acknowledged = true;
    t.scope.FinalDeployToProduction(); t.scope.FinalDeployToProduction();
    assert.equal(t.requests.length, 1);
    assert.equal(t.requests[0].data.WPid, '1'); assert.equal(t.requests[0].data.StagingID, 2);
    assert.equal(t.requests[0].config.headers['X-CSRFToken'], 'csrf');
});
test('sync polls its own status, completes once, and blocks closing while active', () => {
    const t = setup(); t.scope.productionSync.acknowledged = true; t.scope.FinalDeployToProduction();
    let prevented = false; t.handlers['hide.bs.modal.productionSync']({preventDefault: () => prevented = true});
    assert.equal(prevented, true);
    t.requests[0].resolve({data: {status: 1, tempStatusPath: '/sync/123'}});
    assert.equal(t.requests[1].data.statusFile, '/sync/123');
    t.requests[1].resolve({data: {abort: 0, installationProgress: '60', currentStatus: 'Copying content'}});
    assert.equal(t.scope.productionSync.progress, 60); t.timers.shift()();
    assert.equal(t.requests[2].data.statusFile, '/sync/123');
    t.requests[2].resolve({data: {abort: 1, installStatus: 1}});
    assert.equal(t.scope.productionSync.complete, true); assert.equal(t.scope.productionSync.busy, false);
    assert.equal(t.scope.productionSync.progress, 100); assert.equal(t.timers.length, 0);
});
test('poll failure does not submit another potentially destructive sync', () => {
    const t = setup(); t.scope.productionSync.acknowledged = true; t.scope.FinalDeployToProduction();
    t.requests[0].resolve({data: {status: 1, tempStatusPath: '/sync/123'}}); t.requests[1].reject();
    assert.match(t.scope.productionSync.error, /may still be running/);
    t.scope.FinalDeployToProduction(); assert.equal(t.requests.length, 2);
});
test('terminal server error is visible and does not report success', () => {
    const t = setup(); t.scope.productionSync.acknowledged = true; t.scope.FinalDeployToProduction();
    t.requests[0].resolve({data: {status: 1, tempStatusPath: '/sync/123'}});
    t.requests[1].resolve({data: {abort: 1, installStatus: 0, error_message: 'Database import failed'}});
    assert.equal(t.scope.productionSync.error, 'Database import failed');
    assert.equal(t.scope.productionSync.busy, false); assert.notEqual(t.scope.productionSync.complete, true);
});
test('the staging button target has one scoped confirmation dialog', () => {
    const template = fs.readFileSync(__dirname + '/templates/websiteFunctions/WPsiteHome.html', 'utf8');
    assert.equal((template.match(/id="DeployToProduction"/g) || []).length, 1);
    assert.ok(template.indexOf('id="DeployToProduction"') > template.indexOf('ng-controller="WPsiteHome"'));
    assert.match(template, /ng-click="FinalDeployToProduction\(\)"/);
    assert.match(template, /ng-model="productionSync.acknowledged"/);
    assert.match(template, /replaces the production database/);
});
