const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const controllers = {};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, 'static/databases/databases.js'), 'utf8'), {
    app: { controller: (name, fn) => { controllers[name] = fn; } },
    getCookie: () => 'qa-csrf',
});
function fixture() {
    const scope = {};
    const posts = [];
    let success, failure;
    const http = { post: (url, data, config) => {
        posts.push({ url, data, config });
        return { then: (yes, no) => { success = yes; failure = no; } };
    } };
    controllers.listDBs(scope, http);
    scope.changePassword('qa_user');
    assert.equal(scope.changePasswordBox, false);
    assert.equal(scope.dbUsername, 'qa_user');
    return { scope, posts, success: x => success(x), failure: () => failure({}) };
}
{
    const f = fixture();
    f.scope.changePasswordBtn();
    assert.equal(f.posts.length, 0);
    assert.equal(f.scope.changePasswordBox, false);
    assert.match(f.scope.errorMessage, /Enter a new/);
}
for (const outcome of ['success', 'rejected', 'network']) {
    const f = fixture();
    f.scope.dbPassword = 'test-only-not-a-real-credential';
    f.scope.changePasswordBtn();
    assert.equal(f.scope.passwordChangePending, true);
    assert.equal(f.scope.changePasswordBox, false);
    f.scope.changePasswordBtn();
    assert.equal(f.posts.length, 1);
    assert.equal(f.posts[0].url, '/dataBases/changePassword');
    assert.equal(f.posts[0].data.dbUserName, 'qa_user');
    assert.equal(f.posts[0].config.headers['X-CSRFToken'], 'qa-csrf');
    if (outcome === 'network') f.failure();
    else f.success({data: {changePasswordStatus: outcome === 'success' ? 1 : 0,
                         error_message: 'QA rejection'}});
    assert.equal(f.scope.passwordChangePending, false);
    assert.equal(f.scope.changePasswordBox, outcome === 'success');
    if (outcome === 'success') assert.equal(f.scope.dbPassword, '');
    else assert.equal(f.scope.notificationsBox, false);
}
const template = fs.readFileSync(path.join(__dirname, 'templates/databases/listDataBases.html'), 'utf8');
assert(!template.includes('originalChangePasswordBtn'));
assert(!template.includes('setTimeout('));
assert(template.includes('ng-disabled="passwordChangePending"'));
console.log('Database password UI checks passed: open, empty, pending, duplicate, success, rejection, network, template.');
