"""Owned network-disabled OLS fixture; no production files or listeners."""
import argparse,hashlib,json,pathlib,subprocess,time,datetime
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--fixture-root', required=True, type=pathlib.Path)
parser.add_argument('--container', required=True)
args=parser.parse_args()
R=args.fixture_root.resolve();F=R/'native-root';C=args.container
info=json.loads(subprocess.run(['docker','inspect',C],capture_output=True,text=True,check=True).stdout)[0]
assert info['HostConfig']['NetworkMode']=='none', 'Only a network-disabled QA container is allowed'
assert any(m['Destination']=='/usr/local/lsws' and pathlib.Path(m['Source']).resolve()==F for m in info['Mounts']), 'Fixture mount does not match'
assert (R/'.asn-qa-fixture').read_text().strip()=='isolated ASN QA only', 'Missing explicit fixture marker'
config=(F/'conf/httpd_config.conf').read_text()
assert 'serverName fixture' in config and 'useIpInProxyHeader 0' in config, 'Direct-peer QA configuration required' 
DB=F/'conf/ASN-QA.mmdb';good=DB.read_bytes();vh=F/'conf/vhosts/test.conf';base=vh.read_text()
assert 'GEOIP_ASN' in base and '64500|64501' in base

def run(*args):return subprocess.run(args,capture_output=True,text=True,timeout=30)
def restart():
 p=run('docker','exec',C,'/usr/local/lsws/bin/lswsctrl','restart');assert p.returncode==0,p.stderr+p.stdout
 time.sleep(1)
def request(address,headers=()):
 url='http://[::1]:18080/' if ':' in address else 'http://127.0.0.1:18080/'
 args=['docker','exec',C,'curl','--noproxy','*','--interface',address,'-g','-sS','--max-time','5','-o','/dev/null','-w','%{http_code}','-H','Host: new.test']
 for header in headers:args+=['-H',header]
 p=run(*(args+[url]));assert p.returncode==0,p.stderr
 return int(p.stdout)
records=[]
for address,status,kind in [('1.0.0.1',403,'denied-ipv4'),('1.128.0.1',200,'allowed-ipv4'),('192.0.2.1',200,'unknown-ipv4'),('2001:1700::1',403,'denied-ipv6'),('2001:1c00::1',200,'allowed-ipv6'),('2001:db8::1',200,'unknown-ipv6')]:
 actual=request(address);assert actual==status,(kind,actual);records.append({'case':kind,'status':actual})
for address,headers,status,kind in [('1.0.0.1',['GEOIP_ASN: 64502','ASN: 64502','X-Forwarded-For: 1.128.0.1','CF-Connecting-IP: 1.128.0.1'],403,'denied-ipv4-spoofed-allow-headers'),('2001:1700::1',['GEOIP_ASN: 64502','X-Forwarded-For: 2001:1c00::1'],403,'denied-ipv6-spoofed-allow-headers'),('1.128.0.1',['GEOIP_ASN: 64500','ASN: 64500'],200,'allowed-ipv4-spoofed-deny-headers')]:
 actual=request(address,headers);assert actual==status,(kind,actual);records.append({'case':kind,'status':actual})
# Missing and corrupt database: default denylist deliberately allows unknowns.
failures=[]
try:
 for kind in ['missing','corrupt']:
  if kind=='missing':DB.unlink()
  else:DB.write_bytes(b'invalid QA database')
  test=run('docker','exec',C,'/usr/local/lsws/bin/openlitespeed','-t')
  restart();v4=request('1.0.0.1');v6=request('2001:1700::1')
  assert v4==v6==200,(kind,v4,v6)
  failures.append({'case':kind,'policy':'allow unknown','parser_exit':test.returncode,'ipv4':v4,'ipv6':v6})
  DB.write_bytes(good)
 # Optional strict policy returns503 on missing lookup, while matching denied ASN still403.
 strict=base.replace('RewriteCond %{ENV:GEOIP_ASN}', 'RewriteCond %{ENV:GEOIP_ASN} ^$\nRewriteRule ^ - [R=503,L]\nRewriteCond %{ENV:GEOIP_ASN}',1)
 vh.write_text(strict);restart()
 strict_results={name:request(ip) for name,ip in [('denied-ipv4','1.0.0.1'),('allowed-ipv4','1.128.0.1'),('unknown-ipv4','192.0.2.1'),('denied-ipv6','2001:1700::1'),('allowed-ipv6','2001:1c00::1'),('unknown-ipv6','2001:db8::1')]}
 assert strict_results=={'denied-ipv4':403,'allowed-ipv4':200,'unknown-ipv4':503,'denied-ipv6':403,'allowed-ipv6':200,'unknown-ipv6':503},strict_results
 for kind in ['missing','corrupt']:
  if kind=='missing':DB.unlink()
  else:DB.write_bytes(b'invalid QA database')
  restart();v4=request('1.0.0.1');v6=request('2001:1700::1');assert v4==v6==503,(kind,v4,v6)
  failures.append({'case':kind,'policy':'reject unknown503','ipv4':v4,'ipv6':v6});DB.write_bytes(good)
finally:
 DB.write_bytes(good);vh.write_text(base);restart()
assert request('1.0.0.1')==403 and request('1.128.0.1')==200
log=(F/'logs/error.log').read_text();assert '[GEO]' in log and ('No such file' in log or 'test failed' in log)
r={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'container':C,'os':'Ubuntu22.04.5 x86_64','network':'none; test source addresses only inside container namespace','core_sha256':hashlib.sha256((F/'bin/openlitespeed').read_bytes()).hexdigest(),'database_sha256':hashlib.sha256(good).hexdigest(),'database':'synthetic MaxMind MMDB built with official maxmind/mmdbwriter v1.0.0; not real ASN attribution','source_base':'b36940aad147882738a28546573685b9a89ee809','default_policy_cases':records,'strict_policy_cases':strict_results,'database_failure_cases':failures,'database_errors_logged':True,'restored_known_policy':True,'production_changed':False,'native_binaries_modified':False,'modsecurity_asn_available':False,'header_trust':'No proxy headers trusted in this fixture; direct TCP peer selected'}
(R/'native-acceptance.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
