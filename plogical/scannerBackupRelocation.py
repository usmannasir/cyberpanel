"""Move the AI Scanner's backups of earlier releases out of the folders the web server serves.

Earlier releases kept the copy the scanner makes before it changes a file in
`<site directory>/.ai-scanner-backups/<date>/`, inside the document root. The
copies are files of the website (its configuration file among them) under a
name the web server will hand out. The scanner now keeps them in the
website's home, in `/home/<domain>/.ai-scanner-backups/`, which is private to
the website's user and outside every served folder.

During an upgrade every such folder of earlier releases is moved there, as
`from-<site directory>-<number>`, whole and under a name nothing has yet, so
nothing is overwritten and nothing is lost. The places looked at are the ones
the scanner worked in: the document root of every website, the folder of
every child domain and the folder of every WordPress site the panel knows.

The move is made by the website's own user with one fixed command, so it can
do nothing that user could not do. A folder that is a link, or a private
folder that is one, is left alone and reported. Nothing here keeps state: a
folder that is gone is not looked for again, so it can run at every upgrade.
"""
import os
import re
import subprocess

from plogical.securityUtils import is_safe_system_user

BACKUP_DIRECTORY = '.ai-scanner-backups'
DOMAIN = re.compile(r'[A-Za-z0-9](?:[A-Za-z0-9._-]{0,253}[A-Za-z0-9])?\Z')
SHOWN = 12

# $1 is the website's home, $2 the site directory, $3 the name the folder gets.
# g enters a folder for real and keeps its true path in p. The exit status says
# what was found: 4 nothing to move, 5 the old folder is a link, 6 the private
# folder is a link or cannot be used, 7 the move did not happen, 8 a folder
# cannot be entered, 9 the site directory is not inside the home.
MOVE = (
    'g(){ cd -P -- "$1"&&p=$(pwd -P&&echo /)&&p=${p%??};}\n'
    'g "$1"&&h=$p&&g "$2"&&r=$p||exit 8\n'
    '[ "$r" = "$h" ]&&exit 4\n'
    'case "$r/" in "$h"/*);;*)exit 9;;esac\n'
    'o=' + BACKUP_DIRECTORY + '\n'
    '[ -L "$o" ]&&exit 5\n'
    '[ -d "$o" ]||exit 4\n'
    'b=$h/$o\n'
    'mkdir -m 700 "$b"\n'
    '(g "$b"&&[ "$p" = "$b" ])||exit 6\n'
    'chmod 700 "$b"||exit 6\n'
    'n=1\n'
    'while [ -e "$b/from-$3-$n" ]||[ -L "$b/from-$3-$n" ];do n=$((n+1));done\n'
    'mv -n -T -- "$o" "$b/from-$3-$n"||exit 7\n'
    '[ -e "$o" ]||[ -L "$o" ]&&exit 7\n'
    'printf "%s\\n" "$b/from-$3-$n"\n')

REASONS = {
    5: 'it is a link',
    6: 'the private folder in the home is a link or cannot be used',
    7: 'it could not be moved',
    8: 'the folder cannot be entered',
    9: 'the folder is not inside the home of its website',
}


def quote(name):
    """The name between backticks."""
    return '`' + str(name).replace('`', '``') + '`'


def text(value):
    return value.decode('utf-8', 'replace') if isinstance(value, bytes) else str(value)


