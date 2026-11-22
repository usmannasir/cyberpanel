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
import time

MAP_PATH = '/etc/postfix/virtual_regexp'
MAIN_CF = '/etc/postfix/main.cf'
PARAMETER = 'virtual_alias_maps'
HELPER_COMMAND = '/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/mailUtilities.py applyPatternForwarding'

# Every smtpd and cleanup process compiles every line of the map, and smtpd
# runs each recipient through the lines, so the cost of one rule is paid by
# all mail of the server. Two things make a line costly in the C library.
#
# A counted repeat is expanded into copies and stacked counts multiply, so a
# repeat never follows a repeat, a count never follows a group and a group
# that is repeated holds no repeat.
#
# After an open-ended repeat (a wildcard *, or * + {n,} in an expression) the
# matcher has to remember, for every item that can match more than one
# character, whether it is in play: each such item doubles the states it may
# build, and it keeps every state it has built until the process ends. A
# line with 90 of them was measured at 26 microseconds and 3 KB kept for
# every character of every new address. With at most 4 such items the
# matcher has 16 combinations to build, once per process, and the 32 items a
# pattern may have in all keep each of them small; after that an address
# costs a table walk. Three open-ended repeats are enough for "*a*b*".
MAX_PATTERN_LENGTH = 64     # characters as typed; a local part is no longer than that
MAX_ATOMS = 32              # items that match one character each, counted copies included
MAX_UNBOUNDED = 3           # "*" in a wildcard; "*", "+" and "{n,}" in an expression
MAX_AFTER_REPEAT = 4        # "?" of a wildcard after its first "*"; in an expression the
                            # . [ ] | ? and counted copies after its first open-ended
                            # repeat or inside a repeated group
MAX_COUNTED = 16            # all {n}, {n,m} counts of an expression added up, plus one for each "?"
MAX_GROUP_DEPTH = 4         # groups inside groups
MIN_PRIORITY, MAX_PRIORITY = 1, 999

# A rule costs every recipient of the server a little, so their number is
# limited. An account cannot use up what others may add: each account can
# always have its first RESERVED_RULES_PER_ACCOUNT rules, and only rules
# beyond those draw on the SHARED_RULES of the server. The map therefore
# never holds more than SHARED_RULES plus that reserve for each account.
# Where a limit is exceeded the newest rules are the ones left out.
MAX_RULES_PER_DOMAIN = 20
MAX_RULES_PER_ACCOUNT = 40
RESERVED_RULES_PER_ACCOUNT = 5
SHARED_RULES = 200

# postmap reads a map of this size in a fraction of a second. A check that
# takes longer is given up, so that no rule can keep the helper waiting.
CHECK_TIMEOUT = 10          # seconds for the whole map, and for an empty one
RULE_TIMEOUT = 3            # seconds for one rule on its own
MAX_SLOW_RULES = 5          # more than this many slow rules means Postfix itself is slow
COMMAND_TIMEOUT = 60        # seconds for postconf and postfix

# Postfix restarts its programs on a reload, so rule changes cause one at
# most this often. The map is written at once; see _reload().
RELOAD_INTERVAL = 60
STATE = '/run/cyberpanel-pattern-forwarding'

RULES_QUERY = ('SELECT p.id, p.domain_id, p.pattern, p.destination, p.pattern_type, p.priority, '
               'COALESCE(w.admin_id, cw.admin_id) '
               'FROM e_pattern_forwarding p '
               'LEFT JOIN e_domains d ON d.domain = p.domain_id '
               'LEFT JOIN websiteFunctions_websites w ON w.id = d.domainOwner_id '
               'LEFT JOIN websiteFunctions_childdomains c ON c.id = d.childOwner_id '
               'LEFT JOIN websiteFunctions_websites cw ON cw.id = c.master_id '
               'WHERE p.enabled = 1 ORDER BY p.id')
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
    """The map was not installed, or Postfix did not take it."""


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


