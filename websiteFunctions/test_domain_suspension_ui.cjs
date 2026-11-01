const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function controller() {
    const file = fs.readFileSync(path.join(__dirname, 'static/websiteFunctions/websiteFunctions.js'), 'utf8');
    const start = file.indexOf("app.controller('suspendWebsiteControl'");
    const end = file.indexOf('app.controller(', start + 20);
    const scope = {}, calls = [];
    const http = {post(url, data, config) {
        const call = {url, data, config};
        calls.push(call);
        return {then(success, error) {call.success = success; call.error = error;}};
    }};
    vm.runInNewContext(file.slice(start, end), {
        app: {controller(name, factory) {factory(scope, http);}},
        getCookie() {return 'fixture-csrf';}
    });
    return {scope, calls};
}

test('selection reads effective state and inherited suspension before allowing actions', () => {
    const {scope, calls} = controller();
    scope.websiteToBeSuspended = 'child.test';
    scope.showSuspendUnsuspend();
    assert.equal(scope.stateView, true);
    assert.equal(calls[0].url, '/websites/fetchWebsiteStatus');
    assert.equal(calls[0].data.websiteName, 'child.test');
    calls[0].success({data: {websiteStatus: 1, state: 'Suspended', parentSuspended: true}});
    assert.equal(scope.currentWebsiteState, 'Suspended');
    assert.equal(scope.parentSuspended, true);
    assert.equal(scope.stateView, false);
});

test('a late status response for another selection cannot overwrite current status', () => {
    const {scope, calls} = controller();
    scope.websiteToBeSuspended = 'child.test';
    scope.showSuspendUnsuspend();
    scope.websiteToBeSuspended = 'sibling.test';
    scope.showSuspendUnsuspend();
    calls[1].success({data: {websiteStatus: 1, state: 'Active', parentSuspended: false}});
    calls[0].success({data: {websiteStatus: 1, state: 'Suspended', parentSuspended: true}});
    assert.equal(scope.currentWebsiteState, 'Active');
    assert.equal(scope.parentSuspended, false);
});

test('restoring child under suspended parent truthfully shows resulting Suspended state', () => {
    const {scope, calls} = controller();
    scope.websiteToBeSuspended = 'child.test';
    scope.stateView = false;
    scope.state = 'Un-Suspend';
    scope.save();
    scope.save();
    assert.equal(calls.length, 1); // Prevent duplicate mutations.
    assert.equal(calls[0].url, '/websites/submitWebsiteStatus');
    assert.equal(calls[0].config.headers['X-CSRFToken'], 'fixture-csrf');
    calls[0].success({data: {websiteStatus: 1, state: 'Suspended', parentSuspended: true}});
    assert.equal(scope.finalStatus, 'Suspended');
    assert.equal(scope.parentSuspended, true);
    assert.equal(scope.websiteSuccess, false);
    assert.equal(scope.saving, false);
});

test('unknown outcome requires fresh status before repeating an operation', () => {
    const {scope, calls} = controller();
    scope.websiteToBeSuspended = 'child.test';
    scope.stateView = false;
    scope.state = 'Suspend';
    scope.save();
    calls[0].error();
    assert.equal(scope.stateView, true);
    scope.save();
    assert.equal(calls.length, 1);
    assert.equal(scope.couldNotConnect, false);
});

test('invalid or unchecked actions never reach mutation endpoint', () => {
    const {scope, calls} = controller();
    scope.websiteToBeSuspended = 'child.test';
    scope.state = 'Suspend';
    scope.save();
    scope.stateView = false;
    scope.state = 'bogus';
    scope.save();
    assert.equal(calls.length, 0);
});
