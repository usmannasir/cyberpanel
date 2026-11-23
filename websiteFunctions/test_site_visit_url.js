const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const path = require('path');

// siteVisitURL() of both copies of the script: an absolute http:// address
// of the website, or of the sub-folder an application was installed in.
const copies = [
  path.join(__dirname, 'static/websiteFunctions/websiteFunctions.js'),
  path.join(__dirname, '..', 'static/websiteFunctions/websiteFunctions.js'),
];
for (const file of copies) {
  const source = fs.readFileSync(file, 'utf8');
  const start = source.indexOf('function siteVisitURL(');
  assert.ok(start !== -1, file);
  const context = {URL};
  vm.runInNewContext(source.slice(start, source.indexOf('\n}\n', start) + 2), context);
  const visit = context.siteVisitURL;

  assert.strictEqual(visit('shop.example.com'), 'http://shop.example.com/');
  assert.strictEqual(visit('shop.example.com', undefined), 'http://shop.example.com/');
  assert.strictEqual(visit('shop.example.com', ''), 'http://shop.example.com/');
  assert.strictEqual(visit(' shop.example.com\n', 'store'), 'http://shop.example.com/store/');
  assert.strictEqual(visit('shop.example.com', '/store/eu/'), 'http://shop.example.com/store/eu/');
  assert.strictEqual(visit('Shop.Example.com', 'store'), 'http://shop.example.com/store/');
  // A folder name is one path segment each, never a query, fragment or quote.
  assert.strictEqual(visit('shop.example.com', 'my store?x=1#top'),
    'http://shop.example.com/my%20store%3Fx%3D1%23top/');
  assert.strictEqual(visit('shop.example.com', '"><script>'), 'http://shop.example.com/%22%3E%3Cscript%3E/');
  assert.strictEqual(visit('shop.example.com', 'javascript:alert(1)'), 'http://shop.example.com/javascript%3Aalert(1)/');
  // Anything but a plain host name gives no address at all.
  for (const bad of ['', undefined, null, 'evil.example/x', 'user@evil.example', 'evil.example:8090',
                     'evil.example?x', 'evil.example#x', 'a b', '"onmouseover="x', 'javascript:alert(1)']) {
    const result = visit(bad);
    assert.ok(result === '' || /^http:\/\/[a-z0-9.-]+\/$/.test(result), String(bad) + ' -> ' + result);
    assert.ok(!/["'<> ]/.test(result), String(bad) + ' -> ' + result);
  }
  assert.strictEqual(visit('evil.example/x'), '');
  assert.strictEqual(visit('user@evil.example'), '');
  assert.strictEqual(visit('evil.example:8090'), '');
}
console.log('siteVisitURL: both copies give absolute http:// addresses with encoded sub-folders.');
