const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync(process.argv[2] || require('path').join(__dirname, 'static/manageSSL/manageSSL.js'), 'utf8');
const start = source.indexOf("app.controller('sslIssueCtrl'");
const end = source.indexOf('\n});', start) + 4;
assert.ok(start >= 0 && end > start);
for (const [response, title, type, success, detailReads] of [
  [{SSL: 1, outcome: 'issued'}, 'Success', 'success', true, 1],
  [{SSL: 1, outcome: 'renewed'}, 'Success', 'success', true, 1],
  [{SSL: 0, outcome: 'existing_certificate', retained_existing: true, warning: 'Existing date-valid certificate retained.', error_message: 'Existing date-valid certificate retained.'}, 'Existing certificate retained', 'warning', false, 1],
  [{SSL: 0, outcome: 'self_signed', warning: 'Self-signed fallback installed.', error_message: 'Self-signed fallback installed.'}, 'Self-signed certificate fallback', 'warning', false, 1],
  [{SSL: 0, outcome: 'existing_certificate', retained_existing: true, certificate_validity: 'expired', error_message: 'Existing certificate expired.'}, 'SSL Issuance Failed', 'error', false, 1],
  [{SSL: 0, outcome: 'failed', error_message: 'Issuance failed.'}, 'SSL Issuance Failed', 'error', false, 0],
]) {
  const notices = [], scope = {virtualHost: 'disposable.invalid'};
  let reads = 0, issueCallback;
  const context = {
    app: {controller(name, fn) {fn(scope, {post(url) {
      return {then(callback) {
        if (url === '/manageSSL/getSSLDetails') {reads++; callback({data: {status: 1, hasSSL: false}});}
        else {assert.strictEqual(url, '/manageSSL/issueSSL'); issueCallback = callback;}
      }};
    }});}},
    getCookie() {return 'fixture';},
    PNotify: function(data) {notices.push(data);},
    console: {error() {throw new Error('Unexpected console error');}},
  };
  vm.runInNewContext(source.slice(start, end), context);
  scope.issueSSL();
  issueCallback({data: response});
  assert.strictEqual(notices.at(-1).title, title);
  assert.strictEqual(notices.at(-1).type, type);
  assert.strictEqual(scope.sslIssued, !success);
  assert.strictEqual(scope.canNotIssue, success);
  assert.strictEqual(scope.sslIssuing, false);
  assert.strictEqual(reads, detailReads);
}
console.log('SSL live controller: issued, renewed, retained, self-signed, expired and failed outcomes passed.');