def check_priority(priority):
    """The priority as a whole number in the range the page offers."""
    if isinstance(priority, bool) or not isinstance(priority, (int, str)):
        priority = None
    try:
        priority = int(priority)
    except (TypeError, ValueError):
        priority = None
    if priority is None or not MIN_PRIORITY <= priority <= MAX_PRIORITY:
        raise RuleError('The priority must be a whole number from %s to %s.' % (MIN_PRIORITY, MAX_PRIORITY))
    return priority


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
    if len(pattern) - pattern.count('*') > MAX_ATOMS:
        raise RuleError('A wildcard pattern may hold %s characters besides *.' % MAX_ATOMS)
    first = pattern.find('*')
    if first >= 0 and pattern.count('?', first) > MAX_AFTER_REPEAT:
        raise RuleError('After its first * a wildcard pattern may contain at most %s ?.' % MAX_AFTER_REPEAT)
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
    ends a field, so neither may appear, and "@" belongs to the frame and
    not to the pattern. Every "(" must be closed and no ")" may come first:
    otherwise an alternative could leave the group and match addresses of
    other domains. Escapes of letters and digits are refused because they
    mean something else to Postfix than to most people (\\d is a plain d,
    \\1 is a back-reference).

    What a pattern may cost is limited as described at the top of this
    file. Nothing is compiled or run here; the pattern is only read.
    """
    pattern = _text(pattern)
    if not isinstance(pattern, str) or not pattern or len(pattern) > MAX_PATTERN_LENGTH:
        raise RuleError('A pattern is required, up to %s characters.' % MAX_PATTERN_LENGTH)
    if not _PRINTABLE.fullmatch(pattern) or '/' in pattern:
        raise RuleError('A pattern may not contain spaces, line breaks, / or characters outside ASCII.')
    if '@' in pattern:
        raise RuleError('Enter only the part of the address before @, without any @; the domain is added '
                        'for you.')
    tally = {'atoms': 0, 'counted': 0, 'unbounded': 0, 'after': 0}
    groups = []             # one [holds a repeat, weight seen before any open-ended repeat] per open group
    closed = [False, 0]     # the same for the group that closed last
    previous = 'start'      # start, atom, group or repeat
    wide = False            # whether the last atom matches more than one character

    def weigh(amount):
        # Counts toward the limit once an open-ended repeat was seen; before that
        # it is kept with its group, which may turn out to be repeated itself.
        if tally['unbounded']:
            tally['after'] += amount
        elif groups:
            groups[-1][1] += amount

    position = 0
    while position < len(pattern):
        character = pattern[position]
        if character == '\\':
            if position + 1 >= len(pattern) or pattern[position + 1].isalnum():
                raise RuleError('A backslash may only come before a punctuation character. '
                                'Write [0-9] or [[:alnum:]_] instead of \\d or \\w.')
            position += 2
            tally['atoms'] += 1
            previous, wide = 'atom', False
            continue
        if character == '[':
            position = _bracket_end(pattern, position)
            tally['atoms'] += 1
            weigh(1)
            previous, wide = 'atom', True
            continue
        if character in '*+?{':
            if previous == 'repeat':
                raise RuleError('A repeat (* + ? or a count) cannot follow another repeat.')
            if previous == 'start':
                raise RuleError('A repeat (* + ? or a count) needs something before it to repeat. '
                                'Write \\%s for the character itself.' % character)
            holds_repeat = True
            if character == '{':
                count = _COUNT.match(pattern, position)
                if not count:
                    raise RuleError('A repeat count is written {n}, {n,} or {n,m}. Write \\{ for the '
                                    'character itself.')
                if previous == 'group':
                    raise RuleError('A repeat count can follow a single character or [ ], not a group.')
                lowest = int(count.group(1))
                open_ended = bool(count.group(2)) and not count.group(3)
                highest = int(count.group(3)) if count.group(3) else lowest
                if highest < lowest:
                    raise RuleError('In a repeat count {n,m} the second number cannot be the smaller one.')
                tally['counted'] += highest
                tally['atoms'] += max(highest - 1, 0)
                # Each copy of a wide atom is a wide atom; of a plain one, each copy that may be absent.
                weigh(max(highest - 1, 0) if wide else highest - lowest)
                if open_ended:
                    tally['unbounded'] += 1
                position = count.end()
            elif character == '?':
                tally['counted'] += 1
                weigh(1)
                holds_repeat = False
                position += 1
            else:
                if previous == 'group':
                    if closed[0]:
                        raise RuleError('A group followed by * or + cannot contain another repeat.')
                    # What the group holds is now inside a repeat.
                    tally['after'] += closed[1]
                tally['unbounded'] += 1
                position += 1
            if holds_repeat and groups:
                groups[-1][0] = True
            previous = 'repeat'
            continue
        if character == '(':
            if pattern[position + 1:position + 2] == '?':
                raise RuleError('Groups that begin with (? are not available.')
            groups.append([False, 0])
            if len(groups) > MAX_GROUP_DEPTH:
                raise RuleError('Groups can be placed inside groups %s deep at most.' % MAX_GROUP_DEPTH)
            previous = 'start'
        elif character == ')':
            if not groups:
                raise RuleError('A ) has no matching (.')
            closed = groups.pop()
            if groups:
                groups[-1][0] = groups[-1][0] or closed[0]
                if pattern[position + 1:position + 2] not in ('*', '+'):
                    groups[-1][1] += closed[1]
            previous = 'group'
        elif character == '|':
            weigh(1)
            previous = 'start'
        elif character in '^$':
            previous = 'start'
        else:
            tally['atoms'] += 1
            if character == '.':
                weigh(1)
            previous, wide = 'atom', character == '.'
        position += 1
    if groups:
        raise RuleError('A ( is not closed.')
    if tally['atoms'] > MAX_ATOMS:
        raise RuleError('A pattern may describe %s characters at most, counted copies included.' % MAX_ATOMS)
    if tally['counted'] > MAX_COUNTED:
        raise RuleError('The repeat counts of a pattern, with one for each ?, may add up to %s at most. '
                        'Use + or * for longer runs.' % MAX_COUNTED)
    if tally['unbounded'] > MAX_UNBOUNDED:
        raise RuleError('A pattern may contain * + and {n,} in at most %s places.' % MAX_UNBOUNDED)
    if tally['after'] > MAX_AFTER_REPEAT:
        raise RuleError('After its first * + or {n,}, and inside a repeated group, a pattern may contain '
                        'at most %s of: . [ ] | ? and counted copies.' % MAX_AFTER_REPEAT)
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
    """Enabled rules, oldest first, each with its priority and the account that owns its domain."""
    cursor.execute(RULES_QUERY)
    return [tuple(row) for row in cursor.fetchall()]


def disable_rules(cursor, identifiers):
    """Mark rules that are not in the map, so that the page shows them as such and they are not tried again."""
    identifiers = list(identifiers)
    cursor.execute('UPDATE e_pattern_forwarding SET enabled = 0 WHERE id IN (%s)'
                   % ', '.join(['%s'] * len(identifiers)), identifiers)


def build(rules):
    """Split rules into table lines, in the order Postfix is to try them, and refusals.

    A rule is (id, domain, pattern, destination, type, priority, account);
    the last two may be left off. Only the rule's text is read here, which
    costs nothing, so a rule that is too costly or over a limit never
    reaches Postfix. Limits are applied oldest rule first: the one left out
    is the newest, whatever its priority, and never a rule of somebody else.
    """
    admitted, rejected, per_domain, per_account = [], [], {}, {}
    shared = 0
    for rule in sorted((tuple(rule) for rule in rules), key=lambda rule: rule[0]):
        rule += (100, None)[len(rule) - 5:]
        identifier, domain, pattern, destination, pattern_type, priority, account = rule[:7]
        try:
            entry = rule_line(_text(pattern_type), pattern, domain, destination)
            owner = check_domain(domain)
            # A domain whose account is not known stands for itself.
            account = ('domain', owner) if account is None else ('account', account)
            owned = per_account.get(account, 0)
            if per_domain.get(owner, 0) >= MAX_RULES_PER_DOMAIN:
                raise RuleError('A domain can have %s pattern rules; this one is beyond that.'
                                % MAX_RULES_PER_DOMAIN)
            if owned >= MAX_RULES_PER_ACCOUNT:
                raise RuleError('An account can have %s pattern rules on all its domains; this one is '
                                'beyond that.' % MAX_RULES_PER_ACCOUNT)
            if owned >= RESERVED_RULES_PER_ACCOUNT:
                if shared >= SHARED_RULES:
                    raise RuleError('This server has reached its limit of pattern rules; an account can '
                                    'still have %s.' % RESERVED_RULES_PER_ACCOUNT)
                shared += 1
            per_domain[owner] = per_domain.get(owner, 0) + 1
            per_account[account] = owned + 1
            try:
                order = int(priority)
            except (TypeError, ValueError):
                order = 100
            admitted.append((order, identifier, entry))
        except RuleError as error:
            rejected.append({'id': identifier, 'reason': str(error)})
    return [(identifier, entry) for _, identifier, entry in sorted(admitted)], rejected


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


def _reload_later(seconds):
    """Run the helper again after `seconds`, in a process of its own that outlives this one."""
    subprocess.Popen(['/bin/sh', '-c', 'sleep %d; exec %s' % (seconds, HELPER_COMMAND)],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True, close_fds=True)


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
    """After the whole map was too slow to read: drop the rules that are to blame, and only those.

    A rule is dropped when Postfix refuses it on its own, or when it alone
    is too slow twice while an empty map is read at once in between. A busy
    server makes everything slow, the empty map included; then no rule is
    blamed, the attempt ends and nothing is changed.
    """
    busy = MapError('Postfix is too slow to check the pattern rules just now; nothing was changed.')

    def alone(entry):
        refused = _refused_lines(_map_text([entry]), map_path, run, RULE_TIMEOUT)
        return sorted(refused.items())[0][1] if refused else None

    def empty_map_within(seconds):
        try:
            _refused_lines(HEADER, map_path, run, seconds)
        except _TimedOut:
            raise busy

    empty_map_within(CHECK_TIMEOUT)
    slow = 0
    for entry in list(entries):
        try:
            reason = alone(entry)
        except _TimedOut:
            empty_map_within(RULE_TIMEOUT)
            try:
                reason = alone(entry)
            except _TimedOut:
                slow += 1
                if slow > MAX_SLOW_RULES:
                    raise busy
                reason = 'it was not read within %s seconds, twice' % RULE_TIMEOUT
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


def _stamp(path, when):
    with open(path, 'w'):
        pass
    os.utime(path, (when, when))


def _reload(changed, run, state, clock, later, result):
    """Have Postfix read the map again, at most once in RELOAD_INTERVAL seconds.

    A reload that comes too soon after the last one is owed instead: a
    marker is left and the helper is started again for the moment it falls
    due. That run, like any other run of apply() for whatever reason, sees
    the marker and reloads. Should that process be lost, Postfix still
    takes the map up by itself, because each of its programs reads it when
    it starts and none lives long (max_idle, max_use), and a restart of
    Postfix reads it in any case.
    """
    owed = state + '.pending'
    if not changed and not os.path.exists(owed):
        return
    if run([_tool('postfix'), 'status'], COMMAND_TIMEOUT)[0] != 0:
        # Postfix is not running and reads the map when it starts.
        try:
            os.remove(owed)
        except OSError:
            pass
        return
    try:
        wait = os.path.getmtime(state + '.reloaded') + RELOAD_INTERVAL - clock()
    except OSError:
        wait = 0
    if wait > 0:
        try:
            if not os.path.exists(owed):
                _stamp(owed, clock())
                later(int(wait) + 1)
            result['reload_in'] = int(wait) + 1
            return
        except Exception:
            # The reload cannot be put off safely, so it is done now.
            pass
    code, output, error = run([_tool('postfix'), 'reload'], COMMAND_TIMEOUT)
    if code != 0:
        raise MapError('The pattern map was written, but Postfix did not reload: %s' % _said(output, error))
    try:
        _stamp(state + '.reloaded', clock())
        if os.path.exists(owed):
            os.remove(owed)
    except OSError:
        pass


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


def apply(rules, run=_run, map_path=MAP_PATH, main_cf=MAIN_CF, disable=None, state=None, clock=time.time,
          later=None):
    """Make Postfix follow the rules that `rules()` returns.

    Returns {'state': ..., 'rejected': [{'id': ..., 'reason': ...}]}, with
    'reload_in' (seconds) when the reload is owed rather than done. A rule
    listed as rejected is not in the map, and `disable` is called with the
    ids of such rules so that they can be marked. Raises MapError when the
    map could not be written, listed for Postfix or loaded; the map and the
    setting are then put back as they were. A server that has no rule and
    never had the map is left untouched.
    """
    if not os.path.isfile(main_cf):
        return {'state': 'no mail server', 'rejected': []}
    state = state or STATE
    later = later or _reload_later
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
            wanted = alias_maps_with_reference(value, reference)
            if wanted == value and before == _map_text(entries) and not os.path.islink(map_path):
                # The map holds exactly these rules; it was checked when it was written.
                changed = False
            else:
                changed = _install(entries, result['rejected'], run, map_path)
                # The map exists from here on; Postfix must never be pointed at a missing file.
                if wanted != value:
                    setting_touched = True
                    _set_alias_maps(wanted, run, main_cf)
                    changed = True
            _reload(changed, run, state, clock, later, result)
        except Exception as error:
            message = str(error) if isinstance(error, MapError) else (
                'The pattern map could not be installed: %s' % error)
            outcome = _put_back(map_path, before, value, setting_touched, reference, run, main_cf)
            if outcome == 'restored':
                message += ' The previous pattern map was put back.'
            elif outcome == 'failed':
                message += ' The previous pattern map could not be put back.'
            raise MapError(message)
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
    """What the root helper prints for the panel: one line of plain ASCII, whatever the result holds."""
    return RESULT_MARK + json.dumps(result, ensure_ascii=True, default=str)


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
