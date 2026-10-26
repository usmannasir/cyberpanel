const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),test=require('node:test');
for(const file of ['websiteFunctions/static/websiteFunctions/websiteFunctions.js','static/websiteFunctions/websiteFunctions.js','websiteFunctions/static/js/websiteFunctions.js']) {
 const source=fs.readFileSync(path.join(__dirname,'..',file),'utf8');
 const marker="app.controller('RestoreWPBackup',";
 let offset=0,index=0;
 while((offset=source.indexOf(marker,offset))!==-1){
  let end=source.indexOf('app.controller(',offset+marker.length);if(end<0)end=source.length;
  const code=source.slice(offset,end),label=file+' controller '+(++index);offset+=marker.length;
  function setup(answer){
   let controller,confirmations=0;const posts=[],scope={},mutations=[];
   const jq=(selector)=>({show:()=>mutations.push('show'),hide:()=>mutations.push('hide'),html:()=>selector==='#backupid'?'12':'Website Backup',val:()=>selector==='#wprestoresubdirpath'?'':'fixture.example',children:()=>({val:()=> '34'})});
   const context={app:{controller:(name,cb)=>controller=cb},$:jq,getCookie:()=> 'fixture-csrf',console:{log:()=>{}}};
   vm.runInNewContext(code,context);
   controller(scope,{post:(url,data,config)=>{posts.push({url,data,config});return {then:()=>{}};}},()=>{},{confirm:()=>{confirmations++;return answer;}});
   mutations.length=0;return {scope,posts,mutations,confirmations:()=>confirmations};
  }
  test(label+' cancellation submits nothing and preserves screen',()=>{const s=setup(false);s.scope.RestoreWPbackupNow();assert.equal(s.confirmations(),1);assert.equal(s.posts.length,0);assert.equal(s.mutations.length,0);});
  test(label+' confirmation uses existing CSRF-protected POST',()=>{const s=setup(true);s.scope.RestoreWPbackupNow();assert.equal(s.confirmations(),1);assert.equal(s.posts.length,1);assert.equal(s.posts[0].url,'/websites/RestoreWPbackupNow');assert.equal(s.posts[0].config.headers['X-CSRFToken'],'fixture-csrf');});
 }
}
