"""Read-only classifier for the supported stock OpenLiteSpeed ABI mismatch."""
import hashlib
import platform
import re
from pathlib import Path

STOCK_CORE = '9ac9627a2678f366c97066c68f16b4a7ca07b692c7967da2f60a0993eade7377'
# openlitespeed 1.9.4-3+noble, verified against the signed LiteSpeed APT index.
NOBLE_194_3_CORE = '54d84931a7dd46fef4485e5f6580db6884532aa3d00f4e41659451d6b15521bb'
PAIRED_MODULE = '41ae567f45931691e34facf1914bf78bb95236d9f8b1ee75d455cbbc19ca6d8b'
# Verified distribution package bytes; the platform key is also the pinned
# *candidate* native artifact family. A matching OS name alone is never proof.
STOCK_PROFILES = {
    ('almalinux', '9.8'): ('rhel9', 'c8b28ee77643d6d0fb9f1ca08f2df2f1f9175fd72c9917d7265283a01098b83d',
        '7a4d92b6050581e17585cb7be9369d6e7d0496e051fa158a65c049c78db8aedb',
        '1b2eb923dd040ad50bd80bbf10f903b92b2dea00e3f54bcae0de2b21a7324f1f'),
    ('ubuntu', '24.04'): ('ubuntu', STOCK_CORE, PAIRED_MODULE,
        'b41fc8e2941ed2fe8602279ace857ea88b2e5d691e7260fc7af4ab4ed9663eda'),
    ('ubuntu', '22.04'): ('ubuntu', '34f1d526e181a9eec1a5297d5c8692add81f9c83153246fec51b1774739f7f87', PAIRED_MODULE,
        '83c8aa0f9f63e5b29b225a2cf41132625421b39b217492b86ede3b26eb5ac3bd'),
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
    accepted_cores = (stock_core, NOBLE_194_3_CORE) if stock_core == STOCK_CORE else (stock_core,)
    for name, expected in [('bin/openlitespeed', accepted_cores),
                           ('modules/cyberpanel_ols.so', (paired_module,))]:
        path = root / name
        if path.is_symlink() or not path.is_file() or digest(path) not in expected:
            raise RuntimeError('Unrecognized stock recovery input: ' + name)



def without_default_autossl_warnings(root, lines):
    """Recognize only the installed defaults the Noble vendor core skips."""
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


def require_stock(root, selected, returncode, output, classifier=None):
    require_bytes(root, selected)
    root = Path(root).absolute()
    lines = output.splitlines()
    original_count = len(lines)
    if (returncode == 1 and any('[httpServerConfig:] Not support [' in line for line in lines)
            and require_platform(selected)[1] == STOCK_CORE
            and digest(root/'bin/openlitespeed') == NOBLE_194_3_CORE):
        lines = without_default_autossl_warnings(root, lines)
    if returncode == 0 and lines == [DIAGNOSTIC]:
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
            'install-module-2.5.7-r11.sh --repair-stock-module and rerun the upgrade.')
