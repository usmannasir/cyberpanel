/* Run: node mailServer/test_email_limit_display.js */
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

// Execute the real controller; only its HTTP and Angular registration are seams.
const sourceDirectory = process.argv[2] || __dirname;
const script = fs.readFileSync(path.join(sourceDirectory, 'static/mailServer/mailServer.js'), 'utf8');
const start = script.indexOf("app.controller('EmailLimitsNew'");
const end = script.indexOf('/* Java script for EmailLimitsNew */', start);
assert.ok(start >= 0 && end > start);
let scope;
vm.runInNewContext(script.slice(start, end), {
    app: {controller(name, factory) {
        assert.equal(name, 'EmailLimitsNew');
        scope = {};
        factory(scope, {});
    }},
    console: {log() {}},
}, {timeout: 1000});

const template = fs.readFileSync(path.join(sourceDirectory, 'templates/mailServer/EmailLimits.html'), 'utf8');
const preview = template.slice(template.indexOf('<div class="preview-box">'), template.indexOf('<div class="limits-form">'));
const messages = [...preview.matchAll(/<span\b([^>]*)>([\s\S]*?)<\/span>/g)].map(match => ({
    expression: (match[1].match(/ng-if="([^"]+)"/) || [])[1],
    text: match[2].replace(/{%\s*trans\s*"([^"]+)"\s*%}/g, '$1')
        .replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim(),
}));
assert.ok(messages.length > 0, 'Real preview text must be present');

const cases = [
    ['saved positive', 10, '5m', true],
    ['saved zero', 0, '0m', true],
    ['missing/unreadable', null, null, false],
    ['saved zero with positive period', 0, '5m', true],
    ['second unavailable selection', null, null, false],
];
for (const [name, amount, duration, available] of cases) {
    scope.selectedEmail = 'mailbox@example.invalid';
    scope.emails = [{email: scope.selectedEmail, numberofEmails: amount, duration}];
    scope.selectForwardingEmail();
    assert.equal(scope.numberofEmails, amount, name);
    assert.equal(scope.duration, duration, name);
    assert.equal(scope.emailLimitAvailable, available, name);
    const shown = messages.filter(item => !item.expression ||
        vm.runInNewContext(`Boolean(${item.expression})`, scope)).map(item => ({
            text: item.text.replace(/\{\$\s*(\w+)\s*\$\}/g, (_, key) => scope[key] == null ? '' : String(scope[key])),
        }));
    assert.equal(shown.length, 1, name);
    if (available) {
        assert.ok(shown[0].text.includes(String(amount)), name);
        assert.ok(shown[0].text.includes(duration), name);
        assert.ok(!shown[0].text.includes('could not be read'), name);
    } else {
        assert.ok(shown[0].text.includes('could not be read'), name);
        assert.ok(!shown[0].text.includes('will be able to send'), name);
    }
}
const unselectedCases = [
    ['placeholder after saved selection', ''],
    ['unmatched mailbox after saved selection', 'other@example.invalid'],
    ['unset mailbox after saved selection', undefined],
];
for (const [name, selection] of unselectedCases) {
    scope.emails = [{email: 'mailbox@example.invalid', numberofEmails: 25, duration: '1h'}];
    scope.selectedEmail = 'mailbox@example.invalid';
    scope.selectForwardingEmail();
    assert.equal(scope.emailLimitAvailable, true, name + ' setup');
    scope.selectedEmail = selection;
    scope.selectForwardingEmail();
    assert.equal(scope.emailLimitAvailable, false, name);
    assert.equal(scope.numberofEmails, null, name);
    assert.equal(scope.duration, null, name);
    const shown = messages.filter(item => !item.expression ||
        vm.runInNewContext(`Boolean(${item.expression})`, scope));
    assert.equal(shown.length, 1, name);
    assert.ok(shown[0].text.includes('could not be read'), name);
}
console.log(`OK: ${cases.length + unselectedCases.length} controller/preview cases passed`);
