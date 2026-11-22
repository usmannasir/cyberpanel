"""Postfix lookup table for the rules of the Pattern Forwarding page.

Every enabled rule becomes one line of a regexp table, and that table is the
last entry of Postfix's virtual_alias_maps. Postfix looks a full address up
in every map of the list, in order, before it tries a shorter form, and it
never looks a shorter form up in a regexp table. The order for one recipient
is therefore:

1. an exact forwarding for the address as it was written;
2. a real mailbox with that address;
3. the pattern rules, lowest priority number first;
4. where Postfix has a recipient_delimiter (plus-addressing): the forwarding
   or mailbox of the address without its "+tag";
5. the catch-all of the domain, which is stored under "@domain".

Step 3 comes before step 4, so a broad pattern also takes "user+tag" mail of
an existing mailbox "user". A rule only ever matches its own domain.

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
HELPER_COMMAND = '/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/mailUtilities.py applyPatternForwarding'

# Every smtpd and cleanup process compiles every line of the map, and smtpd
# runs an address through the lines for each RCPT TO, so the cost of one rule
# is paid by all mail of the server. The C library expands a counted repeat
# into copies, and its matching time grows with the square of the copies that
# can be in play at once: 2,040 copies were measured at 0.25 s for a
# 64-character address, and stacked counts multiply. The limits below leave
# at most 16 counted or optional copies and 8 open-ended repeats in a pattern,
# never stacked and never inside a repeated group. By the same measure that
# is about a ten-thousandth of the measured cost, a few hundredths of a
# millisecond per rule, and 200 rules stay within a few milliseconds per
# recipient and a few megabytes per Postfix process.
MAX_PATTERN_LENGTH = 100    # characters of a pattern as it is typed
MAX_COUNTED = 16            # all {n}, {n,m} counts of a pattern added up, plus one for each "?"
MAX_UNBOUNDED = 8           # "*", "+" and "{n,}" in a pattern; "*" in a wildcard
MAX_GROUP_DEPTH = 4         # groups inside groups
MAX_RULES_PER_DOMAIN = 20
MAX_RULES = 200             # on the whole server

# postmap reads a map of this size in a fraction of a second. A check that
# takes longer is given up, so that no rule can keep the helper waiting.
CHECK_TIMEOUT = 10          # seconds for the whole map, and for an empty one
RULE_TIMEOUT = 3            # seconds for one rule on its own
MAX_SLOW_RULES = 5          # more than this many slow rules means Postfix itself is slow
COMMAND_TIMEOUT = 60        # seconds for postconf and postfix

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
_COUNT = re.compile(r'\{([0-9]{1,3})(?:(,)([0-9]{0,3}))?\}')
_CLASSES = ('alnum', 'alpha', 'blank', 'cntrl', 'digit', 'graph', 'lower', 'print', 'punct', 'space',
            'upper', 'xdigit')


class RuleError(ValueError):
    """A rule that cannot be written to the map as it was typed."""


class MapError(RuntimeError):
    """The map was not installed, or Postfix did not take it.

    `unchanged` tells whether the map and the Postfix setting are as they
    were before the attempt.
    """

    def __init__(self, message, unchanged=True):
        RuntimeError.__init__(self, message)
        self.unchanged = unchanged


class _TimedOut(Exception):
    """postmap did not finish reading a map in the time it was given."""


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
    # Several * in a row match what one does.
    pattern = re.sub(r'\*+', '*', pattern)
    if pattern.count('*') > MAX_UNBOUNDED:
        raise RuleError('A wildcard pattern may contain * in at most %s places.' % MAX_UNBOUNDED)
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

    Repeats are limited as described at the top of this file: a repeat never
    follows another repeat, a count never follows a group, a group that is
    repeated holds no repeat itself, and the counts of a pattern add up to
    little. Nothing is compiled or run here; the pattern is only read.
    """
    pattern = _text(pattern)
    if not isinstance(pattern, str) or not pattern or len(pattern) > MAX_PATTERN_LENGTH:
        raise RuleError('A pattern is required, up to %s characters.' % MAX_PATTERN_LENGTH)
    if not _PRINTABLE.fullmatch(pattern) or '/' in pattern:
        raise RuleError('A pattern may not contain spaces, line breaks, / or characters outside ASCII.')
    counted = 0
    unbounded = 0
    groups = []             # one entry per open group: True once it holds a repeat
    closed_holds_repeat = False
    previous = 'start'      # start, atom, group or repeat
    position = 0
    while position < len(pattern):
        character = pattern[position]
        if character == '\\':
            if position + 1 >= len(pattern) or pattern[position + 1].isalnum():
                raise RuleError('A backslash may only come before a punctuation character. '
                                'Write [0-9] or [[:alnum:]_] instead of \\d or \\w.')
            position += 2
            previous = 'atom'
            continue
        if character == '[':
            position = _bracket_end(pattern, position)
            previous = 'atom'
            continue
        if character in '*+?{':
            if previous == 'repeat':
                raise RuleError('A repeat (* + ? or a count) cannot follow another repeat.')
            if previous == 'start':
                raise RuleError('A repeat (* + ? or a count) needs something before it to repeat. '
                                'Write \\%s for the character itself.' % character)
            if character == '{':
                count = _COUNT.match(pattern, position)
                if not count:
                    raise RuleError('A repeat count is written {n}, {n,} or {n,m}. Write \\{ for the '
                                    'character itself.')
                if previous == 'group':
                    raise RuleError('A repeat count can follow a single character or [ ], not a group.')
                lowest = int(count.group(1))
                highest = int(count.group(3)) if count.group(3) else lowest
                if highest < lowest:
                    raise RuleError('In a repeat count {n,m} the second number cannot be the smaller one.')
                counted += highest
                if count.group(2) and not count.group(3):
                    unbounded += 1
                position = count.end()
                holds_repeat = True
            else:
                if character == '?':
                    counted += 1
                else:
                    if previous == 'group' and closed_holds_repeat:
                        raise RuleError('A group followed by * or + cannot contain another repeat.')
                    unbounded += 1
                position += 1
                holds_repeat = character != '?'
            if holds_repeat and groups:
                groups[-1] = True
            previous = 'repeat'
            continue
        if character == '(':
            if pattern[position + 1:position + 2] == '?':
                raise RuleError('Groups that begin with (? are not available.')
            groups.append(False)
            if len(groups) > MAX_GROUP_DEPTH:
                raise RuleError('Groups can be placed inside groups %s deep at most.' % MAX_GROUP_DEPTH)
            previous = 'start'
        elif character == ')':
            if not groups:
                raise RuleError('A ) has no matching (.')
            closed_holds_repeat = groups.pop()
            if closed_holds_repeat and groups:
                groups[-1] = True
            previous = 'group'
        elif character == '@':
            raise RuleError('Enter only the part of the address before @; the domain is added for you.')
        elif character in '|^$':
            previous = 'start'
        else:
            previous = 'atom'
        position += 1
    if groups:
        raise RuleError('A ( is not closed.')
    if counted > MAX_COUNTED:
        raise RuleError('The repeat counts of a pattern, with one for each ?, may add up to %s at most. '
                        'Use + or * for longer runs.' % MAX_COUNTED)
    if unbounded > MAX_UNBOUNDED:
        raise RuleError('A pattern may contain * + and {n,} in at most %s places.' % MAX_UNBOUNDED)
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


