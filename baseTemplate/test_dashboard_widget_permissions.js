'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');

const root = process.env.DASHBOARD_SOURCE_ROOT || path.dirname(__dirname);
const source = fs.readFileSync(path.join(root, 'baseTemplate/static/baseTemplate/custom-js/system-status.js'), 'utf8');
const adminURLs = new Set([
    '/base/getTopProcesses', '/base/getRecentSSHLogins', '/base/getRecentSSHLogs',
    '/base/getTrafficStats', '/base/getDiskIOStats', '/base/getCPULoadGraph'
]);
const flush = async () => { for (let i = 0; i < 6; i++) await Promise.resolve(); };

// Register the exact application controllers without executing other controllers.
// HTTP, chart rendering and the clock are inert; no server, process or network is used.
function dashboard(options = {}) {
    const controllers = new Map(), requests = [], errors = [], timers = [], responses = new Map();
    let clock = 0, chartCount = 0, destroyedCharts = 0, resolveACL, rejectACL;
    const acl = new Promise((resolve, reject) => { resolveACL = resolve; rejectACL = reject; });
    const app = {config() {}, filter() {}, controller(name, fn) { controllers.set(name, fn); }};
    const schedule = (fn, delay = 0) => { const timer = {fn, due: clock + delay}; timers.push(timer); return timer; };
    const http = {
        get(url) {
            requests.push({method: 'GET', url});
            if (url === '/base/getAdminStatus') return acl;
            if (responses.has(url)) return responses.get(url)();
            if (url === '/base/getDashboardStats') return Promise.resolve({data: {status: 1, total_users: 1, total_dbs: 2}});
            if (url === '/base/getRecentSSHLogins') return Promise.resolve({data: {logins: []}});
            if (url === '/base/getRecentSSHLogs') return Promise.resolve({data: {logs: []}});
            return Promise.resolve({data: {status: 0}});
        },
        post(url) { requests.push({method: 'POST', url}); return Promise.resolve({data: {status: 0}}); }
    };
    const context = vm.createContext({
        app,
        console: {log() {}, warn() {}, error(...args) { errors.push(args); }},
        document: {cookie: '', getElementById(id) { return options.missingCanvas === id ? null : {getContext() { return options.nullContext ? null : {}; }}; }, addEventListener() {}},
        window: {}, setTimeout: schedule, $() { return {on() {}}; },
        Chart: function(context, config) {
            chartCount++;
            if (chartCount === options.failChart) throw new Error('Controlled chart initialization failure');
            this.data = config.data; this.resize = this.update = () => {};
            this.destroy = () => { destroyedCharts++; };
        }
    });
    if (options.missingChart) delete context.Chart;
    const start = source.indexOf("app.controller('dashboardStatsController'");
    assert.ok(start >= 0);
    assert.equal(source.indexOf("app.controller(", start + 1), -1);
    vm.runInContext(source.slice(start), context, {filename: 'system-status.js'});
    const scope = {};
    assert.equal(typeof controllers.get('dashboardStatsController'), 'function');
    controllers.get('dashboardStatsController')(scope, http, schedule);
    return {
        scope, requests, errors, responses,
        get chartCount() { return chartCount; },
        get destroyedCharts() { return destroyedCharts; },
        get windowChart() { return context.window.trafficChart; },
        adminRequests() { return requests.filter(r => adminURLs.has(r.url)); },
        count(url) { return requests.filter(r => r.url === url).length; },
        async resolve(data) { resolveACL({data}); await flush(); },
        async reject() { rejectACL({status: 503}); await flush(); },
        async advance(ms) {
            const end = clock + ms;
            for (let step = 0; step < 1000; step++) {
                timers.sort((a, b) => a.due - b.due);
                if (!timers.length || timers[0].due > end) { clock = end; await flush(); return; }
                const timer = timers.shift(); clock = timer.due; timer.fn(); await flush();
            }
            throw new Error('Unbounded fixture clock');
        }
    };
}

test('initial state hides admin activity and does not send privileged requests', async () => {
    const d = dashboard();
    assert.equal(d.scope.hideSystemCharts, true);
    assert.equal(d.adminRequests().length, 0);
    assert.equal(d.chartCount, 0);
});

test('slow permission lookup does not race initial or periodic polling', async () => {
    const d = dashboard(); await d.advance(6500);
    assert.equal(d.count('/base/getAdminStatus'), 1);
    assert.equal(d.adminRequests().length, 0);
    assert.equal(d.chartCount, 0);
    assert.ok(d.count('/base/getDashboardStats') >= 3);
    assert.equal(d.scope.totalDBs, 2);
});

test('limited account keeps own dashboard counts but never fetches admin widgets', async () => {
    const d = dashboard(); await d.advance(500); await d.resolve({admin: 0}); await d.advance(6000);
    assert.equal(d.adminRequests().length, 0);
    assert.equal(d.requests.filter(r => r.method === 'POST').length, 0);
    assert.equal(d.scope.hideSystemCharts, true);
    assert.equal(d.chartCount, 0);
    assert.equal(d.scope.statsLoaded, true);
});

