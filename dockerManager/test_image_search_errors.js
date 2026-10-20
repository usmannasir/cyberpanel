// Exercise the real search callback with backend, HTTP and malformed responses.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(process.argv[2] || __dirname + '/static/dockerManager/dockerManager.js', 'utf8');
let start = source.indexOf('    function showImageSearchError(');
if (start < 0) start = source.indexOf('    $scope.searchImages = function');
const end = source.indexOf('    function populateTagList(', start);
assert(start >= 0 && end > start);
function search(response, rejected = false) {
    const notices = [];
    let loading = false;
    const scope = {searchString: 'nextcloud'};
    const context = {
        $scope: scope, delayTimer: null,
        console: {log() {}}, clearTimeout() {},
        setTimeout(fn) { fn(); return 1; },
        getCookie() { return 'fixture-csrf'; },
        $(selector) { return {
            show() { if (selector === '#imageLoading') loading = true; },
            hide() { if (selector === '#imageLoading') loading = false; }
        }; },
        PNotify: function (options) { notices.push(options); },
        $http: {post(url, data, config) {
            assert.equal(url, '/docker/searchImage');
            assert.equal(data.string, 'nextcloud');
            assert.equal(config.headers['X-CSRFToken'], 'fixture-csrf');
            return {then(success, failure) { (rejected ? failure : success)(response); }};
        }}
    };
    vm.runInNewContext(source.slice(start, end), context);
    scope.searchImages();
    assert.equal(loading, false, 'search spinner must stop');
    return {notices, scope};
}
const fallback = 'Unable to search Docker images. Please try again.';
const cases = [
    [{data: {status: 0, error_message: 'Docker not installed'}}, false, 'Docker not installed'],
    [{data: {searchImageStatus: 0, error_message: 'Registry unavailable', error: 'legacy'}}, false, 'Registry unavailable'],
    [{data: {searchImageStatus: 0, error: 'Legacy backend error'}}, false, 'Legacy backend error'],
    [{data: {error_message: '  '}}, false, fallback],
    [{data: null}, false, fallback],
    [{data: '<html>Bad gateway</html>'}, true, fallback],
    [{data: {error_message: 'Docker daemon not running or not responsive'}}, true, 'Docker daemon not running or not responsive'],
    [{status: 0}, true, fallback],
    [{data: {error_message: '<img src=x onerror=alert(1)>'}}, false, '<img src=x onerror=alert(1)>']
];
for (const [response, rejected, expected] of cases) {
    const {notices} = search(response, rejected);
    assert.equal(notices.length, 1);
    assert.equal(notices[0].text, expected);
    assert.equal(notices[0].text_escape, true, 'backend errors must render as text');
}
const matches = [{name: 'nextcloud', description: 'Official image'}];
const success = search({data: {searchImageStatus: 1, matches}});
assert.equal(success.notices.length, 0);
assert.equal(success.scope.images, matches);
console.log('10 Docker image-search cases passed, including success, HTTP failures and escaped errors.');
