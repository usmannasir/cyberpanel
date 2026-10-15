const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const controllers = {};
let elements;
let submissions;
vm.runInNewContext(fs.readFileSync(path.join(__dirname, 'static/databases/databases.js'), 'utf8'), {
    app: {controller: (name, fn) => {controllers[name] = fn;}},
    getCookie: () => 'qa-csrf',
    document: {
        createElement: tag => {
            const element = {tag, children: [], appendChild(child) {this.children.push(child);},
                submit() {submissions.push(this);}};
            elements.push(element);
            return element;
        },
        body: {appendChild: () => {}},
    },
});
function fixture() {
    elements = [];
    submissions = [];
    const scope = {};
    const posts = [];
    let yes, no;
    controllers.phpMyAdmin(scope, {post: (url, data, config) => {
        posts.push({url, data, config});
        return {then: (success, failure) => {yes = success; no = failure;}};
    }}, {});
    scope.generateAccess();
    assert.equal(scope.phpMyAdminPending, true);
    scope.generateAccess();
    assert.equal(posts.length, 1);
    assert.equal(posts[0].url, '/dataBases/generateAccess');
    assert.equal(posts[0].config.headers['X-CSRFToken'], 'qa-csrf');
    return {scope, posts, success: response => yes(response), failure: () => no({})};
}
for (const response of [undefined, {}, {data: {status: 0, error_message: 'private backend detail'}},
        {data: {status: 1}}, {data: {status: 1, username: 'admin', token: ''}}]) {
    const f = fixture();
    f.success(response);
    assert.equal(f.scope.phpMyAdminPending, false);
    assert.equal(f.scope.cyberPanelLoading, true);
    assert.match(f.scope.phpMyAdminError, /Unable to generate/);
    assert(!f.scope.phpMyAdminError.includes('private backend detail'));
    assert.equal(submissions.length, 0);
    f.scope.generateAccess();
    assert.equal(f.posts.length, 2);
    assert.equal(f.scope.phpMyAdminError, '');
}
{
    const f = fixture();
    f.failure();
    assert.equal(f.scope.phpMyAdminPending, false);
    assert.equal(f.scope.cyberPanelLoading, true);
    assert.match(f.scope.phpMyAdminError, /request failed/);
    assert.equal(submissions.length, 0);
}
{
    const f = fixture();
    f.success({data: {status: 1, username: 'qa-admin', token: 'test-only-token'}});
    assert.equal(f.scope.phpMyAdminPending, true);
    assert.equal(f.scope.phpMyAdminError, '');
    assert.equal(submissions.length, 1);
    assert.equal(submissions[0].method, 'post');
    assert.equal(submissions[0].action, '/phpmyadmin/phpmyadminsignin.php');
    assert.deepEqual(submissions[0].children.map(x => [x.name, x.value]),
        [['username', 'qa-admin'], ['token', 'test-only-token']]);
}
const template = fs.readFileSync(path.join(__dirname, 'templates/databases/phpMyAdmin.html'), 'utf8');
assert(template.includes('ng-disabled="phpMyAdminPending"'));
assert(template.includes('ng-click="generateAccess()"'));
assert(template.includes('role="alert"'));
assert(template.includes('ng-bind="phpMyAdminError"'));
console.log('phpMyAdmin UI checks passed: rejection, network, malformed/empty response, duplicate, retry, safe feedback, POST handoff and template.');