def disable_rules(cursor, identifiers):
    """Mark rules that are not in the map, so that the page shows them as such and they are not tried again."""
    identifiers = list(identifiers)
    cursor.execute('UPDATE e_pattern_forwarding SET enabled = 0 WHERE id IN (%s)'
                   % ', '.join(['%s'] * len(identifiers)), identifiers)


def build(rules):
    """Split rules of (id, domain, pattern, destination, type) into table lines and refusals.

    Only the rule's text is read here, which costs nothing, so a rule that
    is too long, too costly or over a limit never reaches Postfix.
    """
    entries, rejected, per_domain = [], [], {}
    for identifier, domain, pattern, destination, pattern_type in rules:
        try:
            entry = rule_line(_text(pattern_type), pattern, domain, destination)
            owner = check_domain(domain)
            if per_domain.get(owner, 0) >= MAX_RULES_PER_DOMAIN:
                raise RuleError('A domain can have %s pattern rules; this one is beyond that.'
                                % MAX_RULES_PER_DOMAIN)
            if len(entries) >= MAX_RULES:
                raise RuleError('A server can have %s pattern rules; this one is beyond that.' % MAX_RULES)
            per_domain[owner] = per_domain.get(owner, 0) + 1
            entries.append((identifier, entry))
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


def _run(command, timeout=COMMAND_TIMEOUT):
    done = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, timeout=timeout)
    return done.returncode, done.stdout, done.stderr


def _said(output, error):
    return (error.strip() or output.strip() or 'no message').splitlines()[-1]


def _alias_maps(run):
    code, output, error = run([_tool('postconf'), '-h', PARAMETER], COMMAND_TIMEOUT)
    if code != 0:
        raise MapError('Postfix did not report its %s setting: %s' % (PARAMETER, _said(output, error)))
    value = output.strip()
    return ' '.join(value.split()) if '\n' in value else value


