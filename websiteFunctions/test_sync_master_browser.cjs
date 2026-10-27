const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const {chromium} = require('playwright');
(async () => {
  const root = path.dirname(__dirname);
  let template = fs.readFileSync(path.join(root, 'websiteFunctions/templates/websiteFunctions/syncMaster.html'), 'utf8');
  template = template.replace(/<script[^>]*>[\s\S]*?<\/script>/g, '')
    .replace(/{%\s*trans\s+"([^"]*)"\s*%}/g, '$1').replace(/{%[\s\S]*?%}/g, '')
    .replace(/{{ childDomain }}/g, 'stage.example').replace(/{{ domainName }}/g, 'live.example')
    .replace(/{{[^}]+}}/g, '');
  const html = '<!doctype html><html ng-app="CyberCP"><head><script>' +
    fs.readFileSync(path.join(root, 'baseTemplate/static/baseTemplate/angularjs.1.6.5.js'), 'utf8') + '</script><script>' +
    'var app = angular.module("CyberCP", []).config(function($interpolateProvider){$interpolateProvider.startSymbol("{$").endSymbol("$}");});' +
    '</script><script>' + fs.readFileSync(path.join(root, 'websiteFunctions/static/websiteFunctions/syncMaster.js'), 'utf8') +
    '</script></head><body>' + template + '</body></html>';
  const browser = await chromium.launch({headless: true});
  try {
    const page = await browser.newPage();
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    let starts = 0, polls = 0, failure = false;
    await page.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (url.pathname === '/websites/startSync') {
        starts++;
        const payload = route.request().postDataJSON();
        assert.equal(payload.confirmed, true); assert.equal(payload.childDomain, 'stage.example');
        return route.fulfill({json: {status: 1, tempStatusPath: '/home/cyberpanel/123'}});
      }
      if (url.pathname === '/websites/installWordpressStatus') {
        polls++;
        if (failure) return route.abort('failed');
        return route.fulfill({json: {abort: 1, installStatus: 1, installationProgress: 100,
          currentStatus: 'Completed. Recovery backup: /private-backup/fixture'}});
      }
      return route.fulfill({contentType: 'text/html', body: html});
    });
    await page.goto('http://sync-fixture.test/');
    const start = page.getByRole('button', {name: 'Start Syncing'});
    assert.equal(await start.isDisabled(), true);
    await page.locator('[ng-model="dbCheck"]').check();
    await page.locator('[ng-model="confirmed"]').check();
    await start.click();
    await page.getByRole('heading', {name: 'Completed. Recovery backup: /private-backup/fixture'}).waitFor();
    assert.equal(starts, 1); assert.equal(polls, 1);
    assert.equal(await page.getByRole('button', {name: 'Go Back'}).isDisabled(), false);
    failure = true;
    await page.goto('http://sync-fixture.test/');
    await page.locator('[ng-model="dbCheck"]').check();
    await page.locator('[ng-model="confirmed"]').check();
    await start.click();
    await page.getByText(/Sync may still be running/).waitFor();
    assert.equal(await page.locator('[ng-click="startSyncing()"]').isDisabled(), true);
    assert.equal(starts, 2); assert.equal(polls, 2); assert.deepEqual(errors, []);
    console.log(JSON.stringify({browser: 'Chromium', successFlow: true, uncertainFlow: true,
      starts, polls, pageErrors: errors, scope: 'actual template/controller with fixture HTTP responses'}));
    await page.close();
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
