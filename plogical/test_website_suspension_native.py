"""Destructive native acceptance, explicitly gated to a disposable QA container.

Prerequisites: the task's OLS/MySQL fixture, /qa/ISOLATED_SUSPENSION_QA with
content cyberpanel-jehu-native-qa, and environment variable
CYBERPANEL_RUN_NATIVE_SUSPENSION_TESTS=isolated-qa. Never run on a real panel.
The ordinary unit-test suite skips this module without importing Django.
"""
import os
from pathlib import Path
import unittest


def run_native_acceptance():
    import os
    from pathlib import Path
    if os.environ.get('CYBERPANEL_RUN_NATIVE_SUSPENSION_TESTS') != 'isolated-qa':
        raise RuntimeError('Explicit isolated QA flag is required.')
    marker = Path('/qa/ISOLATED_SUSPENSION_QA')
    if (not Path('/.dockerenv').is_file() or not marker.is_file() or
            marker.read_text().strip() != 'cyberpanel-jehu-native-qa'):
        raise RuntimeError('Disposable container fixture marker is missing.')
    config = Path('/usr/local/lsws/conf/httpd_config.conf')
    if 'serverName jehu-suspension-qa' not in config.read_text():
        raise RuntimeError('The isolated OLS fixture is required.')
    import os,json,time,ssl,http.client,hashlib,subprocess
    from pathlib import Path
    import django
    django.setup()
    from django.conf import settings
    if settings.DATABASES['default']['NAME'] != 'jehu_qa' or settings.DATABASES['default']['HOST'] != 'cp-jehu-suspension-mysql':
        raise RuntimeError('Native suspension tests require the exact isolated QA database.')
    from django.db import connection
    from loginSystem.models import ACL,Administrator
    from packages.models import Package
    from websiteFunctions.models import Websites,ChildDomains
    from plogical.acl import ACLManager
    from plogical.websiteSuspension import change_suspension
    from websiteFunctions.website import WebsiteManager

    receipt={'engine':'OpenLiteSpeed 2.5.7','database':'isolated MySQL8','checks':[]}
    def passed(name):
        receipt['checks'].append(name);print('PASS',name,flush=True)
    def api(domain,action,user=3):
        value=WebsiteManager().submitWebsiteStatus(user,{'websiteName':domain,'state':action})
        result=json.loads(value.content)
        assert result['websiteStatus']==1,result
        return result
    def get(domain,path='/',tls=False):
        klass=http.client.HTTPSConnection if tls else http.client.HTTPConnection
        kwargs={'context':ssl._create_unverified_context()} if tls else {}
        c=klass('127.0.0.1',18443 if tls else 18088,timeout=3,**kwargs)
        try:
            c.request('GET',path,headers={'Host':domain});r=c.getresponse()
            return r.status,r.read().decode(errors='replace')
        finally:c.close()
    def expected(domain,suspended):
        # lswsctrl returns before graceful workers finish; wait for native traffic.
        results=[]
        for attempt in range(70):
            try:
                results=[get(domain,path,tls) for tls in [False,True] for path in ['/','/api/','/static/']]
                if all(code==200 and (('Website suspended' in body) if suspended else (domain+':' in body)) for code,body in results):return
            except (OSError,http.client.HTTPException):pass
            time.sleep(.1)
        raise AssertionError((domain,suspended,results))
    def fingerprint():
        return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/usr/local/lsws/conf/vhosts').glob('*/vhost.conf')}

    # Synthetic accounts only. IDs are deterministic in this newly-created database.
    for name,config in [('admin',ACLManager.AdminACL),('reseller',ACLManager.ResellerACL),('customer',json.dumps(dict(json.loads(ACLManager.UserACL),suspendWebsite=1))),('denied',ACLManager.UserACL)]:
        ACL.objects.get_or_create(name=name,defaults={'config':config})
    for pk,name,owner,acl in [(1,'qa-admin',1,'admin'),(2,'qa-reseller',1,'reseller'),(3,'qa-customer',2,'customer'),(4,'qa-other',1,'customer'),(5,'qa-denied',2,'denied')]:
        Administrator.objects.get_or_create(pk=pk,defaults={'userName':name,'password':'not-a-login-password','email':name+'@example.invalid','type':1 if pk==1 else 3,'owner':owner,'acl':ACL.objects.get(name=acl)})
    pack,_=Package.objects.get_or_create(packageName='qa',defaults={'admin_id':1,'diskSpace':100,'bandwidth':100})
    parent,_=Websites.objects.get_or_create(domain='parent.test',defaults={'admin_id':3,'package':pack,'adminEmail':'qa@example.invalid','phpSelection':'PHP 8.3','ssl':1,'state':1,'externalApp':'qa'})
    Websites.objects.get_or_create(domain='other.test',defaults={'admin_id':4,'package':pack,'adminEmail':'other@example.invalid','phpSelection':'PHP 8.3','ssl':1,'state':1,'externalApp':'other'})
    for domain in ['child.test','sibling.test']:
        ChildDomains.objects.get_or_create(domain=domain,defaults={'master':parent,'path':'/usr/local/lsws/sites/'+domain,'ssl':1,'phpSelection':'PHP 8.3'})

    for domain in ['parent.test','child.test','sibling.test','other.test']:expected(domain,False)
    baseline=fingerprint();passed('baseline parent/child/sibling HTTP+HTTPS root and specific contexts')
    api('child.test','Suspend');expected('child.test',True);expected('parent.test',False);expected('sibling.test',False)
    assert ChildDomains.objects.get(domain='child.test').state==0
    passed('independent child suspension blocks all contexts; parent and sibling remain live')
    before=fingerprint();api('child.test','Suspend');assert fingerprint()==before;passed('repeated suspend idempotent')
    api('parent.test','Suspend');expected('parent.test',True);expected('child.test',True);expected('sibling.test',True)
    api('parent.test','Un-Suspend');expected('parent.test',False);expected('child.test',True);expected('sibling.test',False)
    passed('parent restore preserves independently suspended child')
    api('parent.test','Suspend');result=api('child.test','Un-Suspend');assert result['parentSuspended'] and result['state']=='Suspended'
    expected('child.test',True);assert ChildDomains.objects.get(domain='child.test').state==1
    api('parent.test','Un-Suspend');expected('child.test',False);expected('sibling.test',False)
    assert fingerprint()==baseline;passed('child restore under suspended parent stays blocked then resumes with parent; original configs restored')
    before=fingerprint()
    for user,domain in [(4,'child.test'),(5,'child.test'),(3,'other.test')]:
        r=json.loads(WebsiteManager().submitWebsiteStatus(user,{'websiteName':domain,'state':'Suspend'}).content)
        assert r['websiteStatus']==0,r
    assert fingerprint()==before;passed('actual ORM ACL and cross-owner denial before file writes')
    api('child.test','Suspend',2);expected('child.test',True);api('child.test','Un-Suspend',2);expected('child.test',False)
    passed('reseller can manage owned customer child')

    # A real invalid OLS config forces the privileged worker's validation failure.
    bad=Path('/usr/local/lsws/conf/vhosts/other.test/vhost.conf');original=bad.read_bytes()
    bad.write_bytes(original+b'\ncontext /broken {\n type static\n location /qa-path-does-not-exist/\n}\n')
    before=fingerprint()
    r=json.loads(WebsiteManager().submitWebsiteStatus(3,{'websiteName':'child.test','state':'Suspend'}).content)
    assert r['websiteStatus']==0,r
    assert ChildDomains.objects.get(domain='child.test').state==1
    assert fingerprint()==before
    bad.write_bytes(original)
    subprocess.run(['/usr/local/lsws/bin/openlitespeed','-t'],check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    expected('child.test',False);passed('real config validation failure retains DB state and original target vhost')

    # Inject one reload failure; rollback must restore original bytes, validate and
    # actually reload the original serving configuration on its recovery attempt.
    ctrl=Path('/usr/local/lsws/bin/lswsctrl');real=ctrl.read_bytes();before=fingerprint()
    reload_marker=Path('/tmp/jehu-failed-reload-once')
    reload_marker.unlink(missing_ok=True)
    ctrl.write_text('#!/bin/sh\nif [ ! -e /tmp/jehu-failed-reload-once ]; then touch /tmp/jehu-failed-reload-once; echo qa-injected-reload-failure; exit 1; fi\nexec /usr/local/lsws/bin/lswsctrl.original "$@"\n')
    Path('/usr/local/lsws/bin/lswsctrl.original').write_bytes(real);Path('/usr/local/lsws/bin/lswsctrl.original').chmod(0o755)
    try:
        r=json.loads(WebsiteManager().submitWebsiteStatus(3,{'websiteName':'child.test','state':'Suspend'}).content)
        assert r['websiteStatus']==0,r
        assert ChildDomains.objects.get(domain='child.test').state==1
        assert fingerprint()==before
        expected('child.test',False)
    finally:
        ctrl.write_bytes(real);ctrl.chmod(0o755)
        reload_marker.unlink(missing_ok=True)
    passed('reload failure rolls back DB and files and reactivates original native configuration')

    # Exercise the real existing-schema upgrade helper (drop only the QA column).
    from plogical.schemaMigration import ensure_child_domain_state
    with connection.cursor() as cursor:
        cursor.execute('ALTER TABLE websiteFunctions_childdomains DROP COLUMN state')
        ensure_child_domain_state(connection,cursor)
        ensure_child_domain_state(connection,cursor)
    assert all(s==1 for s in ChildDomains.objects.values_list('state',flat=True))
    passed('MySQL existing-schema state upgrade is verified and idempotent')
    # The creation worker calls this real inheritance hook before save/activation.
    # The dispatcher/order/failure boundaries are covered by the companion unit
    # tests; this section proves actual ORM+OLS behavior of the hook itself.
    from plogical.virtualHostUtilities import virtualHostUtilities
    from plogical.websiteSuspension import suspension_lock, render_suspension
    from plogical.childDomainState import child_backup_record, append_child_backup_xml, normalize_child_state
    from xml.etree.ElementTree import Element, tostring, fromstring
    sibling_path=Path('/usr/local/lsws/conf/vhosts/sibling.test/vhost.conf')
    sibling_original=sibling_path.read_bytes()
    for saved_state in (None,0):
        api('parent.test','Suspend')
        parent.refresh_from_db()
        with suspension_lock():
            ChildDomains.objects.filter(domain='sibling.test').delete()
            sibling_path.write_bytes(sibling_original)
            virtualHostUtilities._inheritDomainSuspension(parent,'sibling.test',saved_state)
            # Disk config was protected before the new ORM row/first activation;
            # the currently serving workers also remain blocked during creation.
            expected('sibling.test',True)
            ChildDomains.objects.create(master=parent,domain='sibling.test',
                path='/usr/local/lsws/sites/sibling.test',ssl=1,phpSelection='PHP 8.3',
                state=1 if saved_state is None else saved_state)
            subprocess.run(['/usr/local/lsws/bin/openlitespeed','-t'],check=True,
                           stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
            subprocess.run(['/usr/local/lsws/bin/lswsctrl','restart'],check=True,
                           stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        expected('sibling.test',True)
        api('parent.test','Un-Suspend')
        expected('sibling.test',saved_state==0)
        if saved_state==0:api('sibling.test','Un-Suspend')
        expected('sibling.test',False)
    passed('real creation inheritance hook blocks new/default and restored-suspended child before first activation')

    # XML and JSON metadata, and real existing-child restore activation/state.
    virtualHostUtilities.restoreChildDomainState('sibling.test',0,'parent.test')
    expected('sibling.test',True)
    sibling=ChildDomains.objects.get(domain='sibling.test')
    record=child_backup_record(sibling)
    xml=Element('ChildDomains');append_child_backup_xml(xml,sibling)
    assert normalize_child_state(fromstring(tostring(xml)).findtext('domain/state'))==0
    assert json.loads(json.dumps(record))['state']==0
    virtualHostUtilities.restoreChildDomainState('sibling.test',None,'parent.test')
    assert ChildDomains.objects.get(domain='sibling.test').state==0
    expected('sibling.test',True)
    before=fingerprint()
    try:virtualHostUtilities.restoreChildDomainState('sibling.test',1,'other.test')
    except ValueError:pass
    else:raise AssertionError('Cross-parent backup state restore was accepted')
    assert fingerprint()==before
    assert ChildDomains.objects.get(domain='sibling.test').state==0
    virtualHostUtilities.restoreChildDomainState('sibling.test',1,'parent.test')
    expected('sibling.test',False)
    assert fingerprint()==baseline
    passed('XML/JSON metadata and actual restore preserve suspension, legacy existing state and parent ownership')

    Path('/qa/native-receipt.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps(receipt),flush=True)


@unittest.skipUnless(os.environ.get('CYBERPANEL_RUN_NATIVE_SUSPENSION_TESTS') == 'isolated-qa',
                     'Requires explicit disposable native QA environment')
class NativeSuspensionAcceptance(unittest.TestCase):
    tags = {'integration'}
    def test_real_orm_worker_http_https_and_rollback(self):
        run_native_acceptance()


if __name__ == '__main__':
    unittest.main()
