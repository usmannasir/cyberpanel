// Exercise the existing website-creation controller with fake HTTP responses.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../websiteFunctions/static/websiteFunctions/websiteFunctions.js'), 'utf8');
const start = source.indexOf("app.controller('createWebsite',");
assert(start >= 0);
const end = source.indexOf('\n});', start) + '\n});'.length;
assert(end > start);
const controllerSource = source.slice(start, end);

function fixture(status) {
    const requests = [];
    let controller;
    const context = {
        app: {controller(name, body) { assert.equal(name, 'createWebsite'); controller = body; }},
        getCookie() { return 'fixture'; },
        $() { return {css() {}}; },
    };
    vm.runInNewContext(controllerSource, context);
    const scope = {domainNameCreate: 'owned.example', adminEmail: 'admin@example.invalid',
        phpSelection: 'PHP 8.3', packageForWebsite: 'quota-package', websiteOwner: 'admin'};
    const http = {post(url, data) {
        requests.push(url);
        return {then(success) {
            if (url === '/websites/submitWebsiteCreation') {
                success({data: {createWebSiteStatus: 1, tempStatusPath: '/tmp/owned-status'}});
            } else {
                assert.equal(url, '/websites/installWordpressStatus');
                assert.equal(data.statusFile, '/tmp/owned-status');
                success({data: status});
            }
        }};
    }};
    let scheduled = 0;
    const timeout = () => { scheduled += 1; };
    timeout.cancel = () => {};
    controller(scope, http, timeout, {});
    scope.createWebsite();
    assert.deepEqual(requests, ['/websites/submitWebsiteCreation', '/websites/installWordpressStatus']);
    return {scope, scheduled};
}

const failure = fixture({abort: 1, installStatus: 0,
    error_message: ['Website was created, but its disk/inode quota could not be verified. [404]']});
assert.equal(failure.scope.success, true); // ng-hide keeps the success banner hidden.
assert.equal(failure.scope.errorMessageBox, false);
assert.match(String(failure.scope.errorMessage), /Website was created.*quota could not be verified/);
assert.equal(failure.scheduled, 0);
assert.equal(failure.scope.goBackDisable, false);

const pending = fixture({abort: 0, installStatus: 0, installationProgress: 70, currentStatus: 'Applying quotas'});
assert.equal(pending.scope.success, true);
assert.equal(pending.scheduled, 1);

const success = fixture({abort: 1, installStatus: 1, currentStatus: 'Successfully Installed.'});
assert.equal(success.scope.success, false);
assert.equal(success.scope.errorMessageBox, true);
assert.equal(success.scheduled, 0);
console.log('PASS: partial failure, pending state and success; no deletion request or premature success.');
