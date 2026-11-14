"""Opt-in test of real upgrade entrypoints with an official Ubuntu 24 stock fixture.

Set CP_OLS_NATIVE_STOCK_ROOT to an unpacked openlitespeed 1.9.4-2+noble
installation with the published Ubuntu 2.7.7 module, and CP_OLS_NATIVE_IMAGE
to its Docker runtime image. No services or files outside the container change.
"""
import json
import os
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.environ.get('CP_OLS_NATIVE_STOCK_ROOT') and
                     os.environ.get('CP_OLS_NATIVE_IMAGE'), 'requires official stock OLS fixture and Docker runtime')
class NativeStockEntryTests(unittest.TestCase):
    def test_hard_soft_and_prepackage_refusals_use_the_verified_stock_hint(self):
        script = r'''
set -eu
mkdir -p /usr/local/lsws /usr/local/CyberCP/{CyberCP,plogical} /tmp/stage
cp -a /fixture/. /usr/local/lsws/
if [[ -f /paid-module.so ]]; then
    root=/usr/local/lsws
    cp /paid-module.so "$root/modules/cyberpanel_ols.so"
    groupadd -f lsadm; id lsadm >/dev/null 2>&1 || useradd -g lsadm lsadm
    mkdir -p "$root/lsphp83/bin" "$root/admin/tmp" "$root/share/autoindex"
    touch "$root/admin/conf/htpasswd" "$root/admin/conf/enable_webadmin"
    chown -R lsadm:lsadm "$root/conf" "$root/admin/conf" "$root/admin/tmp"
    openssl req -x509 -nodes -newkey rsa:2048 -keyout "$root/admin/conf/webadmin.key" \
        -out "$root/admin/conf/webadmin.crt" -subj '/CN=localhost' -days 1 >/dev/null 2>&1
    if [[ -f /fixture-php ]]; then
        cp /fixture-php "$root/lsphp83/bin/lsphp"
    else
        cp "$root/admin/fcgi-bin/admin_php" "$root/lsphp83/bin/lsphp"
    fi
    chown 65534:65534 "$root/Example/html"
fi
cp /src/plogical/{upgrade,olsSecurityAssets,olsParserRecovery,olsStockClassifier,olsNativeValidation}.py \
   /src/{cyberpanel_firewall_migration,cyberpanel_version,lscpd_binary}.py /tmp/stage
cp /tmp/stage/ols{StockClassifier,ParserRecovery,NativeValidation}.py /usr/local/CyberCP/plogical/
# Stub only imports for DB/client settings. No DB should ever be contacted.
touch /usr/local/CyberCP/CyberCP/{__init__,settings}.py /tmp/stage/MySQLdb.py
cd /tmp/stage
export LSWS_HOME=/usr/local/lsws/ PYTHONDONTWRITEBYTECODE=1
core=/usr/local/lsws/bin/openlitespeed
module=/usr/local/lsws/modules/cyberpanel_ols.so
config=/usr/local/lsws/conf/httpd_config.conf
if ! grep -q '^module cyberpanel_ols' "$config"; then
    printf '\nmodule cyberpanel_ols {\n ls_enabled 1\n}\n' >>"$config"
fi
if [[ "$(sha256sum "$core" | cut -d' ' -f1)" = 54d84931a7dd46fef4485e5f6580db6884532aa3d00f4e41659451d6b15521bb ]]; then
    printf '\nautoSSL 1\nacmeEmail admin@cyberpanel.net\n' >>"$config"
fi
sed -n '/^OLS_Pinned_Helper() {/,/^Check_OS() {/p' /src/cyberpanel_upgrade.sh | sed '$d' >/tmp/guard.sh
source /tmp/guard.sh
for matched in 1 0; do
    if [[ "$matched" = 0 ]]; then
        # A harmless trailing byte changes this ELF's hash while retaining its behavior.
        printf '\0' >>"$module"
    fi
    sha256sum "$core" "$module" "$config" >/tmp/prior
    native_status=0
    "$core" -t >/tmp/native 2>&1 || native_status=$?
    test "$native_status" -le 1
    grep -Fxq '[cyberpanel_ols] Module v2.7.7 DISABLED: incompatible OpenLiteSpeed core ABI (expected CyberPanel OLS 2.5.2)' /tmp/native
    for branch in v3.0.8 SoftUpgrade,v3.0.8 prepackage; do
        code=0
        if [[ "$branch" == prepackage ]]; then
            Protect_Custom_OLS_From_Packages >/tmp/result 2>&1 || code=$?
            test "$code" = 1
        else
            python3 -u upgrade.py "$branch" >/tmp/result 2>&1 || code=$?
            test "$code" = 78
        fi
        grep -Fq 'incompatible OpenLiteSpeed core ABI' /tmp/result
        if [[ "$matched" = 1 ]]; then
            grep -Fq 'install-module-2.5.7-r14.sh --repair-stock-module' /tmp/result
            grep -Fq 'https://cyberpanel.net/install-module-2.5.7-r14.sh and verify SHA256 c2db9dccca842e80d45dcaa93bb03d62ef469766a41fc52a598941a4bb8a4e9c' /tmp/result
        else
            if grep -Fq -- '--repair-stock-module' /tmp/result; then exit 1; fi
        fi
        sha256sum -c /tmp/prior
    done
done
'''
        profiles = [{'image': os.environ['CP_OLS_NATIVE_IMAGE'], 'root': os.environ['CP_OLS_NATIVE_STOCK_ROOT']}]
        profiles.extend(json.loads(os.environ.get('CP_OLS_NATIVE_ADDITIONAL_STOCK', '[]')))
        for profile in profiles:
            with self.subTest(image=profile['image']):
                mounts = ['-v', '%s:/fixture:ro' % Path(profile['root']).resolve()]
                if profile.get('module'):
                    mounts.extend(['-v', '%s:/paid-module.so:ro' % Path(profile['module']).resolve()])
                if profile.get('php'):
                    mounts.extend(['-v', '%s:/fixture-php:ro' % Path(profile['php']).resolve()])
                result = subprocess.run([
                    'docker', 'run', '--rm', '--network', 'none', '--tmpfs', '/usr/local/lsws:exec',
                    '-v', '%s:/src:ro' % ROOT, *mounts,
                    '--entrypoint', '/bin/bash', profile['image'], '-c', script,
                ], capture_output=True, text=True, timeout=180)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


