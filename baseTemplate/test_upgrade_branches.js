const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, 'templates/baseTemplate/versionManagment.html'), 'utf8');
const start = source.indexOf('function populateBranches(branches)');
const end = source.indexOf('// Call the function to get all branches', start);
assert.ok(start >= 0 && end > start);
function fixture(fetch) {
    const select = {options: [{value: 'stable'}, {value: 'v3.0.8'}],
                    appendChild(option) { this.options.push(option); }};
    const context = {document: {getElementById: () => select, createElement: () => ({})},
                     fetch, console: {error() {}}, Set, Array};
    vm.createContext(context);
    vm.runInContext(source.slice(start, end), context);
    return {context, values: () => select.options.map(option => option.value)};
}
test('actual branch population preserves fallback and deduplicates valid names', () => {
    const f = fixture();
    f.context.populateBranches(['v3.0.8', 'v3.0.9', 'v3.0.9', 'stable',
                                'v3.0-dev', 'v3.0-version-counter', null, {}, 'v3.0?bad']);
    assert.deepEqual(f.values(), ['stable', 'v3.0.8', 'v3.0.9']);
});
test('rate limit retains rendered fallback without parsing the failure body', async () => {
    const f = fixture(async () => ({ok: false, json() { throw Error('must not parse'); }}));
    await f.context.getBranches('https://api.github.com/test', [], 1);
    assert.deepEqual(f.values(), ['stable', 'v3.0.8']);
});
test('invalid data and transport/JSON failures retain rendered choices', async () => {
    for (const payload of [{message: 'rate limit'}, [null], [{name: 123}]]) {
        const f = fixture(async () => ({ok: true, json: async () => payload}));
        await f.context.getBranches('https://api.github.com/test', [], 1);
        assert.deepEqual(f.values(), ['stable', 'v3.0.8']);
    }
    for (const fetch of [
        async () => { throw Error('offline'); },
        async () => ({ok: true, json: async () => { throw Error('invalid JSON'); }})
    ]) {
        const f = fixture(fetch);
        await f.context.getBranches('https://api.github.com/test', [], 1);
        assert.deepEqual(f.values(), ['stable', 'v3.0.8']);
    }
});
test('real paginated function appends unique branches and retains fallback', async () => {
    const pages = [[{name: 'v3.0.8'}, {name: 'v3.0.9'}], [{name: 'v3.0.9'}], []];
    let calls = 0;
    const f = fixture(async () => ({ok: true, json: async () => pages[calls++]}));
    await f.context.getBranches('https://api.github.com/test', [], 1);
    assert.equal(calls, 3);
    assert.deepEqual(f.values(), ['stable', 'v3.0.8', 'v3.0.9']);
});
test('pagination is bounded when the provider never returns an empty page', async () => {
    let calls = 0;
    const f = fixture(async () => {
        calls++;
        return {ok: true, json: async () => [{name: 'v3.0.9'}]};
    });
    await f.context.getBranches('https://api.github.com/test', [], 1);
    assert.equal(calls, 20);
    assert.deepEqual(f.values(), ['stable', 'v3.0.8', 'v3.0.9']);
});