def _set_alias_maps(value, run, main_cf):
    before = os.stat(main_cf)
    code, output, error = run([_tool('postconf'), '-e', '%s = %s' % (PARAMETER, value)], COMMAND_TIMEOUT)
    if code != 0:
        raise MapError('%s could not be changed in %s: %s' % (PARAMETER, main_cf, _said(output, error)))
    # postconf replaces the file; the panel and Postfix keep reading it as before.
    os.chmod(main_cf, stat.S_IMODE(before.st_mode))
    os.chown(main_cf, before.st_uid, before.st_gid)


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


def _read(path):
    """The text of a map, or None where there is no such file."""
    try:
        with open(path) as handle:
            return handle.read()
    except (IOError, OSError, UnicodeDecodeError):
        return None


def _refused_lines(text, map_path, run, timeout):
    """Line numbers of a map with this text that Postfix cannot use, with its reason for each.

    The text is checked in a file beside the map, which is removed again.
    Raises _TimedOut when postmap needs longer than `timeout` seconds.
    """
    path = _write_beside(map_path, text)
    try:
        try:
            code, output, error = run([_tool('postmap'), '-q', PROBE, 'regexp:' + path], timeout)
        except subprocess.TimeoutExpired:
            raise _TimedOut()
        refused = {}
        for line in error.splitlines():
            found = re.search(r'%s, line ([0-9]+): (.*)' % re.escape(path), line)
            if found:
                refused.setdefault(int(found.group(1)), found.group(2).strip())
        # postmap ends with 1 both for "no match", which is expected here, and after a fatal error.
        if not refused and (code not in (0, 1) or 'fatal:' in error or 'panic:' in error):
            raise MapError('Postfix could not read the pattern map: %s' % _said(output, error))
        return refused
    finally:
        if os.path.exists(path):
            os.remove(path)


def _map_text(entries):
    return HEADER + ''.join(line + '\n' for _, line in entries)


def _single_out(entries, rejected, run, map_path):
    """After the whole map was too slow to read: drop the rules that are slow or refused on their own.

    An empty map is tried first. If Postfix cannot read even that in time,
    the rules are not to blame and nothing is changed.
    """
    try:
        _refused_lines(HEADER, map_path, run, CHECK_TIMEOUT)
    except _TimedOut:
        raise MapError('Postfix did not finish reading an empty pattern map in %s seconds.' % CHECK_TIMEOUT)
    slow = 0
    for entry in list(entries):
        try:
            refused = _refused_lines(_map_text([entry]), map_path, run, RULE_TIMEOUT)
            reason = sorted(refused.items())[0][1] if refused else None
        except _TimedOut:
            slow += 1
            if slow > MAX_SLOW_RULES:
                raise MapError('Postfix is too slow to check the pattern rules: more than %s of them each '
                               'took over %s seconds.' % (MAX_SLOW_RULES, RULE_TIMEOUT))
            reason = 'it was not read within %s seconds' % RULE_TIMEOUT
        if reason:
            rejected.append({'id': entry[0], 'reason': 'The mail server cannot use this pattern: %s' % reason})
            entries.remove(entry)


def _install(entries, rejected, run, map_path):
    """Write the lines Postfix accepts to the map. True when the file changed."""
    singled_out = False
    while True:
        text = _map_text(entries)
        try:
            refused = _refused_lines(text, map_path, run, CHECK_TIMEOUT)
        except _TimedOut:
            if singled_out:
                raise MapError('Postfix did not finish reading the pattern map in %s seconds.' % CHECK_TIMEOUT)
            _single_out(entries, rejected, run, map_path)
            singled_out = True
            continue
        if not refused:
            if not os.path.islink(map_path) and _read(map_path) == text:
                return False
            os.replace(_write_beside(map_path, text), map_path)
            return True
        # The header is line 1, so line n holds entry n - 2.
        indexes = sorted(number - 2 for number in refused)
        if indexes[0] < 0 or indexes[-1] >= len(entries):
            raise MapError('Postfix could not read the pattern map: %s' % sorted(refused.items())[0][1])
        for index in reversed(indexes):
            rejected.append({'id': entries[index][0],
                             'reason': 'The mail server cannot use this pattern: %s' % refused[index + 2]})
            del entries[index]


def _put_back(map_path, text, value, setting_touched, reference, run, main_cf):
    """Return the map and the Postfix setting to what they were.

    Answers 'untouched' when both still were, 'restored' when they were put
    back and 'failed' when they could not be.
    """
    try:
        acted = False
        if setting_touched and _alias_maps(run) != value:
            _set_alias_maps(value, run, main_cf)
            acted = True
        if _read(map_path) != text:
            if text is None:
                if reference in re.split(r'[\s,]+', value):
                    # The setting names the map, so the file has to stay.
                    return 'failed'
                os.remove(map_path)
            else:
                os.replace(_write_beside(map_path, text), map_path)
            acted = True
        return 'restored' if acted else 'untouched'
    except Exception:
        return 'failed'


