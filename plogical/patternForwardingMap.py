"""Postfix lookup table for the rules of the Pattern Forwarding page.

Every enabled rule becomes one line of a regexp table, and that table is the
last entry of Postfix's virtual_alias_maps. Postfix looks a full address up
in every map of the list, in order, before it tries the "@domain" form, and it
never looks the "@domain" form up in a regexp table. Listed last, a pattern
therefore loses to an exact forwarding and to a real mailbox, which the maps
before it answer, and wins over the domain's catch-all, which is stored under
"@domain".

A regexp table is read when a Postfix program starts and needs no postmap,
so Postfix is reloaded after a change. Only root can write under
/etc/postfix: the panel reaches apply() through its root helper
(mailUtilities.py) and the upgrade calls upgrade().
"""
import fcntl
import grp
import json
import os
import re
import stat
import subprocess
import tempfile

MAP_PATH = '/etc/postfix/virtual_regexp'
MAIN_CF = '/etc/postfix/main.cf'
PARAMETER = 'virtual_alias_maps'
MAX_PATTERN_LENGTH = 200
MAX_REPEAT = 255
RULES_QUERY = ('SELECT id, domain_id, pattern, destination, pattern_type FROM e_pattern_forwarding '
               'WHERE enabled = 1 ORDER BY priority, id')
HEADER = '# Written by CyberPanel from the Pattern Forwarding page. Changes made here are lost.\n'
RESULT_MARK = 'PATTERN_FORWARDING_RESULT '
PROBE = 'cyberpanel-map-check@invalid'

_LABEL = r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?'
_DOMAIN = re.compile(r'(?:%s\.)+%s' % (_LABEL, _LABEL))
_LOCAL_PART = re.compile(r'[A-Za-z0-9._+=-]+')
_WILDCARD = re.compile(r'[A-Za-z0-9._+=*?-]+')
_PRINTABLE = re.compile(r'[\x21-\x7e]+')
_INTERVAL = re.compile(r'\{([0-9]{1,5})(?:,([0-9]{0,5}))?\}')
_CLASSES = ('alnum', 'alpha', 'blank', 'cntrl', 'digit', 'graph', 'lower', 'print', 'punct', 'space',
            'upper', 'xdigit')


class RuleError(ValueError):
    """A rule that cannot be written to the map as it was typed."""


class MapError(RuntimeError):
    """The map was not installed, or Postfix did not take it."""


def _text(value):
    if isinstance(value, bytes):
        return value.decode('utf-8', 'replace')
    return value


def check_domain(domain):
    """The mail domain in lower case; anything that is not a plain host name is refused."""
    domain = _text(domain)
    if not isinstance(domain, str) or len(domain) > 253 or not _DOMAIN.fullmatch(domain.lower()):
        raise RuleError('The domain is not a valid mail domain.')
    return domain.lower()


def check_destination(destination):
    """One mail address, with nothing a regexp table would read as more than that.

    The result of a table line may hold several addresses and "$" substitutions;
    a destination is limited to characters that mean neither.
    """
    destination = _text(destination)
    if not isinstance(destination, str) or len(destination) > 255:
        raise RuleError('The destination must be one email address.')
    local_part, at, domain = destination.rpartition('@')
    if not at or not _LOCAL_PART.fullmatch(local_part):
        raise RuleError('The destination must be one email address; its part before @ may contain '
                        'letters, digits and . _ + = - only.')
    try:
        return local_part + '@' + check_domain(domain)
    except RuleError:
        raise RuleError('The destination must be one email address at a valid domain.')


def wildcard_expression(pattern):
    """The regular expression for a wildcard: * is any run of characters, ? is one, never across @."""
    pattern = _text(pattern)
    if (not isinstance(pattern, str) or len(pattern) > MAX_PATTERN_LENGTH
            or not _WILDCARD.fullmatch(pattern)):
        raise RuleError('A wildcard pattern is the part of the address before @. It may contain letters, '
                        'digits, . _ + = - and the wildcards * and ?, up to %s characters.'
                        % MAX_PATTERN_LENGTH)
    translated = {'*': '[^@]*', '?': '[^@]', '.': '\\.', '+': '\\+'}
    return ''.join(translated.get(character, character) for character in pattern)


