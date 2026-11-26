"""Read-only classifier for the supported stock OpenLiteSpeed ABI mismatch."""
import hashlib
import mmap
import os
import platform
import re
import sys
from pathlib import Path

STOCK_CORE = '9ac9627a2678f366c97066c68f16b4a7ca07b692c7967da2f60a0993eade7377'
# openlitespeed 1.9.4-3+noble, verified against the signed LiteSpeed APT index.
NOBLE_194_3_CORE = '54d84931a7dd46fef4485e5f6580db6884532aa3d00f4e41659451d6b15521bb'
# openlitespeed 1.9.4-3+resolute, verified against the signed LiteSpeed APT index.
RESOLUTE_194_3_CORE = 'ab860ab89dfeb6f157bbfc62786ae4ff5c401fd427310d53a0edc1ccbd58df87'
# openlitespeed 1.9.4-1+jammy amd64, extracted from the LiteSpeed archive.
JAMMY_194_1_CORE = 'a66855d898427e0241991eb55d83e29771995ef3abd0e5c31c4fbc64b7b4364a'
JAMMY_194_3_CORE = '34f1d526e181a9eec1a5297d5c8692add81f9c83153246fec51b1774739f7f87'
# openlitespeed 1.9.4-3.el9 x86_64, verified against the LiteSpeed RPM payload.
EL9_194_3_CORE = '1788aef94ca79d824f80ecbfbc1faf916f68b3d6688feb8e986eead2795ec8e2'
EL9_194_1_CORE = 'c8b28ee77643d6d0fb9f1ca08f2df2f1f9175fd72c9917d7265283a01098b83d'
PAIRED_MODULE = '41ae567f45931691e34facf1914bf78bb95236d9f8b1ee75d455cbbc19ca6d8b'
# Verified distribution package bytes; the platform key is also the pinned
# *candidate* native artifact family. A matching OS name alone is never proof.
STOCK_PROFILES = {
    ('almalinux', '9.8'): ('rhel9', EL9_194_1_CORE,
        '7a4d92b6050581e17585cb7be9369d6e7d0496e051fa158a65c049c78db8aedb',
        '1b2eb923dd040ad50bd80bbf10f903b92b2dea00e3f54bcae0de2b21a7324f1f'),
    ('ubuntu', '24.04'): ('ubuntu', STOCK_CORE, PAIRED_MODULE,
        'b41fc8e2941ed2fe8602279ace857ea88b2e5d691e7260fc7af4ab4ed9663eda'),
    ('ubuntu', '22.04'): ('ubuntu', JAMMY_194_3_CORE, PAIRED_MODULE,
        '83c8aa0f9f63e5b29b225a2cf41132625421b39b217492b86ede3b26eb5ac3bd'),
    ('ubuntu', '26.04'): ('ubuntu26', RESOLUTE_194_3_CORE, PAIRED_MODULE,
        '453f86d0adc560c7b33a425719e912481c8fd97b6099ab5801f90a49106325e9'),
}

DIAGNOSTIC = ('[cyberpanel_ols] Module v2.7.7 DISABLED: incompatible OpenLiteSpeed '
              'core ABI (expected CyberPanel OLS 2.5.2)')


def require_platform(selected, os_release='/etc/os-release'):
    values = {}
    for line in Path(os_release).read_text().splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            values[key] = value.strip().strip('"\'')
    profile = STOCK_PROFILES.get((values.get('ID'), values.get('VERSION_ID')))
    if (not profile or (selected is not None and selected != profile[0]) or
            platform.machine() not in ('amd64', 'x86_64')):
        raise RuntimeError('Unsupported stock recovery OS, architecture or artifact family')
    return profile



