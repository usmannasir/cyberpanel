/* Run: node manageSSL/test_ssl_status_templates.js */
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

// Inspect the real status elements and evaluate their inherited ng-if bindings
// with JavaScript semantics. Browser acceptance separately exercises Angular.
function statusElements(filename) {
    const html = fs.readFileSync(filename, 'utf8')
        .replace(/{%\s*trans\s+"([^"]+)"\s*%}/g, '$1')
        .replace(/{%[\s\S]*?%}/g, '');
    const stack = [];
    const result = [];
    const voidTags = new Set(['area', 'base', 'br', 'col', 'embed', 'hr', 'img',
        'input', 'link', 'meta', 'param', 'source', 'track', 'wbr']);
    for (const token of html.match(/<[^>]*>|[^<]+/g) || []) {
        const close = token.match(/^<\/([a-z][\w-]*)\s*>$/i);
        if (close) {
            const index = stack.map(node => node.tag).lastIndexOf(close[1].toLowerCase());
            if (index >= 0) stack.splice(index);
            continue;
        }
        const open = token.match(/^<([a-z][\w-]*)\b([^>]*)>/i);
        if (open) {
            const condition = open[2].match(/\bng-if="([^"]+)"/);
            const node = {
                tag: open[1].toLowerCase(),
                conditions: stack.flatMap(parent => parent.condition ? [parent.condition] : []),
                condition: condition && condition[1],
                text: '',
            };
            if (node.condition) node.conditions.push(node.condition);
            if (node.tag === 'span') result.push(node);
            if (!voidTags.has(node.tag) && !token.endsWith('/>')) stack.push(node);
            continue;
        }
        if (!token.startsWith('<')) {
            for (const node of stack) node.text += token;
        }
    }
    return result.map(node => ({...node, text: node.text.replace(/\s+/g, ' ').trim()}))
        .filter(node => ['Active', 'Expired', 'Not yet valid'].includes(node.text));
}

const cases = [
    ['valid', {hasSSL: true, validityStatus: 'valid', days: '60'}, ['Active']],
    ['expired', {hasSSL: true, validityStatus: 'expired', days: '-31'}, ['Expired']],
    ['exact expiry', {hasSSL: true, validityStatus: 'expired', days: '0'}, ['Expired']],
    ['less than one day', {hasSSL: true, validityStatus: 'valid', days: '0'}, ['Active']],
    ['future validity', {hasSSL: true, validityStatus: 'not_yet_valid', days: '30'}, ['Not yet valid']],
    ['missing certificate', {hasSSL: false}, []],
    ['malformed certificate', {hasSSL: false, error_message: 'Invalid PEM'}, []],
];

let checked = 0;
for (const template of ['manageSSL.html', 'v2ManageSSL.html']) {
    const elements = statusElements(path.join(__dirname, 'templates', 'manageSSL', template));
    assert.ok(elements.length > 0, `${template}: status elements were not found`);
    for (const [name, sslDetails, expected] of cases) {
        const shown = elements.filter(node => node.conditions.every(expression =>
            vm.runInNewContext(`Boolean(${expression})`, {sslDetails}, {timeout: 100})
        )).map(node => node.text);
        assert.deepEqual(shown, expected, `${template}: ${name}`);
        checked++;
    }
}
console.log(`OK: ${checked} SSL status template cases passed`);