test('failed permission lookup remains disabled while ordinary stats continue', async () => {
    const d = dashboard(); await d.advance(500); await d.reject(); await d.advance(6000);
    assert.equal(d.adminRequests().length, 0);
    assert.equal(d.scope.hideSystemCharts, true);
    assert.ok(d.count('/base/getDashboardStats') >= 3);
});

for (const [name, data] of [['missing', {}], ['null', null], ['string', {admin: '1'}], ['boolean', {admin: true}], ['other number', {admin: 2}]]) {
    test('permission response '+name+' does not grant admin widgets', async () => {
        const d = dashboard(); await d.advance(500); await d.resolve(data); await d.advance(4000);
        assert.equal(d.adminRequests().length, 0);
        assert.equal(d.scope.hideSystemCharts, true);
    });
}

test('manual refresh callbacks cannot bypass unresolved or denied permissions', async () => {
    const d = dashboard();
    for (const key of ['refreshTopProcesses', 'refreshSSHLogins', 'refreshSSHLogs']) d.scope[key]();
    await d.advance(500); await d.resolve({admin: 0});
    for (const key of ['refreshTopProcesses', 'refreshSSHLogins', 'refreshSSHLogs']) d.scope[key]();
    await flush(); assert.equal(d.adminRequests().length, 0);
});

test('authorized account starts charts and all widgets only after positive permission', async () => {
    const d = dashboard(); await d.advance(4500);
    assert.equal(d.adminRequests().length, 0);
    await d.resolve({admin: 1});
    assert.equal(d.scope.hideSystemCharts, false);
    assert.equal(d.chartCount, 3);
    for (const url of adminURLs) assert.equal(d.count(url), 1, url);
    await d.advance(2000);
    assert.equal(d.count('/base/getTopProcesses'), 2);
    assert.equal(d.count('/base/getRecentSSHLogins'), 1);
    assert.equal(d.count('/base/getRecentSSHLogs'), 1);
    for (const url of ['/base/getTrafficStats', '/base/getDiskIOStats', '/base/getCPULoadGraph']) assert.equal(d.count(url), 2, url);
});

test('permitted widget failures remain visible and are not turned into successful data', async () => {
    const d = dashboard();
    for (const url of ['/base/getTopProcesses', '/base/getRecentSSHLogins', '/base/getRecentSSHLogs']) d.responses.set(url, () => Promise.reject({status: 500}));
    await d.advance(500); await d.resolve({admin: 1});
    assert.equal(d.scope.errorTopProcesses, 'Failed to load top processes.');
    assert.equal(d.scope.errorSSHLogins, 'Failed to load SSH logins.');
    assert.equal(d.scope.errorSSHLogs, 'Failed to load SSH logs.');
    assert.equal(d.errors.length, 2);
});

test('admin-only response disables later periodic and manual widget requests', async () => {
    const d = dashboard();
    d.responses.set('/base/getTrafficStats', () => Promise.resolve({data: {admin_only: true}}));
    await d.advance(500); await d.resolve({admin: 1});
    const count = d.adminRequests().length;
    assert.equal(d.scope.hideSystemCharts, true);
    await d.advance(6000);
    for (const key of ['refreshTopProcesses', 'refreshSSHLogins', 'refreshSSHLogs']) d.scope[key]();
    assert.equal(d.adminRequests().length, count);
    assert.ok(d.count('/base/getDashboardStats') >= 3);
});

test('permitted widget data still populates its loading states and rows', async () => {
    const d = dashboard();
    d.responses.set('/base/getTopProcesses', () => Promise.resolve({data: {status: 1, processes: [{pid: 42}]}}));
    d.responses.set('/base/getRecentSSHLogins', () => Promise.resolve({data: {logins: [{user: 'fixture'}]}}));
    d.responses.set('/base/getRecentSSHLogs', () => Promise.resolve({data: {logs: [{message: 'fixture'}]}}));
    await d.advance(500); await d.resolve({admin: 1});
    assert.equal(d.scope.topProcesses[0].pid, 42);
    assert.equal(d.scope.sshLoginsPaginated[0].user, 'fixture');
    assert.equal(d.scope.sshLogsPaginated[0].message, 'fixture');
    assert.equal(d.scope.loadingTopProcesses, false);
    assert.equal(d.scope.loadingSSHLogins, false);
    assert.equal(d.scope.loadingSSHLogs, false);
});

test('activity board and SSH modal use the server-provided admin template condition', () => {
    const text = fs.readFileSync(path.join(root, 'baseTemplate/templates/baseTemplate/homePage.html'), 'utf8');
    function enclosingIf(marker) {
        const at = text.indexOf(marker); assert.ok(at >= 0);
        const stack = [];
        for (const match of text.slice(0, at).matchAll(/{%\s*(if\s+[^%]+|endif)\s*%}/g)) {
            const tag = match[1].trim();
            if (tag === 'endif') stack.pop(); else stack.push(tag);
        }
        return stack;
    }
    assert.ok(enclosingIf('class="activity-section"').includes('if admin'));
    assert.ok(enclosingIf('id="ssh-activity-modal"').includes('if admin'));
    assert.ok(!enclosingIf('class="insights-grid"').includes('if admin'));
    assert.match(text, /class="activity-section"[^>]*ng-hide="hideSystemCharts"[^>]*ng-cloak/);
});

