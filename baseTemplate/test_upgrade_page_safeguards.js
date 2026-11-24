'use strict';
// The upgrade page asks before it starts, never offers an older release and
// always tells the administrator where a run stands.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');

const script = fs.readFileSync(path.join(__dirname, 'static/baseTemplate/custom-js/system-status.js'), 'utf8');
const template = fs.readFileSync(path.join(__dirname, 'templates/baseTemplate/versionManagment.html'), 'utf8');

function upgradeScreen(answer) {
    const start = script.indexOf("app.controller('versionManagment'");
    const end = script.indexOf("app.controller('designtheme'", start);
    let controller;
    const requests = [], timers = [], questions = [];
    const schedule = (handler, delay) => { const timer = {handler, delay}; timers.push(timer); return timer; };
    schedule.cancel = () => {};
    const context = {
        app: {controller(name, fn) { controller = fn; }},
        window: {confirm(question) { questions.push(question); return answer; }},
        document: {
            getElementById: () => ({value: 'v3.0.10'}),
            querySelector: (selector) => selector === 'button[ng-click="upgrade()"]'
                ? {getAttribute: (name) => name === 'data-confirm' ? 'Upgrade CyberPanel now?' : null}
                : {getAttribute: () => '0'}
        },
        getCookie: () => null
    };
    vm.runInNewContext(script.slice(start, end), context, {filename: 'system-status.js'});
    const scope = {$on() {}};
    controller(scope, {post(url, data) { return {then(success, failure) { requests.push({url, data, success, failure}); }}; }}, schedule);
    return {scope, requests, timers, questions};
}

test('nothing is started when the administrator declines', () => {
    const ui = upgradeScreen(false);
    ui.scope.upgrade();
    assert.deepEqual(ui.questions, ['Upgrade CyberPanel now?']);
    assert.equal(ui.requests.length, 0);
    assert.equal(ui.scope.upgradeLoading, true);
});

test('the upgrade starts once the administrator agrees', () => {
    const ui = upgradeScreen(true);
    ui.scope.upgrade();
    assert.equal(ui.requests[0].url, '/base/upgrade');
    assert.equal(ui.requests[0].data.branchSelect, 'v3.0.10');
    assert.match(template, /ng-click="upgrade\(\)"[^>]*\sdata-confirm="\{% trans "[^"]*services are restarted[^"]*" %\}"/);
});

test('a failed run shows its reason together with the end of the log', () => {
    const ui = upgradeScreen(true);
    ui.scope.upgrade();
    ui.requests[0].success({data: {upgrade: 1}});
    ui.requests[1].success({data: {finished: 1, upgradeStatus: 0, upgradeLog: 'last lines',
                                   error_message: 'Upgrade exited with code 1. The previous version was put back and the panel restarted.'}});
    assert.equal(ui.scope.updateError, false);
    assert.match(ui.scope.errorMessage, /previous version was put back/);
    assert.equal(ui.scope.upgradelogBox, false);
    assert.equal(ui.scope.upgradeLog, 'last lines');
    assert.equal(ui.timers.length, 0);
});

test('an answer that is not the upgrade verdict is retried, and ends the wait only when it lasts', () => {
    for (const [data, expected] of [
        [{error_message: 'This request need session.'}, /This request need session\./],
        [{upgradeStatus: 0, error_message: 'Not Logged In, please refresh the page or login again.'}, /Not Logged In/],
        [{FilemanagerAdmin: 0, errorMessage: 'You are not authorized.'}, /not authorized/],
        ['<html>login</html>', /no longer accepts this session/],
        [undefined, /no longer accepts this session/]
    ]) {
        const ui = upgradeScreen(true);
        ui.scope.upgrade();
        ui.requests[0].success({data: {upgrade: 1}});
        for (let poll = 1; poll <= 20; poll++) {
            ui.requests[poll].success({data});
            assert.equal(ui.scope.updateError, true);
            assert.equal(ui.scope.couldNotConnect, false);
            assert.equal(ui.timers[poll - 1].delay, 3000);
            ui.timers[poll - 1].handler();
        }
        ui.requests[21].success({data});
        assert.match(ui.scope.errorMessage, expected);
        assert.equal(ui.scope.updateError, false);
        assert.equal(ui.scope.upgradeLoading, true);
        assert.equal(ui.scope.updateStarted, true);
        assert.equal(ui.timers.length, 20);
    }
});