def run_as_site_user(user, home, root, name):
    """Run the move as the website's user; return (exit status, what it printed)."""
    process = subprocess.Popen(
        ['sudo', '-u', user, '--', 'sh', '-c', MOVE, 'sh', home, root, name], cwd='/',
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        output = process.communicate(timeout=300)[0]
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        return 7, b''
    return process.returncode, output


def folder_name(home, root):
    """The site directory as one plain name: its path below the home, with every other character replaced."""
    return re.sub(r'[^A-Za-z0-9._-]', '_', root[len(home) + 1:])[:100].strip('.') or 'site'


def places(cursor, database):
    """(user, home, site directory) of every place the scanner of earlier releases worked in."""
    websites = quote(database) + '.websiteFunctions_websites'
    found = []
    seen = set()

    def add(domain, user, root):
        domain, user, root = text(domain), text(user), text(root)
        home = '/home/' + domain
        key = (home, root)
        if key in seen or DOMAIN.match(domain) is None or '..' in domain:
            return
        seen.add(key)
        found.append((user, home, root))

    cursor.execute('SELECT domain, externalApp FROM %s' % websites)
    for domain, user in cursor.fetchall():
        add(domain, user, '/home/%s/public_html' % text(domain))
    # A table an older installation does not have yet is no reason to skip the rest.
    for table, owner in (('websiteFunctions_childdomains', 'master_id'), ('websiteFunctions_wpsites', 'owner_id')):
        try:
            cursor.execute('SELECT w.domain, w.externalApp, p.path FROM %s.%s p JOIN %s w ON w.id = p.%s' % (
                quote(database), table, websites, owner))
            rows = cursor.fetchall()
        except Exception:
            continue
        for domain, user, root in rows:
            add(domain, user, text(root).rstrip('/'))
    return found


def relocate(found, runner=run_as_site_user, exists=os.path.lexists):
    """Move the old backup folder of every place that has one."""
    result = {'moved': [], 'skipped': []}
    for user, home, root in found:
        old = os.path.join(root, BACKUP_DIRECTORY)
        try:
            if any(ord(char) < 32 or ord(char) == 127 for char in root) or os.path.normpath(root) != root \
                    or not root.startswith(home + '/'):
                # A place outside the home of its website is none the scanner made backups in.
                continue
            # Looked at without opening anything; everything else is done by the website's user.
            if not exists(old):
                continue
            if not is_safe_system_user(user) or user == 'root' or user.startswith('-'):
                result['skipped'].append([old, 'its website has no user of its own'])
                continue
            status, output = runner(user, home, root, folder_name(home, root))
            moved_to = text(output).rstrip('\n')
            if status == 0 and moved_to.startswith('/'):
                result['moved'].append([old, moved_to])
            elif status != 4:
                result['skipped'].append([old, REASONS.get(status, 'the command ended with status %s' % status)])
        except Exception as error:
            result['skipped'].append([old, type(error).__name__ + ': ' + str(error)])
    return result


def describe(result, log):
    """Tell the administrator what was moved and what needs a look."""
    for old, new in result['moved'][:SHOWN]:
        log('AI Scanner backups: moved %s to %s' % (old, new))
    if len(result['moved']) > SHOWN:
        log('AI Scanner backups: and %d more folder(s) moved.' % (len(result['moved']) - SHOWN))
    for old, reason in result['skipped']:
        log('WARNING: The AI Scanner backups in %s were left where they are: %s. '
            'The web server may serve the files in them.' % (old, reason))


def panel_database():
    """The name of the panel's own database."""
    try:
        from CyberCP import settings
        return str(settings.DATABASES['default']['NAME'])
    except Exception:
        return 'cyberpanel'


def run(connect=None, log=print, runner=run_as_site_user, exists=os.path.lexists):
    """Entry point for the upgrader; `connect` returns (connection, cursor) or (0, 0)."""
    if connect is None:
        from plogical.mysqlUtilities import mysqlUtilities
        connect = mysqlUtilities.setupConnection

    connection, cursor = connect()
    if connection == 0:
        log('WARNING: AI Scanner backups of earlier releases were not looked for: '
            'no connection to the database server.')
        return 'no connection'
    try:
        found = places(cursor, panel_database())
    finally:
        connection.close()
    result = relocate(found, runner, exists)
    describe(result, log)
    return '%d folder(s) of earlier releases moved out of served folders, %d left where they are, ' \
           '%d place(s) looked at' % (len(result['moved']), len(result['skipped']), len(found))
