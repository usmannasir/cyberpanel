'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const root = path.resolve(__dirname, '..');
for (const relative of ['firewall/static/firewall/firewall.js', 'static/firewall/firewall.js']) {
  const controllers = {};
  const elements = new Map();
  function jquery(selector) {
    if (typeof selector === 'object') return selector;
    if (!elements.has(selector)) elements.set(selector, {
      checked: false,
      change(handler) { this.handler = handler; },
      prop(name, value) {
        if (arguments.length === 1) return this[name];
        this[name] = value;
        if (this.handler) this.handler.call(this);
        return this;
      },
    });
    return elements.get(selector);
  }
  const context = {app:{controller(name, handler) {controllers[name] = handler;}},
                   getCookie:()=>'fixture', $:jquery};
  vm.runInNewContext(fs.readFileSync(path.join(root, relative), 'utf8'), context);
  const calls = [];
  const http = {post(url, data) {
    const call = {url, data}; calls.push(call);
    return {then(resolve, reject) {call.resolve=resolve;call.reject=reject;}};
  }};
  const scope = {};
  controllers.firewallController(scope, http);
  const request = calls.find(c=>c.url==='/firewall/getCurrentRules');
  assert(request, 'firewall inventory request');
  request.reject({});
  assert.strictEqual(scope.firewalldRead, true);
  assert.strictEqual(scope.rulesLoading, true);
  assert.strictEqual(scope.couldNotConnect, false);
  request.resolve({data:{fetchStatus:1,data:'[]',firewalld:{runtime:'runtime fixture',permanent:'permanent fixture'}}});
  assert.strictEqual(scope.firewalld.runtime, 'runtime fixture');
  assert.strictEqual(scope.firewalld.permanent, 'permanent fixture');

  calls.length=0;
  controllers.modSecRulesPack({}, http, callback=>callback(), {});
  calls.find(c=>c.url==='/firewall/getOWASPAndComodoStatus').resolve({
    data:{modSecInstalled:1,owaspInstalled:0,comodoInstalled:0}
  });
  assert.strictEqual(calls.filter(c=>c.url==='/firewall/installModSecRulesPack').length,0,
                     'status refresh must not change WAF rules');
  elements.get('#owaspInstalled').prop('checked',true);
  elements.get('#comodoInstalled').prop('checked',true);
  assert.deepStrictEqual(calls.filter(c=>c.url==='/firewall/installModSecRulesPack').map(c=>c.data.packName),
                         ['installOWASP','installComodo'], 'first manual toggle must work');
  console.log(relative + ': inventory errors/readback and WAF toggle compatibility passed');
}
