const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const path = require('path');
const source = fs.readFileSync(path.join(__dirname, 'static/websiteFunctions/websiteFunctions.js'), 'utf8');
let position = 0, controllers = 0;
while ((position = source.indexOf("app.controller('deleteWebsiteControl'", position)) !== -1) {
  const end = source.indexOf('\n});', position) + 4;
  const snippet = source.slice(position, end);
  for (const response of [
    {websiteDeleteStatus: 1, state: 'completed'},
    {websiteDeleteStatus: 2, state: 'pending', error_message: 'Wait and refresh.'},
    {websiteDeleteStatus: 0, state: 'failed', error_message: 'Failed.'},
    {websiteDeleteStatus: 2, state: 'awaiting_primary', error_message: 'Complete deletion on primary.'},
    {}, {websiteDeleteStatus: 1},
  ]) {
    const visible = {}, notices = [], scope = {websiteToBeDeleted: 'fixture.example'};
    let callback, failure;
    const context = {
      app: {controller(name, fn) { fn(scope, {post() {return {then(ok, bad) { callback = ok; failure = bad; }};}}); }},
      $(selector) {return {hide() {visible[selector] = false;}, show() {visible[selector] = true;}, fadeIn() {visible[selector] = true;}};},
      getCookie() {return 'fixture';}, PNotify: function(data) {notices.push(data);},
    };
    vm.runInNewContext(snippet, context);
    scope.deleteWebsiteFinal();
    callback({data: response});
    assert.strictEqual(visible['#websiteDeleteSuccess'], response.websiteDeleteStatus === 1 && response.state === 'completed');
    failure({status: 504});
    assert.strictEqual(visible['#websiteDeleteSuccess'], false);
    assert.ok(scope.errorMessage.includes('unknown'));
  }
  controllers++;
  position = end;
}
assert.strictEqual(controllers, 2);
console.log('Both website deletion controllers: completed, pending, failed, malformed, legacy and unknown-network states passed.');
