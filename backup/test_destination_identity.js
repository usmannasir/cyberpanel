/* Run the shipped controllers and template click expressions without a browser. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const template = fs.readFileSync(path.join(__dirname, 'templates/backup/backupDestinations.html'), 'utf8');

for (const asset of ['static/backup/backup.js', '../static/backup/backup.js']) {
    function harness() {
        let controller;
        const requests = [], notifications = [], scope = {};
        const sandbox = {
            app: {controller(name, callback) { if (name === 'backupDestinations') controller = callback; }},
            getCookie: () => 'csrf-token',
            PNotify: function(value) { notifications.push(value); }
        };
        vm.runInNewContext(fs.readFileSync(path.join(__dirname, asset), 'utf8'), sandbox);
        controller(scope, {post(url, data) {
            const request = {url, data};
            requests.push(request);
            return {then(success) { request.respond = body => success({data: body}); }};
        }});
        return {scope, requests, notifications};
    }

    for (const kind of ['SFTP', 'local']) {
        test(`${asset}: ${kind} row sends its own stable ID when names are duplicated`, () => {
            const h = harness();
            const click = Array.from(template.matchAll(/ng-click="([^"]*removeDestination[^\"]*)"/g))
                .map(match => match[1]).find(value => value.includes(`'${kind}'`));
            assert.ok(click, 'destination row has a delete action');
            for (const record of [{name: 'same', id: 41}, {name: 'same', id: 42}]) {
                vm.runInNewContext(click, {removeDestination: h.scope.removeDestination, record});
            }
            assert.equal(h.requests[0].url, '/backup/deleteDestination');
            assert.equal(h.requests[0].data.destinationID, 41);
            assert.equal(h.requests[1].data.destinationID, 42);
            assert.equal(h.requests[1].data.nameOrPath, 'same');
            assert.equal(h.requests[1].data.type, kind);
        });
    }

    test(`${asset}: failed deletion displays server error and refreshes the list`, () => {
        const h = harness();
        h.scope.removeDestination('SFTP', 'same', 42);
        h.requests[0].respond({status: 0, delStatus: 0, error_message: 'Destination no longer exists.'});
        assert.equal(h.notifications[0].type, 'error');
        assert.equal(h.notifications[0].text, 'Destination no longer exists.');
        assert.equal(h.requests[1].url, '/backup/getCurrentBackupDestinations');
    });
}