def _bracket_end(pattern, start):
    """Index after the bracket expression opening at `start`, read the way POSIX reads it."""
    position = start + 1
    if pattern[position:position + 1] == '^':
        position += 1
    if pattern[position:position + 1] == ']':
        position += 1
    while position < len(pattern):
        character = pattern[position]
        if character == '\\':
            raise RuleError('A backslash cannot be used inside [ ].')
        if character == '[' and pattern[position + 1:position + 2] in (':', '.', '='):
            end = pattern.find(':]', position + 2)
            if pattern[position + 1] != ':' or end < 0 or pattern[position + 2:end] not in _CLASSES:
                raise RuleError('Inside [ ] only classes such as [:alnum:] or [:digit:] may be named.')
            position = end + 2
            continue
        if character == ']':
            return position + 1
        position += 1
    raise RuleError('A [ is not closed.')


def regex_expression(pattern):
    """A POSIX extended regular expression that is safe to place between "^(" and ")@domain$".

    Postfix reads the table line up to the first unescaped "/", and whitespace
    ends a field, so neither may appear. Every "(" must be closed and no ")"
    may come first: otherwise an alternative could leave the group and match
    addresses of other domains. Escapes of letters and digits are refused
    because they mean something else to Postfix than to most people (\\d is a
    plain d, \\1 is a back-reference).
    """
    pattern = _text(pattern)
    if not isinstance(pattern, str) or not pattern or len(pattern) > MAX_PATTERN_LENGTH:
        raise RuleError('A pattern is required, up to %s characters.' % MAX_PATTERN_LENGTH)
    if not _PRINTABLE.fullmatch(pattern) or '/' in pattern:
        raise RuleError('A pattern may not contain spaces, line breaks, / or characters outside ASCII.')
    depth = 0
    position = 0
    previous = ''
    while position < len(pattern):
        character = pattern[position]
        if character == '\\':
            if position + 1 >= len(pattern) or pattern[position + 1].isalnum():
                raise RuleError('A backslash may only come before a punctuation character. '
                                'Write [0-9] or [[:alnum:]_] instead of \\d or \\w.')
            position += 2
            previous = 'escape'
            continue
        if character == '[':
            position = _bracket_end(pattern, position)
            previous = ']'
            continue
        if character == '{':
            interval = _INTERVAL.match(pattern, position)
            numbers = [int(number) for number in interval.groups() if number] if interval else []
            if not interval or previous == ')' or max(numbers) > MAX_REPEAT:
                raise RuleError('A repeat count is written {n}, {n,} or {n,m} after a single character or '
                                '[ ], with numbers up to %s. Write \\{ for the character itself.' % MAX_REPEAT)
            position = interval.end()
            previous = '}'
            continue
        if character == '(':
            if pattern[position + 1:position + 2] == '?':
                raise RuleError('Groups that begin with (? are not available.')
            depth += 1
        elif character == ')':
            depth -= 1
            if depth < 0:
                raise RuleError('A ) has no matching (.')
        elif character == '@':
            raise RuleError('Enter only the part of the address before @; the domain is added for you.')
        previous = character
        position += 1
    if depth:
        raise RuleError('A ( is not closed.')
    return pattern


def rule_line(pattern_type, pattern, domain, destination):
    """The table line of one rule: its pattern, tied to its own domain, and its destination."""
    if pattern_type == 'wildcard':
        expression = wildcard_expression(pattern)
    elif pattern_type == 'regex':
        expression = regex_expression(pattern)
    else:
        raise RuleError('The pattern type must be wildcard or regex.')
    return '/^(%s)@%s$/ %s' % (expression, check_domain(domain).replace('.', '\\.'),
                               check_destination(destination))


def read_rules(cursor):
    """Enabled rules in the order Postfix is to try them, from any database cursor."""
    cursor.execute(RULES_QUERY)
    return [tuple(row) for row in cursor.fetchall()]


