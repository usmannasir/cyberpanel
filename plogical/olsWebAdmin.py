"""Keep stock and CyberPanel custom OLS update notices in their own channels."""
import json
import os
import shutil
import stat
import tempfile


_CUSTOM_ABI = b'cyberpanel_lsi_api_abi_v1'
_MARKER = 'admin/cyberpanel-release-channel.json'
_BASE = 'admin/html/lib/LSWebAdmin/Product/Base/ProductBase.php'
_OWS = 'admin/html/lib/LSWebAdmin/Product/Ows/Product.php'
_DASHBOARD = 'admin/html/view/dashboard.php'

_CHANNEL_METHOD = '''    public function isCyberPanelCustomBuild()
    {
        $marker = $this->getServerRootPath('admin/cyberpanel-release-channel.json');
        $binary = $this->getServerRootPath('bin/openlitespeed');
        if (!is_file($marker) || !is_file($binary)) {
            return false;
        }
        $channel = json_decode((string) file_get_contents($marker), true);
        $identity = stat($binary);
        if (!is_array($channel) || !is_array($identity)
                || !isset($channel['channel']) || $channel['channel'] !== 'cyberpanel-custom') {
            return false;
        }
        foreach (['dev', 'ino', 'size', 'mtime'] as $field) {
            if (!isset($channel[$field]) || $channel[$field] !== $identity[$field]) {
                return false;
            }
        }
        return true;
    }

'''
_CHANNEL_NOTE = '''<?php if ($dashboardProduct->isCyberPanelCustomBuild()) { ?>
                    <span class="lst-dashboard-statusbar__meta">CyberPanel custom build. Check CyberPanel for compatible updates; upstream version numbers use a separate release channel.</span>
<?php } ?>
'''


def _replace_known(source, original, replacement, label):
    if source.count(replacement) == 1:
        if original not in source.replace(replacement, '', 1):
            return source
    if source.count(original) != 1 or replacement in source:
        raise RuntimeError('Unrecognized WebAdmin source at ' + label)
    return source.replace(original, replacement, 1)


def prepare_webadmin_sources(sources):
    """Validate every supported source shape before any installed file changes."""
    result = dict(sources)
    result[_BASE] = _replace_known(
        result[_BASE],
        "return ($release !== '' && $version !== '' && $this->version != $version);",
        "return ($release !== '' && $version !== '' && $this->version !== ''\n"
        "            && version_compare($version, $this->version, '>'));", _BASE)
    anchor = '    public static function extractBuildDisplay($versionOutput)'
    if _CHANNEL_METHOD not in result[_BASE]:
        if result[_BASE].count(anchor) != 1 or 'function isCyberPanelCustomBuild' in result[_BASE]:
            raise RuntimeError('Unrecognized WebAdmin source at ' + _BASE)
        result[_BASE] = result[_BASE].replace(anchor, _CHANNEL_METHOD + anchor, 1)
    result[_OWS] = _replace_known(result[_OWS],
        "        $newVersion = '';",
        "        if ($this->isCyberPanelCustomBuild()) {\n"
        "            return ''; // Upstream releases cannot identify compatible custom updates.\n"
        "        }\n        $newVersion = '';", _OWS)
    result[_OWS] = _replace_known(result[_OWS],
        'if ($this->version != $currentBranchVersion)',
        'if ($this->isNewRelease($currentBranchRelease))', _OWS)
    result[_OWS] = _replace_known(result[_OWS],
        'if ($this->version != $latestVersion && $currentBranchVersion != $latestVersion)',
        'if ($this->isNewRelease($latestRelease) && $currentBranchVersion != $latestVersion)', _OWS)
    anchor = "<?php if ($dashboardNewVersion !== '' && $dashboardNewVersionUrl !== '') { ?>"
    if _CHANNEL_NOTE not in result[_DASHBOARD]:
        if result[_DASHBOARD].count(anchor) != 1 or 'isCyberPanelCustomBuild' in result[_DASHBOARD]:
            raise RuntimeError('Unrecognized WebAdmin source at ' + _DASHBOARD)
        result[_DASHBOARD] = result[_DASHBOARD].replace(anchor, _CHANNEL_NOTE + anchor, 1)
    return result


