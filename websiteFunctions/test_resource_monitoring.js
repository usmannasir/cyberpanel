const fs = require('fs'), vm = require('vm'), assert = require('assert');
const path = require('path');
const copies = ['static/websiteFunctions/js/resource-monitoring.js', 'websiteFunctions/static/js/resource-monitoring.js', 'websiteFunctions/static/websiteFunctions/js/resource-monitoring.js'];
const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, copies[0]), 'utf8');
for (const copy of copies) assert.equal(fs.readFileSync(path.join(root, copy), 'utf8'), source, copy);
let requests = [], charts = [], timers = new Map(), events = {}, nextTimer = 0, checks = 0;
const status = {textContent: ''};
const document = {hidden: false, getElementById: id => id === 'resource-usage-status' ? status : {getContext: () => ({})}, addEventListener: (name, fn) => {events[name] = fn;}};
function jquery(arg) {return arg === document ? {ready: fn => fn()} : {text: () => ' example.test '};}
jquery.ajax = args => requests.push(args);
const context = {document, window: {addEventListener: (name, fn) => {events[name] = fn;}}, $: jquery,
  Chart: function(ctx, options) {this.data = options.data; this.update = () => {}; charts.push(this);},
  setTimeout: (fn, delay) => {assert.equal(delay, 5000);timers.set(++nextTimer,fn);return nextTimer;}, clearTimeout: id => timers.delete(id), Date, Number};
const check = fn => {fn();checks++;};
function tick() {const [id, fn] = timers.entries().next().value;timers.delete(id);fn();}
function respond(data) {const current=requests.at(-1);current.success(data);current.complete();}
const valid={status:1,cpu_usage:25,memory_usage:2,disk_percent:0.1,disk_used:8};
vm.runInNewContext(source, context);
check(()=>assert.equal(requests.length,1));
check(()=>assert.equal(timers.size,0));
check(()=>assert.equal(requests[0].timeout,12000));
check(()=>assert.deepEqual(JSON.parse(requests[0].data),{domain:'example.test'}));
events.visibilitychange();check(()=>assert.equal(requests.length,1));
respond(valid);check(()=>assert(status.textContent.includes('Document root: 8 MiB')));
check(()=>assert.equal(timers.size,1));
tick();check(()=>assert.equal(requests.length,2));
respond({...valid,cpu_usage:NaN});check(()=>assert.equal(charts[0].data.datasets[0].data.length,1));
check(()=>assert(status.textContent.includes('historical')));
tick();requests.at(-1).error();requests.at(-1).complete();check(()=>assert(status.textContent.includes('unavailable')));
document.hidden=true;tick();check(()=>assert.equal(requests.length,3));
document.hidden=false;events.visibilitychange();check(()=>assert.equal(requests.length,4));
respond(valid);
for(let i=0;i<35;i++){tick();respond(valid);}
check(()=>assert(charts.every(c=>c.data.labels.length===30 && c.data.datasets[0].data.length===30)));
events.pagehide();check(()=>assert.equal(timers.size,0));
events.visibilitychange();check(()=>assert.equal(requests.length,39));
events.pageshow();check(()=>assert.equal(requests.length,40));
console.log(JSON.stringify({status:'passed',checks,scope:'Actual production JavaScript in VM; request lifecycle, visibility, errors, finite data and chart bound.'}));
