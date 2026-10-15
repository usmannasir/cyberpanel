'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(__dirname+'/static/backup/backup.js','utf8');
const template=fs.readFileSync(__dirname+'/templates/backup/googleDrive.html','utf8');
assert.match(template,/gdrive-handoff-2/);
assert.match(template,/type="password" autocomplete="off"/);
assert.match(template,/ng-disabled="!gdriveSetupEnabled/);
const start=source.indexOf("app.controller('googleDrive'");
const end=source.indexOf('$scope.currentPage',start);
function fixture(enabled=true,blocked=false){
  const calls=[],notices=[],scope={accountName:'new',client_id:'synthetic.apps.googleusercontent.com',client_secret:'SYNTHETIC-SECRET'};
  let ok,bad;
  const popup={opener:{},location:{},closed:false,close(){this.closed=true;}};
  vm.runInNewContext(source.slice(start,end)+'});',{
    app:{controller(name,fn){fn(scope,{get(url){assert.equal(url,'/backup/GDriveSetupStatus');return{then(success){success({data:{status:1,enabled}});}};},post(...args){calls.push(args);return{then(a,b){ok=a;bad=b;}};}});}},
    window:{open(url){assert.equal(url,'about:blank');return blocked?null:popup;}},URL,Array,
    getCookie(){return 'synthetic-csrf';},PNotify:function(options){notices.push(options);}
  });
  return {scope,calls,popup,notices,success(data){ok({data});},fail(){bad();}};
}
let f=fixture(false);f.scope.setupAccount();assert.equal(f.calls.length,0);
f=fixture();f.scope.setupAccount();f.scope.setupAccount();assert.equal(f.calls.length,1);
assert.equal(f.calls[0][0],'/backup/BeginGDriveSetup');
assert.equal(f.calls[0][2].headers['X-CSRFToken'],'synthetic-csrf');
assert.equal(f.popup.opener,null);
f.success({status:1,authorization_url:'https://platform.example.test/gDrive/v2/start?handoff='+'a'.repeat(43)});
assert.equal(f.scope.client_secret,'');assert.ok(!f.popup.location.href.includes('SYNTHETIC'));
for(const authorization_url of ['https://platform.example.test/gDrive?handoff='+'a'.repeat(43),
 'https://platform.example.test/gDrive/v2/start?handoff='+'a'.repeat(43)+'&secret=SYNTHETIC',
 'http://platform.example.test/gDrive/v2/start?handoff='+'a'.repeat(43)]){
 f=fixture();f.scope.setupAccount();f.success({status:1,authorization_url});
 assert.equal(f.popup.closed,true);assert.ok(!JSON.stringify(f.notices).includes('SYNTHETIC'));
}
f=fixture();f.scope.setupAccount();f.fail();f.scope.setupAccount();assert.equal(f.calls.length,2);
f=fixture(true,true);f.scope.setupAccount();assert.equal(f.calls.length,0);
console.log('OK normal enrollment: capability gate, POST/CSRF, duplicate guard, popup isolation, secret clearing, URL validation, safe errors/retry');