def apply(rules, run=_run, map_path=MAP_PATH, main_cf=MAIN_CF, disable=None):
    """Make Postfix follow the rules that `rules()` returns.

    Returns {'state': ..., 'rejected': [{'id': ..., 'reason': ...}]}. A rule
    listed as rejected is not in the map, and `disable` is called with the
    ids of such rules so that they can be marked. Raises MapError when the
    map could not be written, listed for Postfix or loaded; the map and the
    setting are then put back as they were, so that what Postfix reads and
    what the caller keeps in its database stay the same thing. A server
    that has no rule and never had the map is left untouched.
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

        before = _read(map_path)
        result = {'rejected': []}
        setting_touched = False
        try:
            entries, result['rejected'] = build(saved)
            changed = _install(entries, result['rejected'], run, map_path)

            # The map exists from here on; Postfix must never be pointed at a missing file.
            wanted = alias_maps_with_reference(value, reference)
            if wanted != value:
                setting_touched = True
                _set_alias_maps(wanted, run, main_cf)
                changed = True

            if changed and run([_tool('postfix'), 'status'], COMMAND_TIMEOUT)[0] == 0:
                code, output, error = run([_tool('postfix'), 'reload'], COMMAND_TIMEOUT)
                if code != 0:
                    raise MapError('The pattern map was written, but Postfix did not reload: %s'
                                   % _said(output, error))
        except Exception as error:
            message = str(error) if isinstance(error, MapError) else (
                'The pattern map could not be installed: %s' % error)
            outcome = _put_back(map_path, before, value, setting_touched, reference, run, main_cf)
            if outcome == 'restored':
                message += ' The previous pattern map was put back.'
            elif outcome == 'failed':
                message += ' The previous pattern map could not be put back.'
            raise MapError(message, outcome != 'failed')
        # Marked only now that the map without them is what Postfix uses.
        if result['rejected'] and disable is not None:
            try:
                disable([refused['id'] for refused in result['rejected']])
            except Exception as error:
                result['unmarked'] = str(error)
        result['state'] = 'updated' if changed else 'unchanged'
        return result
    except (IOError, OSError, subprocess.SubprocessError) as error:
        raise MapError('The pattern map could not be installed: %s' % error)
    finally:
        if lock is not None:
            os.close(lock)


def apply_saved_rules(run=_run, map_path=MAP_PATH, main_cf=MAIN_CF):
    """As root inside the panel: apply the rules of the panel's database and mark those left out."""
    from django.db import connection

    def rules():
        with connection.cursor() as cursor:
            return read_rules(cursor)

    def disable(identifiers):
        with connection.cursor() as cursor:
            disable_rules(cursor, identifiers)

    return apply(rules, run, map_path, main_cf, disable)


def _log_failed_rebuild(error):
    try:
        from plogical import CyberCPLogFileWriter as logging
        logging.CyberCPLogFileWriter.writeToFile(
            'The pattern forwarding map was not rebuilt after a removal: %s [patternForwardingMap]' % error)
    except Exception:
        pass


def _rebuild(map_path):
    try:
        if not os.path.lexists(map_path):
            return
        if os.geteuid() == 0:
            apply_saved_rules(map_path=map_path)
            return
        from plogical.processUtilities import ProcessUtilities
        result = parse_result(ProcessUtilities.outputExecutioner(HELPER_COMMAND))
        if not result.get('status'):
            raise MapError(result.get('error_message'))
    except Exception as error:
        _log_failed_rebuild(error)


def rebuild_after_removal(map_path=MAP_PATH):
    """Drop the map lines of rules that left the database with their website or mail domain.

    The rules go by cascade when a website, a child domain or a mail domain
    is deleted. Their lines would keep rewriting recipients of that domain,
    also after the domain is added again under another account, so every
    such deletion calls this. It runs once the deletion is committed, as
    root directly and from the panel's web process through the root helper,
    does nothing on a server that has no map, and never fails its caller:
    a failure is written to the panel's log.
    """
    try:
        from django.db import transaction
        transaction.on_commit(lambda: _rebuild(map_path))
    except Exception as error:
        _log_failed_rebuild(error)


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

    def disable(identifiers):
        disable_rules(cursor, identifiers)
        connection.commit()

    try:
        result = apply(lambda: read_rules(cursor), run, map_path, main_cf, disable)
    finally:
        connection.close()
    if result['state'] == 'updated':
        log('Pattern forwarding rules are now in %s and Postfix uses them.' % map_path)
    if result.get('unmarked'):
        log('WARNING: Pattern forwarding rules that are not in use could not be marked as such: %s'
            % result['unmarked'])
    for refusal in result['rejected']:
        log('WARNING: Pattern forwarding rule %s is not in use and is shown as such on its page: %s'
            % (refusal['id'], refusal['reason']))
    return result['state']