test('existing single dashboard script has a cache suffix for this change', () => {
    const text = fs.readFileSync(path.join(root, 'baseTemplate/templates/baseTemplate/index.html'), 'utf8');
    const scripts = text.match(/<script[^>]+baseTemplate\/custom-js\/system-status\.js[^>]*>/g);
    assert.equal(scripts.length, 1);
    assert.ok(scripts[0].includes('?v={{ CP_VERSION }}-dashboard-acl-2'));
});


test('missing Chart cannot revoke a successful admin permission or suppress nonchart widgets', async () => {
    const d = dashboard({missingChart: true});
    await d.advance(2500); assert.equal(d.adminRequests().length, 0);
    await d.resolve({admin: 1}); await d.advance(6000);
    assert.equal(d.scope.hideSystemCharts, false);
    assert.equal(d.scope.systemChartsError, true);
    assert.equal(d.scope.adminWidgetsError, false);
    assert.equal(d.count('/base/getRecentSSHLogins'), 1);
    assert.equal(d.count('/base/getRecentSSHLogs'), 1);
    assert.ok(d.count('/base/getTopProcesses') >= 3);
    assert.ok(d.count('/base/getDashboardStats') >= 4);
    assert.equal(d.scope.statsLoaded, true);
    for (const url of ['/base/getTrafficStats', '/base/getDiskIOStats', '/base/getCPULoadGraph']) assert.equal(d.count(url), 0);
});

test('partial chart construction is discarded and nonchart polling continues', async () => {
    const d = dashboard({failChart: 2});
    await d.advance(500); await d.resolve({admin: 1}); await d.advance(4000);
    assert.equal(d.scope.hideSystemCharts, false); assert.equal(d.scope.systemChartsError, true);
    assert.equal(d.chartCount, 2); assert.equal(d.destroyedCharts, 1);
    assert.equal(d.windowChart, null);
    assert.ok(d.count('/base/getTopProcesses') >= 2);
    assert.equal(d.count('/base/getTrafficStats'), 0);
});

for (const [name, options] of [['absent canvas', {missingCanvas: 'diskIOChart'}], ['unavailable 2d context', {nullContext: true}]]) {
    test(name+' is a chart failure, not a permission failure', async () => {
        const d = dashboard(options); await d.advance(500); await d.resolve({admin: 1});
        assert.equal(d.scope.systemChartsError, true); assert.equal(d.scope.adminWidgetsError, false);
        assert.equal(d.scope.hideSystemCharts, false); assert.equal(d.chartCount, 0);
        assert.equal(d.count('/base/getRecentSSHLogs'), 1);
    });
}

test('ACL transport failure has a separate visible state and remains default deny', async () => {
    const d = dashboard({missingChart: true}); await d.advance(500); await d.reject();
    assert.equal(d.scope.adminWidgetsError, true); assert.equal(d.scope.systemChartsError, false);
    assert.equal(d.scope.hideSystemCharts, true); assert.equal(d.adminRequests().length, 0);
});

test('limited account does not initialize or report an unavailable admin chart', async () => {
    const d = dashboard({missingChart: true}); await d.advance(500); await d.resolve({admin: 0}); await d.advance(4000);
    assert.equal(d.scope.systemChartsError, false); assert.equal(d.scope.adminWidgetsError, false);
    assert.equal(d.scope.hideSystemCharts, true); assert.equal(d.adminRequests().length, 0);
    assert.equal(d.scope.statsLoaded, true);
});

test('local v4 asset is loaded once, before dashboard bootstrap, with visible error markup', () => {
    const index = fs.readFileSync(path.join(root, 'baseTemplate/templates/baseTemplate/index.html'), 'utf8');
    assert.equal((index.match(/chart\.umd\.min\.js/g) || []).length, 1);
    assert.ok(index.includes("{% static 'baseTemplate/vendor/chartjs-4.5.1/chart.umd.min.js' %}"));
    assert.ok(!index.includes('https://cdn.jsdelivr.net/npm/chart.js'));
    assert.ok(index.indexOf('chart.umd.min.js') < index.indexOf('custom-js/system-status.js'));
    const html = fs.readFileSync(path.join(root, 'baseTemplate/templates/baseTemplate/homePage.html'), 'utf8');
    assert.match(html, /ng-show="adminWidgetsError"[^>]*role="alert"/);
    assert.match(html, /ng-show="systemChartsError"[^>]*role="alert"/);
    assert.equal((html.match(/class="chart-container" ng-hide="systemChartsError"/g) || []).length, 3);
});