def build(rules):
    """Split rules of (id, domain, pattern, destination, type) into table lines and refusals."""
    entries, rejected = [], []
    for identifier, domain, pattern, destination, pattern_type in rules:
        try:
            entries.append((identifier, rule_line(_text(pattern_type), pattern, domain, destination)))
        except RuleError as error:
            rejected.append({'id': identifier, 'reason': str(error)})
    return entries, rejected


def alias_maps_with_reference(value, reference):
    """The virtual_alias_maps value with `reference` as its last entry; the other entries are kept as written."""
    entries = [entry for entry in re.split(r'[\s,]+', value) if entry]
    if entries.count(reference) == 1 and entries[-1] == reference:
        return value
    others = re.sub(r'(?:^|(?<=[\s,]))%s(?:[\s,]+|$)' % re.escape(reference), '', value).rstrip(' \t\r\n,')
    return others + ', ' + reference if others else reference


def _tool(name):
    for directory in ('/usr/sbin', '/sbin', '/usr/bin'):
        if os.path.exists(os.path.join(directory, name)):
            return os.path.join(directory, name)
    return name


def _run(command):
    done = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, timeout=120)
    return done.returncode, done.stdout, done.stderr


def _said(output, error):
    return (error.strip() or output.strip() or 'no message').splitlines()[-1]


def _alias_maps(run):
    code, output, error = run([_tool('postconf'), '-h', PARAMETER])
    if code != 0:
        raise MapError('Postfix did not report its %s setting: %s' % (PARAMETER, _said(output, error)))
    value = output.strip()
    return ' '.join(value.split()) if '\n' in value else value


def _write_beside(path, text):
    descriptor, temporary = tempfile.mkstemp(prefix='.%s.' % os.path.basename(path), dir=os.path.dirname(path))
    try:
        with os.fdopen(descriptor, 'w') as handle:
            handle.write(text)
            handle.flush()
            os.fchmod(handle.fileno(), 0o640)
            try:
                os.fchown(handle.fileno(), 0, grp.getgrnam('postfix').gr_gid)
            except (KeyError, PermissionError):
                pass
            os.fsync(handle.fileno())
    except BaseException:
        os.remove(temporary)
        raise
    return temporary


def _refused_lines(path, run):
    """Line numbers of `path` that Postfix cannot use, with its reason for each."""
    code, output, error = run([_tool('postmap'), '-q', PROBE, 'regexp:' + path])
    refused = {}
    for line in error.splitlines():
        found = re.search(r'%s, line ([0-9]+): (.*)' % re.escape(path), line)
        if found:
            refused.setdefault(int(found.group(1)), found.group(2).strip())
    # postmap ends with 1 both for "no match", which is expected here, and after a fatal error.
    if not refused and (code not in (0, 1) or 'fatal:' in error or 'panic:' in error):
        raise MapError('Postfix could not read the pattern map: %s' % _said(output, error))
    return refused


def _same(path, text):
    try:
        if os.path.islink(path):
            return False
        with open(path) as handle:
            return handle.read() == text
    except (IOError, OSError, UnicodeDecodeError):
        return False


def _install(entries, rejected, run, map_path):
    """Write the lines Postfix accepts to the map. True when the file changed."""
    while True:
        text = HEADER + ''.join(line + '\n' for _, line in entries)
        temporary = _write_beside(map_path, text)
        try:
            refused = _refused_lines(temporary, run)
            if not refused:
                if _same(map_path, text):
                    return False
                os.replace(temporary, map_path)
                return True
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)
        # The header is line 1, so line n holds entry n - 2.
        indexes = sorted(number - 2 for number in refused)
        if indexes[0] < 0 or indexes[-1] >= len(entries):
            raise MapError('Postfix could not read the pattern map: %s' % sorted(refused.items())[0][1])
        for index in reversed(indexes):
            rejected.append({'id': entries[index][0],
                             'reason': 'The mail server cannot use this pattern: %s' % refused[index + 2]})
            del entries[index]