def digest(path):
    hasher = hashlib.sha256()
    with open(str(path), 'rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            hasher.update(block)
    return hasher.hexdigest()


def require_bytes(root, selected):
    _, stock_core, paired_module, _ = require_platform(selected)
    root = Path(root)
    additional_cores = {
        STOCK_CORE: (NOBLE_194_3_CORE,),
        JAMMY_194_3_CORE: (JAMMY_194_1_CORE,),
        EL9_194_1_CORE: (EL9_194_3_CORE,),
    }
    accepted_cores = (stock_core,) + additional_cores.get(stock_core, ())
    for name, expected in [('bin/openlitespeed', accepted_cores),
                           ('modules/cyberpanel_ols.so', (paired_module,))]:
        path = root / name
        if path.is_symlink() or not path.is_file() or digest(path) not in expected:
            raise RuntimeError('Unrecognized stock recovery input: ' + name)



def without_default_autossl_warnings(root, lines):
    """Recognize only the installed defaults these vendor cores skip."""
    config = root / 'conf/httpd_config.conf'
    warning = re.compile(
        r'[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6} '
        r'\[WARN\] \[PlainConf\] \[httpServerConfig:\] Not support '
        r'\[(autossl 1|acmeemail admin@cyberpanel\.net)\] in file '
        + re.escape(str(config)) + r':([1-9][0-9]{0,7})'
    )
    if config.is_symlink() or not config.is_file():
        return lines
    configured = config.read_text(encoding='utf-8').splitlines()
    remaining, seen = [], set()
    for line in lines:
        match = warning.fullmatch(line)
        if match:
            directive, number = match.groups()
            index = int(number) - 1
            if (directive not in seen and index < len(configured)
                    and ' '.join(configured[index].lower().split()) == directive):
                seen.add(directive)
                continue
        remaining.append(line)
    return remaining


def noble_webadmin_throttle_rejection(root, returncode, lines):
    """Recognize the verified stock Noble parser diagnostic without editing the config."""
    if (returncode != 2 or len(lines) != 2 or lines.count(DIAGNOSTIC) != 1
            or digest(root / 'bin/openlitespeed') != STOCK_CORE):
        return False
    config = root / 'admin/conf/admin_config.conf'
    if config.is_symlink() or not config.is_file():
        return False
    diagnostic = next(line for line in lines if line != DIAGNOSTIC)
    match = re.fullmatch(
        r'(?:\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+ )?\[ERROR\] '
        r'(?:\[\d+\] )?\[PlainConf\] \[adminConfig:\] Not support '
        r'\[throttleenabled 1\] in file ' + re.escape(str(config)) + r':([1-9][0-9]{0,7})',
        diagnostic,
    )
    if not match:
        return False
    configured = config.read_text(encoding='utf-8').splitlines()
    index = int(match[1]) - 1
    return index < len(configured) and bool(re.fullmatch(
        r'\s*throttleEnabled\s+1\s*(?:#.*)?', configured[index], re.I))


def require_stock(root, selected, returncode, output, classifier=None):
    require_bytes(root, selected)
    root = Path(root).absolute()
    lines = output.splitlines()
    original_count = len(lines)
    if (returncode in (1, 2) and any('[httpServerConfig:] Not support [' in line for line in lines)
            and digest(root/'bin/openlitespeed') in (
                STOCK_CORE, NOBLE_194_3_CORE, RESOLUTE_194_3_CORE, JAMMY_194_1_CORE, EL9_194_3_CORE)):
        lines = without_default_autossl_warnings(root, lines)
    if lines == [DIAGNOSTIC] and (returncode == 0 or (returncode == 1 and original_count > 1)):
        return []
    if noble_webadmin_throttle_rejection(root, returncode, lines):
        return []
    if (returncode != 1 or lines.count(DIAGNOSTIC) != 1 or len(lines) > 3
            or (len(lines) == 1 and original_count == 1)):
        raise RuntimeError('Unrecognized stock core ABI or diagnostic status')
    if classifier is None:
        import olsParserRecovery as classifier
    others = [line for line in lines if line != DIAGNOSTIC]
    errors, warnings = classifier.split_diagnostics(Path(root), '\n'.join(others))
    if (errors or len(warnings) != len(others) or len(set(warnings)) != len(warnings) or
            not set(warnings).issubset(classifier.example_warnings(Path(root)))):
        raise RuntimeError('Stock ABI diagnostic contains unrelated, duplicate or unverifiable warnings')
    return warnings


def stock_recovery_hint(binary, returncode, output, classifier=None):
    try:
        require_stock(Path(binary).parent.parent, require_platform(None)[0], returncode, output, classifier)
    except (OSError, RuntimeError, ValueError, ImportError):
        return ''
    return (' Known stock core/module mismatch. Use the checksum-verified '
            'install-module-2.5.7-jammy-r1.sh --repair-stock-module and rerun the upgrade.')


# The Jammy -1 vendor WAF and this reviewed POSIX drain controller are
# admitted only as an exact tuple, never as an OS-wide controller exception.
JAMMY_194_1_WAF = '189d9a06d3924e75aeb6945b796c37c54a63a5b26a23b004fc04411605249957'
JAMMY_DRAIN_CONTROLLER = '83435cff252f314ec65c0b61c7eba01289c721a2bf4e4351a402501b6f4bf709'


def stock_waf_hashes(root, selected):
    require_bytes(root, selected)
    _, core, _, stock_waf = require_platform(selected)
    result = {stock_waf}
    if core == JAMMY_194_3_CORE and digest(Path(root)/'bin/openlitespeed') == JAMMY_194_1_CORE:
        result.add(JAMMY_194_1_WAF)
    return frozenset(result)


def reviewed_jammy_controller(root, selected):
    root = Path(root)
    _, core, module, _ = require_platform(selected)
    if core != JAMMY_194_3_CORE:
        return False
    for rel, expected in (('bin/openlitespeed', JAMMY_194_1_CORE),
                          ('modules/cyberpanel_ols.so', PAIRED_MODULE),
                          ('modules/mod_security.so', JAMMY_194_1_WAF),
                          ('bin/lswsctrl.open', JAMMY_DRAIN_CONTROLLER)):
        path = root/rel
        if path.is_symlink() or not path.is_file() or digest(path) != expected:
            return False
    return True


# --- Vendor core beside a self-disabled CyberPanel module ("split" bundle) ---
#
# A package update can replace only bin/openlitespeed. The bundle transaction of
# the ordinary upgrade repairs that state: it keeps the exact previous bytes,
# validates the configuration with the CyberPanel core and restores the previous
# files when that fails. The old state is therefore not fingerprinted here; it
# may stop the upgrade only for faults the vendor core did not cause.
MARKER = b'cyberpanel_lsi_api_abi_v1'
SPLIT_DIAGNOSTIC = re.compile(
    r'\[cyberpanel_ols\] Module v[0-9]+(?:\.[0-9]+)* DISABLED: incompatible OpenLiteSpeed core ABI\b')
# Directives implemented only by the CyberPanel core. A vendor core reports
# them as unsupported; they are not configuration faults.
CUSTOM_ONLY_DIRECTIVES = frozenset(('autossl', 'acmeemail'))
_UNSUPPORTED = re.compile(
    r'(?:\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+ )?\[(?:WARN|ERROR)\] (?:\[\d+\] )?\[PlainConf\] '
    r'\[[^\]]*\] Not support \[([^\s\]]+)[^\]]*\] in file (/[^:]+):([1-9][0-9]{0,7})')
_STAMP = re.compile(r'^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+ (\[[A-Z]+\]) (?:\[\d+\] )?')


# OpenLiteSpeed keeps running, and keeps serving every other website, when one
# website's own configuration is wrong: a PHP version that is no longer
# installed, a certificate that is gone, a syntax error in that website's
# file. Such an error was there before the upgrade and cannot be caused by it.
ABI_DIAGNOSTIC = 'incompatible OpenLiteSpeed core ABI'
_SITE = re.compile(r'\[config:server:vhosts:vhost:([^\]:\s]+)')
# Braces that do not pair up by the end of a website's file are reported for
# the file as a whole, without a line number. The bracket after [PlainConf]
# names the block that was still open ("[context:/]"), not the kind of file;
# the kind of file is the rootTag at the end of the line.
_SITE_FILE = re.compile(r'\[PlainConf\] \[virtualHostConfig:\] .* in (?:file )?(/[^\s:]+):[0-9]+\s*$'
                        r'|Path for vhost config is invalid: (/\S+)\s*$'
                        r"|\[PlainConf\] \[.*\] parseFile find '\{' and '\}' do not match "
                        r'in the end of file (/[^\s,]+), rootTag virtualHostConfig\.?\s*$')


def site_scope(line):
    """Name the one website an error line is confined to, or None."""
    if '[ERROR]' not in line or '[FATAL]' in line or ABI_DIAGNOSTIC in line:
        return None
    match = _SITE.search(line)
    if match:
        return 'website ' + match.group(1)
    match = _SITE_FILE.search(line)
    if not match:
        return None
    # A website's own file names the website, however the core words the error.
    path = match.group(1) or match.group(2) or match.group(3)
    owner = re.search(r'/conf/vhosts/([^/]+)/[^/]+$', path)
    return 'website ' + owner.group(1) if owner else 'file ' + path


def site_errors(output):
    """The websites that have errors of their own, each with its error lines."""
    found = {}
    for line in output.splitlines():
        scope = site_scope(line)
        if scope:
            found.setdefault(scope, []).append(line.strip())
    return found


def blocking_errors(output, known=None):
    """The error lines that must stop an upgrade.

    An error confined to one website does not. `known` names the websites that
    had errors before anything was changed; given it, an error in any other
    website appeared during the upgrade and stops it too.
    """
    blocking = []
    for line in output.splitlines():
        if not ('[ERROR]' in line or '[FATAL]' in line or ABI_DIAGNOSTIC in line):
            continue
        scope = site_scope(line)
        if scope is None or (known is not None and scope not in known):
            blocking.append(line.strip())
    return blocking


def status_refused(returncode, output):
    """Whether the exit status of `-t` alone must stop an upgrade.

    OpenLiteSpeed ends with 1 after warnings and with 2 after any error, a
    website's included. Status 2 is accepted only with a website error to
    account for it; `blocking_errors` judges the lines themselves.
    """
    return returncode not in (0, 1) and not (returncode == 2 and site_errors(output))


class SplitStateRefused(RuntimeError):
    """The vendor-core state must not be repaired; the message is for the administrator."""


def has_marker(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not path.stat().st_size:
        return False
    with open(str(path), 'rb') as source:
        with mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_READ) as data:
            return data.find(MARKER) >= 0


def _custom_only(root, line, limits):
    """True when the vendor core rejected one of our directives at the cited line."""
    match = _UNSUPPORTED.fullmatch(line)
    name = match.group(1).lower() if match else ''
    if name not in CUSTOM_ONLY_DIRECTIVES and name not in limits:
        return False
    path = Path(match.group(2))
    if path.is_symlink() or not path.is_file():
        return False
    resolved = str(path.resolve())
    if not any(resolved.startswith(str((root / name).resolve()) + os.sep) for name in ('conf', 'admin/conf')):
        return False
    configured = path.read_text(encoding='utf-8', errors='replace').splitlines()
    index = int(match.group(3)) - 1
    words = configured[index].split() if index < len(configured) else []
    if not words or words[0].lower() != name:
        return False
    if name not in limits:
        return True
    # A value the CyberPanel core would reject is a fault of the configuration.
    low, high = limits[name]
    return len(words) > 1 and words[1].isdigit() and low <= int(words[1]) <= high


def split_state(binary, returncode, output, parser=None, os_release='/etc/os-release'):
    """Classify `-t` output of a core that lacks the CyberPanel ABI marker.

    Returns None when this is not a vendor core beside a self-disabled CyberPanel
    module (the ordinary validation applies), a baseline dict when the bundle
    transaction may repair it, and raises SplitStateRefused otherwise.
    """
    binary = Path(binary).absolute()
    root = binary.parent.parent
    if binary.is_symlink() or not binary.is_file() or has_marker(binary):
        return None
    if not has_marker(root / 'modules/cyberpanel_ols.so'):
        return None
    lines = [line for line in output.splitlines() if line.strip()]
    disabled = [line for line in lines if SPLIT_DIAGNOSTIC.search(line)]
    if len(disabled) != 1:
        return None
    if parser is None:
        import olsParserRecovery as parser
    try:
        parser.host_platform(os_release)
    except (OSError, RuntimeError):
        raise SplitStateRefused(
            'This server runs the vendor OpenLiteSpeed core beside a disabled CyberPanel module, '
            'and no CyberPanel OpenLiteSpeed bundle exists for this operating system or '
            'architecture. Nothing was changed.')
    errors, vendor_errors = [], 0
    for line in lines:
        if line is disabled[0] or not ('[ERROR]' in line or '[FATAL]' in line):
            continue
        if _custom_only(root, line, parser.LIMITS) or site_scope(line):
            vendor_errors += 1  # Neither is a reason to leave the vendor core in place.
        else:
            errors.append(line)
    if errors:
        raise SplitStateRefused(
            'OpenLiteSpeed reports configuration errors that the vendor core did not cause. '
            'Correct them and run the upgrade again; nothing was changed:\n' + '\n'.join(errors))
    if returncode not in (0, 1, 2) or (returncode == 2 and not vendor_errors):
        raise SplitStateRefused(
            'The vendor OpenLiteSpeed core could not test the configuration (exit status %s); '
            'nothing was changed:\n%s' % (returncode, '\n'.join(lines)))
    # Timestamps, process IDs and informational lines vary between runs. The
    # exit status and the error-level lines identify the state before and
    # after a rollback.
    return {'returncode': returncode,
            'errors': sorted(_STAMP.sub(r'\1 ', line) for line in lines
                             if line is disabled[0] or '[ERROR]' in line or '[FATAL]' in line)}


# --- A declaration of the CyberPanel module on a server that never received it ---
#
# Until 3.0.18 the installer declared the module also when it kept the vendor
# core (no CyberPanel build for the architecture or system), and upgrades from
# November 2025 to November 2026 did the same after a failed download. The
# vendor core reports that it cannot load the missing file and keeps serving.
# Where a CyberPanel build exists, the bundle transaction supplies the module
# and the declaration becomes valid; elsewhere the upgrade removes it.
# The Ubuntu 2.5.0 / 2.7.3 core predates the ABI marker; the launcher treats it
# as a CyberPanel core.
LEGACY_UBUNTU_CORE = '2a836d4bf17fe5152d15dd60fd3817c1d3c294b48b35f12b776fa2efb7771422'
STALE_MODULE_ERROR = re.compile(
    r'(?:\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+ )?\[ERROR\] (?:\[\d+\] )?Failed to load module '
    r'\[cyberpanel_ols\], error: (/\S+): cannot open shared object file: No such file or directory\s*')
_STANZA_OPEN = re.compile(r'[ \t]*module[ \t]+cyberpanel_ols[ \t]*\{[ \t]*')
_STANZA_BODY = re.compile(r'[ \t]*(?:ls_enabled[ \t]+[01][ \t]*)?')
_STANZA_CLOSE = re.compile(r'[ \t]*\}[ \t]*')


def module_stanza(text):
    """(first, last) line index of the one top-level `module cyberpanel_ols` block, or None.

    A narrow brace/backtick scanner like olsParserRecovery.top_level_group, not
    an OLS parser. Only the block the installer writes is recognised: its own
    lines, with nothing in it but `ls_enabled 0|1`. Anything ambiguous (two
    blocks, a block inside another, unbalanced braces, the name anywhere else,
    including comments and opaque rule text) yields None.
    """
    lines = text.split('\n')
    depth, opaque, spans, start = 0, False, [], None
    for number, line in enumerate(lines):
        ticks = line.count('`')
        if opaque:
            if ticks % 2:
                opaque = False
            continue
        if start is not None:
            if _STANZA_CLOSE.fullmatch(line):
                spans.append((start, number))
                start = None
            elif not _STANZA_BODY.fullmatch(line):
                return None
            continue
        if ticks:
            if ticks % 2:
                opaque = True
            continue
        if line.lstrip().startswith('#'):
            continue
        if depth == 0 and _STANZA_OPEN.fullmatch(line):
            start = number
            continue
        opens, closes = line.count('{'), line.count('}')
        if opens > 1 or closes > 1:
            return None
        depth += opens - closes
        if depth < 0:
            return None
    if opaque or depth or start is not None or len(spans) != 1:
        return None
    first, last = spans[0]
    if any('cyberpanel_ols' in line for line in lines[:first] + lines[last + 1:]):
        return None
    return first, last


def without_module_stanza(text, span):
    """The configuration with exactly the lines of that block taken out."""
    lines = text.split('\n')
    first, last = span
    return '\n'.join(lines[:first] + lines[last + 1:])


def stale_module_stanza(binary, returncode, output):
    """Classify `-t` output of a vendor core whose configuration declares the missing module.

    Returns None when this is not that state (the ordinary validation applies)
    and otherwise a baseline that identifies the same state in a later run.
    """
    binary = Path(binary).absolute()
    root = binary.parent.parent
    if binary.is_symlink() or not binary.is_file() or has_marker(binary):
        return None
    if digest(binary) == LEGACY_UBUNTU_CORE:
        return None
    module = root / 'modules/cyberpanel_ols.so'
    if os.path.lexists(str(module)) or os.path.lexists(str(root / '.cyberpanel-stock-recovery-policy')):
        return None
    if returncode not in (0, 1, 2):
        return None
    blocking = blocking_errors(output)
    match = STALE_MODULE_ERROR.fullmatch(blocking[0]) if len(blocking) == 1 else None
    if not match or os.path.normpath(match.group(1)) != str(module):
        return None
    config = root / 'conf/httpd_config.conf'
    if config.is_symlink() or not config.is_file():
        return None
    try:
        text = config.read_bytes().decode('utf-8')
    except (OSError, UnicodeDecodeError):
        return None
    if module_stanza(text) is None:
        return None
    return {'state': 'stale-module-stanza', 'returncode': returncode,
            'errors': sorted(_STAMP.sub(r'\1 ', line.strip()) for line in output.splitlines()
                             if '[ERROR]' in line or '[FATAL]' in line)}


def module_declarable(root='/usr/local/lsws'):
    """Whether the CyberPanel core and module are both installed, so the module may be declared."""
    root = Path(root)
    return has_marker(root / 'bin/openlitespeed') and has_marker(root / 'modules/cyberpanel_ols.so')


if __name__ == '__main__':
    # olsStockClassifier.py --split-state BINARY RETURNCODE OS_RELEASE < output-of-BINARY-t
    # 0: repairable split bundle, 3: not that state, 4: refused (reason on stdout).
    # olsStockClassifier.py --stale-module-stanza BINARY RETURNCODE < output-of-BINARY-t
    # 0: declaration of the missing module, 3: not that state.
    # Both: 64 wrong arguments, 78 the state could not be classified.
    mode = sys.argv[1] if len(sys.argv) > 1 else ''
    if (mode, len(sys.argv)) not in (('--split-state', 5), ('--stale-module-stanza', 4)):
        sys.exit(64)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        if mode == '--split-state':
            state = split_state(sys.argv[2], int(sys.argv[3]), sys.stdin.read(), os_release=sys.argv[4])
        else:
            state = stale_module_stanza(sys.argv[2], int(sys.argv[3]), sys.stdin.read())
    except SplitStateRefused as refusal:
        print(refusal)
        sys.exit(4)
    except Exception as error:
        print('Cannot classify the installed OpenLiteSpeed state: %s' % error)
        sys.exit(78)
    sys.exit(0 if state is not None else 3)
