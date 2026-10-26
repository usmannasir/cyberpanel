const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const {test} = require('node:test');

for (const file of ['filemanager/static/filemanager/js/fileManager.js', 'static/filemanager/js/fileManager.js', 'filemanager/static/filemanager/js/newFileManager.js']) {
    function fixture() {
        const text=fs.readFileSync(path.join(__dirname,'..',file),'utf8');
        const start=text.indexOf('    $scope.fixPermissions = function () {');
        const end=text.indexOf('\n    };',start)+7;
        const calls=[];const notices=[];
        const scope={fetchForTableSecondary(){}};
        const context={$scope:scope,$http:{post(...args){return {then(ok,bad){calls.push({args,ok,bad});}};}},
            domainName:'fixture.test',domainRandomSeed:'fixture',getCookie(){return 'csrf';},
            alertify:{notify(...args){notices.push(args);}},PNotify:function(value){notices.push(value);}};
        vm.runInNewContext(text.slice(start,end),context);
        return {scope,calls,notices};
    }
    test(file+': duplicate click waits for completion',()=>{
        const {scope,calls}=fixture();scope.fixPermissions();scope.fixPermissions();
        assert.equal(calls.length,1);assert.equal(scope.fixPermissionsPending,true);
        calls[0].ok({data:{permissionsChanged:1}});
        assert.equal(scope.fixPermissionsPending,false);scope.fixPermissions();assert.equal(calls.length,2);
    });
    test(file+': HTTP failure is visible and permits retry',()=>{
        const {scope,calls,notices}=fixture();scope.fixPermissions();calls[0].bad({status:500});
        assert.equal(scope.fixPermissionsPending,false);assert.equal(notices.length,1);
        scope.fixPermissions();assert.equal(calls.length,2);
    });
}