def apply(rules, run=_run, map_path=MAP_PATH, main_cf=MAIN_CF):
    """Make Postfix follow the rules that `rules()` returns.

    Returns {'state': ..., 'rejected': [{'id': ..., 'reason': ...}]}; a rule
    listed as rejected is not in the map. Raises MapError when the map could
    not be written, listed for Postfix or loaded. A server that has no rule
    and never had the map is left untouched.
    """
    if not os.path.isfile(main_cf):
        return {'state': 'no mail server', 'rejected': []}
    reference = 'regexp:' + map_path
    lock = None
    try:
        # One writer at a time, and the rules are read under the lock, so the
        # map that is written last is never older than one written before it.
        lock = os.open(os.path.dirname(map_path), os.O_RDONLY)
        fcntl.flock(lock, fcntl.LOCK_EX)
        saved = list(rules())
        value = _alias_maps(run)
        listed = reference in re.split(r'[\s,]+', value)
        if not saved and not listed and not os.path.lexists(map_path):
            return {'state': 'not in use', 'rejected': []}

        entries, rejected = build(saved)
        changed = _install(entries, rejected, run, map_path)

        # The map exists from here on; Postfix must never be pointed at a missing file.
        wanted = alias_maps_with_reference(value, reference)
        if wanted != value:
            before = os.stat(main_cf)
            code, output, error = run([_tool('postconf'), '-e', '%s = %s' % (PARAMETER, wanted)])
            if code != 0:
                raise MapError('The pattern map could not be added to %s in %s: %s'
                               % (PARAMETER, main_cf, _said(output, error)))
            # postconf replaces the file; the panel and Postfix keep reading it as before.
            os.chmod(main_cf, stat.S_IMODE(before.st_mode))
            os.chown(main_cf, before.st_uid, before.st_gid)
            changed = True

        if changed and run([_tool('postfix'), 'status'])[0] == 0:
            code, output, error = run([_tool('postfix'), 'reload'])
            if code != 0:
                raise MapError('The pattern map was written, but Postfix did not reload: %s'
                               % _said(output, error))
        return {'state': 'updated' if changed else 'unchanged', 'rejected': rejected}
    except (IOError, OSError, subprocess.SubprocessError) as error:
        raise MapError('The pattern map could not be installed: %s' % error)
    finally:
        if lock is not None:
            os.close(lock)


def result_line(result):
    """What the root helper prints for the panel."""
    return RESULT_MARK + json.dumps(result)


def parse_result(output):
    """The helper's result from everything it printed; a missing or unreadable answer is a failure."""
    if isinstance(output, bytes):
        output = output.decode('utf-8', 'replace')
    if isinstance(output, str):
        for line in reversed(output.splitlines()):
            if line.startswith(RESULT_MARK):
                try:
                    # Whatever the command channel adds after the result is not part of it.
                    result = json.JSONDecoder().raw_decode(line[len(RESULT_MARK):])[0]
                except ValueError:
                    break
                if isinstance(result, dict) and 'status' in result:
                    return result
                break
    return {'status': 0, 'error_message': 'The mail server helper did not report a result.'}


def upgrade(connect, log=lambda message: None, run=_run, map_path=MAP_PATH, main_cf=MAIN_CF):
    """Give Postfix the map for rules that an earlier release saved and never wrote. Returns the state."""
    if not os.path.isfile(main_cf):
        return 'no mail server'
    connection, cursor = connect('cyberpanel')
    if connection == 0:
        log('WARNING: Pattern forwarding rules were not checked: no connection to the database server.')
        return 'no connection'
    try:
        result = apply(lambda: read_rules(cursor), run, map_path, main_cf)
    finally:
        connection.close()
    if result['state'] == 'updated':
        log('Pattern forwarding rules are now in %s and Postfix uses them.' % map_path)
    for refusal in result['rejected']:
        log('WARNING: Pattern forwarding rule %s is not in use: %s' % (refusal['id'], refusal['reason']))
    return result['state']
