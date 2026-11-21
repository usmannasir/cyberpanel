'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const template = name => fs.readFileSync(path.join(__dirname, 'templates', 'multiServer', name), 'utf8');
let submitted = 0;
const form = { submit() { submitted++; } };
const script = name => template(name).match(/<script nonce="{{ nonce }}">([\s\S]+?)<\/script>/)[1];
vm.runInNewContext(script('post.html'), {
    document: { getElementById(id) { assert.equal(id, 'handoff'); return form; } }
});
assert.equal(submitted, 1);
let landed;
vm.runInNewContext(script('return.html'), {
    document: { getElementById(id) { assert.equal(id, 'finish'); return {href: '/multiserver/login/finish'}; } },
    location: {replace(value) { landed = value; }}
});
assert.equal(landed, '/multiserver/login/finish');
const control = template('selector.html');
assert.ok(control.includes('target="_blank" rel="noopener"'));
const onsubmit = control.match(/onsubmit="([^"]+)"/)[1];
for (const [server, shouldSubmit] of [['local', false], ['linked-node', true]]) {
    const result = vm.runInNewContext('(function(){' + onsubmit + '}).call(form)', {
        form: {elements: {server: {value: server}}}
    });
    assert.equal(result, shouldSubmit);
}
console.log('4 browser script checks passed');