test('a short loss of the session store during an upgrade does not end the wait', () => {
    const ui = upgradeScreen(true);
    ui.scope.upgrade();
    ui.requests[0].success({data: {upgrade: 1}});
    ui.requests[1].success({data: {error_message: 'This request need session.'}});
    ui.timers[0].handler();
    ui.requests[2].success({data: {finished: 0, upgradeStatus: 1, upgradeLog: 'still running'}});
    assert.equal(ui.scope.couldNotConnect, true);
    assert.equal(ui.scope.updateError, true);
    assert.equal(ui.scope.upgradeLog, 'still running');
    ui.timers[1].handler();
    ui.requests[3].success({data: {finished: 1, upgradeStatus: 1, upgradeLog: 'done'}});
    assert.equal(ui.scope.updateFinish, false);
    assert.equal(ui.scope.updateError, true);
});

test('a completed upgrade with steps that did not complete is not shown as a plain success', () => {
    const ui = upgradeScreen(true);
    ui.scope.upgrade();
    ui.requests[0].success({data: {upgrade: 1}});
    ui.requests[1].success({data: {finished: 1, upgradeStatus: 1, upgradeLog: 'done',
                                   incomplete: ['The panel web worker was not rebuilt: no network', 7]}});
    assert.equal(ui.scope.updateFinish, false);
    assert.deepEqual(Array.from(ui.scope.upgradeIncomplete), ['The panel web worker was not rebuilt: no network']);
    assert.match(template, /ng-hide="updateFinish \|\| upgradeIncomplete\.length"[^>]*>\s*\{% trans "CyberPanel upgrade completed\." %\}/);
    assert.match(template, /ng-show="!updateFinish && upgradeIncomplete\.length"[\s\S]*?ng-repeat="step in upgradeIncomplete/);
    // A clean run, and a new run after one with failures, show the plain success.
    const clean = upgradeScreen(true);
    clean.scope.upgrade();
    clean.requests[0].success({data: {upgrade: 1}});
    clean.requests[1].success({data: {finished: 1, upgradeStatus: 1, upgradeLog: 'done'}});
    assert.deepEqual(Array.from(clean.scope.upgradeIncomplete), []);
    ui.scope.upgrade();
    assert.deepEqual(Array.from(ui.scope.upgradeIncomplete), []);
});

test('a quiet run offers the stop button, which asks first and then asks the server', () => {
    const ui = upgradeScreen(true);
    ui.scope.upgrade();
    ui.requests[0].success({data: {upgrade: 1}});
    ui.requests[1].success({data: {finished: 0, upgradeStatus: 1, upgradeLog: 'cloning', idleMinutes: 2, canStop: 0}});
    assert.equal(ui.scope.upgradeCanStop, false);
    ui.timers[0].handler();
    ui.requests[2].success({data: {finished: 0, upgradeStatus: 1, upgradeLog: 'cloning', idleMinutes: 6, canStop: 1}});
    assert.equal(ui.scope.upgradeCanStop, true);
    assert.equal(ui.scope.upgradeIdleMinutes, 6);
    assert.match(template, /ng-click="stopUpgrade\(\)"[\s\S]*?data-confirm="\{% trans "Stop the upgrade now\?[^"]*" %\}"/);
    const questions = ui.questions.length;
    ui.scope.stopUpgrade();
    assert.equal(ui.questions.length, questions + 1);
    assert.equal(ui.requests[3].url, '/base/upgradeStop');
    ui.requests[3].success({data: {stopped: 1, error_message: 'The upgrade is being stopped.'}});
    assert.equal(ui.scope.upgradeCanStop, false);
    assert.equal(ui.scope.stopMessage, 'The upgrade is being stopped.');
    // The run then ends as a failure with its reason; the button is gone.
    ui.timers[1].handler();
    ui.requests[4].success({data: {finished: 1, upgradeStatus: 0, upgradeLog: 'x',
                                   error_message: 'The upgrade was stopped from the panel after it wrote nothing for 6 minutes.'}});
    assert.equal(ui.scope.upgradeCanStop, false);
    assert.match(ui.scope.errorMessage, /stopped from the panel/);
});

test('a declined stop question sends nothing', () => {
    const ui = upgradeScreen(false);
    ui.scope.stopUpgrade();
    assert.equal(ui.requests.length, 0);
});

test('the page keeps checking through a slow restart and says when it stops', () => {
    const ui = upgradeScreen(true);
    ui.scope.upgrade();
    ui.requests[0].success({data: {upgrade: 1}});
    for (let poll = 1; poll <= 200; poll++) {
        ui.requests[poll].failure({status: 502});
        assert.equal(ui.timers.length, poll);
        assert.equal(ui.timers[poll - 1].delay, 3000);
        assert.match(ui.scope.connectionMessage, /keeps checking/);
        ui.timers[poll - 1].handler();
    }
    ui.requests[201].failure({status: 502});
    assert.equal(ui.timers.length, 200);
    assert.match(ui.scope.connectionMessage, /has not answered for 10 minutes/);
    assert.equal(ui.scope.couldNotConnect, false);
    assert.match(template, /ng-hide="couldNotConnect"[^>]*>\s*<span ng-bind="connectionMessage">/);
});

function branchList(installed, rendered) {
    const start = template.indexOf('function populateBranches(branches)');
    const end = template.indexOf('// Call the function to get all branches', start);
    const select = {options: rendered.map(value => ({value})), appendChild(option) { this.options.push(option); },
                    getAttribute: (name) => name === 'data-installed-release' ? installed : null};
    const context = {document: {getElementById: () => select, createElement: () => ({})}, console: {error() {}}, Set, Array, Math, Number, isNaN};
    vm.createContext(context);
    vm.runInContext(template.slice(start, end), context);
    return {populate: (names) => context.populateBranches(names), values: () => select.options.map(option => option.value)};
}

test('releases older than the installed one are not offered', () => {
    const list = branchList('v3.0.9', ['v3.0.10', 'v3.0.9', 'stable']);
    list.populate(['v1.7.4', 'v2.3.5-design', 'v2.4.8', 'v3.0', 'v3.0.6', 'v3.0.8', 'v3.0.9', 'v3.0.10', 'v3.0.11', 'v3.1.0', 'v4.0.0-rc1']);
    assert.deepEqual(list.values(), ['v3.0.10', 'v3.0.9', 'stable', 'v4.0.0-rc1', 'v3.1.0', 'v3.0.11']);
});

test('every release stays available when the installed one is unknown', () => {
    const list = branchList('', ['stable']);
    list.populate(['v2.4.8', 'v3.0.9']);
    assert.deepEqual(list.values(), ['stable', 'v3.0.9', 'v2.4.8']);
});

test('the newest release is the default choice and comes first', () => {
    assert.match(template, /ng-init="branchSelect='\{\{ defaultRelease\|default:'stable' \}\}'"/);
    const options = template.slice(template.indexOf('id="branchSelect"'), template.indexOf('</select>', template.indexOf('id="branchSelect"')));
    assert.ok(options.indexOf('{{ latestRelease }}') < options.indexOf('{{ currentRelease }}'));
    assert.ok(options.indexOf('{{ currentRelease }}') < options.indexOf('<option value="stable">stable</option>'));
    assert.match(options, /data-installed-release="\{\{ currentRelease\|default:'' \}\}"/);
});