@unittest.skipUnless(os.environ.get('CP_OLS_NATIVE_CUSTOM_ROOT') and os.environ.get('CP_OLS_NATIVE_IMAGE'),
                     'requires old custom OLS WebAdmin fixture and Docker runtime')
class NativeCustomEntryTests(unittest.TestCase):
    def test_custom_false_zero_and_both_real_entrypoints(self):
        import tempfile
        script = r'''
set -eu
mkdir -p /usr/local/lsws /usr/local/CyberCP/{CyberCP,plogical} /tmp/stage
cp -a /fixture/. /usr/local/lsws/
cp /src/plogical/{upgrade,olsSecurityAssets,olsParserRecovery,olsStockClassifier,olsNativeValidation}.py \
   /src/{cyberpanel_firewall_migration,cyberpanel_version,lscpd_binary}.py /tmp/stage
cp /tmp/stage/ols{ParserRecovery,StockClassifier,NativeValidation}.py /usr/local/CyberCP/plogical/
touch /usr/local/CyberCP/CyberCP/{__init__,settings}.py /tmp/stage/MySQLdb.py
groupadd -f lsadm; id lsadm >/dev/null 2>&1 || useradd -g lsadm lsadm
cd /tmp/stage
export LSWS_HOME=/usr/local/lsws/ PYTHONDONTWRITEBYTECODE=1
core=/usr/local/lsws/bin/openlitespeed
test ! -e /tmp/lshttpd
"$core" -t >/tmp/raw 2>&1
test ! -s /tmp/raw
sha256sum "$core" /usr/local/lsws/{modules/cyberpanel_ols.so,conf/httpd_config.conf,admin/conf/admin_config.conf} >/tmp/prior
sed -n '/^OLS_Pinned_Helper() {/,/^Check_OS() {/p' /src/cyberpanel_upgrade.sh | sed '$d' >/tmp/guard.sh
source /tmp/guard.sh
for branch in v3.0.8 SoftUpgrade,v3.0.8 prepackage; do
    code=0
    if [[ "$branch" == prepackage ]]; then
        Protect_Custom_OLS_From_Packages >/tmp/result 2>&1 || code=$?
        test "$code" = 1
    else
        python3 -u upgrade.py "$branch" >/tmp/result 2>&1 || code=$?
        test "$code" = 78
    fi
    grep -Fq '[PlainConf] [adminConfig:] Not support' /tmp/result
    grep -Fq 'install-module-2.5.7-r9.sh --repair-webadmin-parser' /tmp/result
    grep -Fq 'https://cyberpanel.net/install-module-2.5.7-r9.sh and verify SHA256 45390adf477eff7cc0ff1a9d03c98f7fe88b45758708aa0243196e855e1699e9' /tmp/result
    test ! -e /tmp/lshttpd
    sha256sum -c /tmp/prior
done
mkdir /tmp/lshttpd
printf 'existing-ledger' >/tmp/lshttpd/testconf
code=0; python3 -IB olsNativeValidation.py "$core" >/tmp/stale 2>&1 || code=$?
test "$code" = 78
grep -Fq 'existing OLS diagnostic' /tmp/stale
test "$(cat /tmp/lshttpd/testconf)" = 'existing-ledger'
'''
        # Docker's overlay writable layer cannot itself be an overlay upper.
        # Use an ordinary installation-like backing filesystem for private scratch.
        with tempfile.TemporaryDirectory(dir=os.environ.get('CP_OLS_NATIVE_SCRATCH_BASE')) as scratch:
            result = subprocess.run([
                'docker', 'run', '--rm', '--privileged', '--network', 'none', '--tmpfs', '/usr/local/lsws:exec',
                '--tmpfs', '/tmp:exec', '-v', '%s:/var/tmp' % scratch, '-v', '%s:/src:ro' % ROOT,
                '-v', '%s:/fixture:ro' % Path(os.environ['CP_OLS_NATIVE_CUSTOM_ROOT']).resolve(),
                '--entrypoint', '/bin/bash', os.environ['CP_OLS_NATIVE_IMAGE'], '-c', script,
            ], capture_output=True, text=True, timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


@unittest.skipUnless(all(os.environ.get(key) for key in
    ('CP_OLS_NATIVE_EL9_IMAGE', 'CP_OLS_NATIVE_EL9_ROOT', 'CP_OLS_NATIVE_EL9_STAGE', 'CP_OLS_NATIVE_EL9_RPMS')),
    'requires AlmaLinux 9 fixture, matched bundle and vendor RPMs')
class NativeRPMEntryTests(unittest.TestCase):
    def test_real_rpm_owners_and_native_gate_before_real_yum_update(self):
        import tempfile
        script = r'''
set -eu
mkdir -p /usr/local/lsws /usr/local/CyberCP/plogical
cp -a /fixture/. /usr/local/lsws/
mkdir -p /usr/local/lsws/modules /usr/local/lsws/share/autoindex
cp /stage/{cyberpanel_ols,mod_security}.so /usr/local/lsws/modules/
cp /src/plogical/ols{NativeValidation,StockClassifier,ParserRecovery}.py /usr/local/CyberCP/plogical/
groupadd -f lsadm; id lsadm >/dev/null 2>&1 || useradd -g lsadm lsadm
getent group nogroup >/dev/null || groupadd -o -g 65534 nogroup
rpm --justdb --nodeps --noscripts --replacefiles -i /core.rpm /waf.rpm
# No network or real repos. The installed RPM metadata contains BOTH owners
# for mod_security.so; the paired paid module is not owned by any package.
mkdir -p /tmp/test-repos /tmp/repo/repodata
printf '[main]\nreposdir=/tmp/test-repos\n' > /etc/dnf/dnf.conf
printf '[qa]\nname=Private QA fixture\nbaseurl=file:///tmp/repo\ngpgcheck=0\n' >/tmp/test-repos/qa.repo
# Offer the real vendor RPMs with a higher fixture metadata epoch so the
# real DNF solver has both updates available. No unfiltered update is applied.
python3 - <<'REPO'
import gzip, hashlib, os
from pathlib import Path
from xml.etree import ElementTree as E
common, rpm, md = ('http://linux.duke.edu/metadata/' + key for key in ('common', 'rpm', 'repo'))
root = E.Element('metadata', xmlns=common, packages='2', **{'xmlns:rpm': rpm})
for name, filename in [('openlitespeed', 'core.rpm'), ('ols-modsecurity', 'waf.rpm')]:
    source = Path('/') / filename
    (Path('/tmp/repo') / filename).symlink_to(source)
    pkg = E.SubElement(root, 'package', type='rpm')
    for key, value in [('name',name),('arch','x86_64')]:
        E.SubElement(pkg,key).text=value
    E.SubElement(pkg, 'version', epoch='1', ver='1.9.4', rel='1.el9')
    E.SubElement(pkg, 'checksum', type='sha256', pkgid='YES').text=hashlib.sha256(source.read_bytes()).hexdigest()
    E.SubElement(pkg, 'summary').text=name
    E.SubElement(pkg, 'description').text='Synthetic solver metadata for real fixture RPM'
    E.SubElement(pkg, 'time', file='1', build='1')
    E.SubElement(pkg, 'size', package=str(source.stat().st_size), installed='1', archive='1')
    E.SubElement(pkg, 'location', href=filename)
    fmt=E.SubElement(pkg, 'format')
    E.SubElement(E.SubElement(fmt,'rpm:provides'),'rpm:entry', name=name, flags='EQ', epoch='1', ver='1.9.4', rel='1.el9')
data=E.tostring(root, encoding='utf-8')
compressed=gzip.compress(data)
where=Path('/tmp/repo/repodata')
(where/'primary.xml.gz').write_bytes(compressed)
index=E.Element('repomd', xmlns=md)
entry=E.SubElement(index,'data',type='primary')
E.SubElement(entry,'checksum',type='sha256').text=hashlib.sha256(compressed).hexdigest()
E.SubElement(entry,'open-checksum',type='sha256').text=hashlib.sha256(data).hexdigest()
E.SubElement(entry,'location',href='repodata/primary.xml.gz')
E.SubElement(entry,'timestamp').text='1'
E.SubElement(entry,'size').text=str(len(compressed))
E.SubElement(entry,'open-size').text=str(len(data))
(where/'repomd.xml').write_bytes(E.tostring(index, encoding='utf-8'))
REPO
code=0; dnf -q check-update openlitespeed ols-modsecurity >/tmp/available || code=$?
test "$code" = 100; grep -q openlitespeed /tmp/available && grep -q ols-modsecurity /tmp/available
sed -n '/^OLS_Pinned_Helper() {/,/^Check_OS() {/p' /src/cyberpanel_upgrade.sh | sed '$d' >/tmp/guard.sh
source /tmp/guard.sh
package_work() {
    Protect_Custom_OLS_From_Packages || return 1
    touch /tmp/package-work-started
    yum update -y "${OLS_RPM_EXCLUDES[@]}"
}
code=0; package_work >/tmp/refusal 2>&1 || code=$?
test "$code" = 1 && test ! -e /tmp/package-work-started
grep -Fq 'install-module-2.5.7-r9.sh --repair-webadmin-parser' /tmp/refusal
cp /stage/openlitespeed /usr/local/lsws/bin/new-core
mv /usr/local/lsws/bin/new-core /usr/local/lsws/bin/openlitespeed
sha256sum /usr/local/lsws/{bin/openlitespeed,modules/cyberpanel_ols.so,modules/mod_security.so,conf/httpd_config.conf} >/tmp/prior
package_work
test "${OLS_RPM_EXCLUDES[*]}" = '--exclude=openlitespeed --exclude=ols-modsecurity'
dnf -q list --installed openlitespeed ols-modsecurity bash >/tmp/unfiltered
dnf -q "${OLS_RPM_EXCLUDES[@]}" list --installed openlitespeed ols-modsecurity bash >/tmp/filtered
grep -Fq 'ols-modsecurity.x86_64' /tmp/unfiltered && grep -Fq 'openlitespeed.x86_64' /tmp/unfiltered
if grep -E 'ols-modsecurity|openlitespeed' /tmp/filtered; then exit 1; fi
grep -Fq 'bash.x86_64' /tmp/filtered
sha256sum -c /tmp/prior
'''
        rpms = Path(os.environ['CP_OLS_NATIVE_EL9_RPMS']).resolve()
        with tempfile.TemporaryDirectory(dir=os.environ.get('CP_OLS_NATIVE_SCRATCH_BASE')) as scratch:
            result = subprocess.run([
                'docker', 'run', '--rm', '--privileged', '--network', 'none', '--tmpfs', '/usr/local/lsws:exec',
                '--tmpfs', '/tmp:exec', '-v', '%s:/var/tmp' % scratch, '-v', '%s:/src:ro' % ROOT,
                '-v', '%s:/fixture:ro' % Path(os.environ['CP_OLS_NATIVE_EL9_ROOT']).resolve(),
                '-v', '%s:/stage:ro' % Path(os.environ['CP_OLS_NATIVE_EL9_STAGE']).resolve(),
                '-v', '%s:/core.rpm:ro' % (rpms / 'openlitespeed-1.9.4-1.el9.x86_64.rpm'),
                '-v', '%s:/waf.rpm:ro' % (rpms / 'ols-modsecurity-1.9.4-1.el9.x86_64.rpm'),
                '--entrypoint', '/bin/bash', os.environ['CP_OLS_NATIVE_EL9_IMAGE'], '-c', script,
            ], capture_output=True, text=True, timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
