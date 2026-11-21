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
// The control opens the same page on the chosen server. It must not read as the target of a form below it.
// Beside a form it says so in words; in the header, where there is no room, the tooltip does.
assert.ok(control.includes('{% if placement == "create" %}{% trans "Open this page on another server" %}{% else %}'));
assert.ok(control.includes('title="{% trans "Open this page on another server" %}"'));
assert.ok(control.includes('{% if placement == "create" %}<small>{% trans "The form on this page always applies to this server." %}'));
// It leaves this page instead of opening a second one beside a form that would still look aimed elsewhere.
assert.ok(!control.includes('target='));
const chooser = control.match(/<form class="ms-server-selector"[\s\S]+?<\/form>/)[0];
assert.ok(/^<form class="ms-server-selector" method="post" action="{% url 'msSelect' %}" ng-non-bindable>/.test(chooser));
assert.ok(!/<script/i.test(control));
// Without scripting the choice is sent with a button; with it, by choosing.
assert.ok(/<noscript><button type="submit"[^>]*>{% trans "Open" %}<\/button><\/noscript>/.test(chooser));
const onchange = chooser.match(/<select [^>]*onchange="([^"]+)"/)[1];
for (const [server, shouldLeave] of [['local', false], ['linked-node', true]]) {
    const sent = [];
    const select = {value: server, form: {submit() { sent.push(select.value); }}};
    vm.runInNewContext('(function(){' + onchange + '}).call(select)', {select});
    assert.deepEqual(sent, shouldLeave ? [server] : []);
    // Whatever was chosen, what stays on this page says "This server".
    assert.equal(select.value, 'local');
}
console.log('browser script checks passed');