def _has_custom_abi(binary):
    with open(binary, 'rb') as source:
        previous = b''
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                return False
            if _CUSTOM_ABI in previous + chunk:
                return True
            previous = chunk[-len(_CUSTOM_ABI):]


def patch_webadmin_release_notice(server_root='/usr/local/lsws'):
    """Patch only known PHP assets, preserving bytes on any validation failure.

    The channel marker is bound to the actual binary identity, so replacing the
    custom executable with a stock build invalidates it. This is display metadata,
    never a security-patch attestation or a reason to skip package updates.
    """
    binary = os.path.join(server_root, 'bin/openlitespeed')
    if not os.path.isfile(binary):
        return {'status': 'not-openlitespeed', 'changed': []}
    paths = {name: os.path.join(server_root, name) for name in (_BASE, _OWS, _DASHBOARD)}
    if not any(os.path.lexists(path) for path in paths.values()):
        return {'status': 'unsupported-webadmin-layout', 'changed': []}
    sources = {}
    for name, path in paths.items():
        if os.path.islink(path) or not os.path.isfile(path):
            raise RuntimeError('Missing or linked WebAdmin source: ' + name)
        with open(path, encoding='utf-8') as source:
            sources[name] = source.read()
    prepared = prepare_webadmin_sources(sources)
    changes = {name: value.encode('utf-8') for name, value in prepared.items() if value != sources[name]}
    binary_stat = os.stat(binary)
    custom = _has_custom_abi(binary)
    marker = {'channel': 'cyberpanel-custom' if custom else 'upstream'}
    marker.update({name: getattr(binary_stat, 'st_' + name) for name in ('dev', 'ino', 'size')})
    marker['mtime'] = int(binary_stat.st_mtime)
    marker_bytes = (json.dumps(marker, sort_keys=True) + '\n').encode('utf-8')
    marker_path = os.path.join(server_root, _MARKER)
    if os.path.islink(marker_path):
        raise RuntimeError('Linked WebAdmin release channel marker')
    old_marker = None
    if os.path.exists(marker_path):
        with open(marker_path, 'rb') as source:
            old_marker = source.read()
    if old_marker != marker_bytes:
        changes[_MARKER] = marker_bytes
    if not changes:
        return {'status': 'current', 'channel': marker['channel'], 'changed': []}
    backup = tempfile.mkdtemp(prefix='.cyberpanel-webadmin-backup-', dir=os.path.join(server_root, 'admin'))
    touched = []
    existing = {}
    try:
        for name, data in changes.items():
            target = os.path.join(server_root, name)
            existing[name] = os.path.isfile(target)
            saved = os.path.join(backup, name)
            os.makedirs(os.path.dirname(saved), exist_ok=True)
            if existing[name]:
                shutil.copy2(target, saved)
            staged = saved + '.new'
            with open(staged, 'wb') as output:
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
            mode = os.stat(target) if existing[name] else None
            os.chmod(staged, stat.S_IMODE(mode.st_mode) if mode else 0o644)
            if mode and os.geteuid() == 0:
                os.chown(staged, mode.st_uid, mode.st_gid)
        for name in changes:
            os.replace(os.path.join(backup, name) + '.new', os.path.join(server_root, name))
            touched.append(name)
    except BaseException:
        for name in reversed(touched):
            target = os.path.join(server_root, name)
            if existing[name]:
                shutil.copy2(os.path.join(backup, name), target)
            else:
                os.unlink(target)
        raise
    return {'status': 'patched', 'channel': marker['channel'], 'changed': sorted(changes), 'backup': backup}
