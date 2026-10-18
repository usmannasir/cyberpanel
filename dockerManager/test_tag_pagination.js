const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(__dirname + '/static/dockerManager/dockerManager.js', 'utf8');
const start = source.indexOf('$scope.selectTag = function (image)');
const end = source.indexOf('$scope.getHistory', start);
const element = { page: 1 };
const calls = [];
const context = {
  $scope: { imageTag: { 'n8nio:n8n': 'Load more' } },
  document: { getElementById: id => { assert.equal(id, 'n8nio:n8n'); return element; } },
  $: target => { assert.equal(target, element); return { data: (key, value) => value === undefined ? element.page : element.page = value }; },
  populateTagList: (...args) => calls.push(args)
};
vm.runInNewContext(source.slice(start, end), context);
context.$scope.selectTag('n8nio:n8n');
assert.equal(element.page, 2);
assert.deepEqual(calls, [['n8nio:n8n', 1]]);
assert.equal(context.$scope.imageTag['n8nio:n8n'], undefined);
context.$scope.imageTag['n8nio:n8n'] = '2.42.4';
context.$scope.selectTag('n8nio:n8n');
assert.equal(calls.length, 1);
console.log('Tag selection and pagination passed with namespaced image ID, without global event.');
