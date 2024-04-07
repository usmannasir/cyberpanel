import sys
sys.path.append('/usr/local/CyberCP')
from plogical.processUtilities import ProcessUtilities


def findPHPVersions():
    # distro = ProcessUtilities.decideDistro()
    # if distro == ProcessUtilities.centos:
    #     return ['PHP 5.3', 'PHP 5.4', 'PHP 5.5', 'PHP 5.6', 'PHP 7.0', 'PHP 7.1', 'PHP 7.2', 'PHP 7.3', 'PHP 7.4', 'PHP 8.0', 'PHP 8.1']
    # elif distro == ProcessUtilities.cent8:
    #     return ['PHP 7.1','PHP 7.2', 'PHP 7.3', 'PHP 7.4', 'PHP 8.0', 'PHP 8.1']
    # elif distro == ProcessUtilities.ubuntu20:
    #     return ['PHP 7.2', 'PHP 7.3', 'PHP 7.4', 'PHP 8.0', 'PHP 8.1']
    # else:
    #     return ['PHP 7.0', 'PHP 7.1', 'PHP 7.2', 'PHP 7.3', 'PHP 7.4', 'PHP 8.0', 'PHP 8.1']

    try:

        # Run the shell command and capture the output
        result = ProcessUtilities.outputExecutioner('ls -la /usr/local/lsws')

        # Get the lines containing 'lsphp' in the output
        lsphp_lines = [line for line in result.split('\n') if 'lsphp' in line]
        print(lsphp_lines)

        # Extract the version from the lines and format it as 'PHP x.y'
        php_versions = ['PHP ' + line.split()[8][5] + '.' + line.split()[8][6:] for line in lsphp_lines]
        print(php_versions)

        # Now php_versions contains the formatted PHP versions
        return php_versions
    except BaseException as msg:
        print(str(msg))
        return ['PHP 7.0', 'PHP 7.1', 'PHP 7.2', 'PHP 7.3', 'PHP 7.4', 'PHP 8.0', 'PHP 8.1']

findPHPVersions()