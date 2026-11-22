"""Run the real top level of cyberpanel.sh where it can change nothing.

The tests that use this execute the installer script itself: its argument
handling, its checks of the server, its status events and its exit handling.
What would install or configure something is replaced, and three separate
things keep a mistake here from touching the machine the tests run on:

1. every function that installs or configures is replaced as a whole
   (STUBBED_PHASES), and a test fails when the script calls a function at its
   top level that is in neither list below;
2. PATH holds only a directory of links to harmless tools, so a command that
   was not replaced is "not found" instead of being run;
3. every absolute system path in the script text points into a temporary
   directory.
"""
import ast
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]

TOP_LEVEL_START = '\nRead_Admin_Password_File\n'

# Functions of the script that run as they are.
REAL_FUNCTIONS = (
    'Check_Usage', 'Read_Admin_Password_File', 'Mask_Arguments', 'Use_Admin_Password_File',
    'Set_Default_Variables', 'Check_Root', 'Check_Server_IP',
    'Check_OS', 'Check_Virtualization', 'Check_Panel', 'Check_Process', 'Check_Provider',
    'Check_Argument', 'Argument_Mode', 'Interactive_Mode', 'Validate_Remote_MySQL',
    'Fail_Install', 'Install_Step', 'Pre_Install_Setup_Git_URL', 'Hold_Panel',
    'Post_Install_Display_Final_Info',
)

# Functions that install or configure. Each is replaced by a line in the
# phase record; QA_FAIL_AT names one that fails the way the real one does.
STUBBED_PHASES = {
    'Pre_Install_Setup_Repository': 'Fail_Install package_manager',
    'Pre_Install_Required_Components': 'false; Check_Return',
    'Pre_Install_Python_Environment': 'exit 1',
    'Pre_Install_Get_Panel_Source': 'false; Check_Return "git clone"',
    'Pre_Install_System_Tweak': 'exit 1',
    'Post_Install_Addon_Memcached': 'exit 1',
    'Post_Install_Addon_Redis': 'exit 1',
    'Post_Install_Required_Components': 'exit 1',
    'Post_Install_PHP_Session_Setup': 'exit 1',
    'Post_Install_PHP_TimezoneDB': 'cd /nonexistent-directory || exit',
    'Post_Install_Regenerate_Cert': 'exit 1',
    # Cannot fail a run: when the service does not start, the real one only
    # writes a warning to the log and the installation goes on.
    'Post_Install_Start_Web_Terminal': 'log_warning "Web Terminal service could not be started"',
    'Post_Install_Regenerate_Webadmin_Console_Passwd': 'exit 1',
    'Post_Install_Setup_Watchdog': 'exit 1',
    'Post_Install_Setup_Utility': 'exit 1',
}

# Replaced by more than a line in the phase record: see COMMAND_STUBS and
# Installer.harness.
SPECIAL_STUBS = ('Main_Installation', 'Post_Install_Tweak')

# Tools the script may really run. Everything else is "command not found".
HARMLESS_TOOLS = (
    'awk', 'cat', 'chmod', 'cut', 'date', 'df', 'expr', 'find', 'free', 'grep', 'head',
    'mkdir', 'od', 'python3', 'sed', 'stat', 'tail', 'tee', 'touch', 'tr', 'uname',
)

SYSTEM_PATH = re.compile(r'(?<![\w./])/(etc|var|usr|root|home|tmp|opt|sys)/')

UBUNTU_22 = 'PRETTY_NAME="Ubuntu 22.04.5 LTS"\nNAME="Ubuntu"\nVERSION_ID="22.04"\nID=ubuntu\n'
DEBIAN_12 = 'PRETTY_NAME="Debian GNU/Linux 12 (bookworm)"\nNAME="Debian GNU/Linux"\nVERSION_ID="12"\nID=debian\n'

CLI_OK = '{"success": 1, "errorMessage": "None"}'
CLI_FAILED = '{"success": 0, "errorMessage": "fixture failure"}'

COMMAND_STUBS = r'''
note() { printf '%s\n' "$*" >> "$QA_CALLS"; }
curl() {
  note "curl $*"
  case "$*" in
    *cyberpanel.net/version.txt*) printf '%s' "$QA_VERSION" ;;
    *cyberpanel.sh/?ip*) printf '%s' "$QA_IP" ;;
    *cyberpanel.sh/?country*) printf 'US' ;;
    *latest.php*) printf 'LSWS_STABLE=6.3.4 BUILD 1\n' ;;
    *127.0.0.1:8090*)
      if [ "$QA_PANEL_EXIT" != 0 ] && [ "$QA_PANEL_HANGS" = 1 ]; then
        # A request that gets no answer lasts as long as it was allowed to.
        local limit="$*"
        limit=${limit#*--max-time }
        SECONDS=$((SECONDS + ${limit%% *}))
      fi
      return "$QA_PANEL_EXIT"
      ;;
  esac
  return 0
}
id() { printf '%s\n' "$QA_UID"; }
hostnamectl() { :; }
systemctl() {
  note "systemctl $*"
  if [ "$1" = is-active ]; then [ "$3" = "$QA_ACTIVE_SERVICE" ]; return; fi
  return 0
}
# Time passes without being waited for: SECONDS is the clock of the script.
sleep() { SECONDS=$((SECONDS + ${1%.*})); }
timeout() { return 1; }
reboot() { note "reboot"; }
hostname() { printf '%s\n' 'qa.example.test'; }
dig() { if [ "$QA_DNS" = 1 ]; then printf '%s\n' '192.0.2.1'; fi; }
cyberpanel() {
  note "cyberpanel $*"
  if [ "$1" = createWebsite ]; then printf '%s\n' "$QA_CREATE_OUTPUT"; fi
  if [ "$1" = hostNameSSL ]; then
    note "result-during-the-certificate-request=$Hostname_SSL_Result"
    # QA_TLS_SIGNAL: the script is sent this signal while the request runs.
    if [ -n "$QA_TLS_SIGNAL" ]; then kill -s "$QA_TLS_SIGNAL" "$$"; fi
    printf '%s\n' "$QA_TLS_OUTPUT"
  fi
  return 0
}
phase() {
  printf '%s\n' "$1" >> "$QA_PHASES"
  # QA_SIGNAL_AT: the script is sent QA_SIGNAL when this phase starts.
  if [ -n "$QA_SIGNAL_AT" ] && [ "$QA_SIGNAL_AT" = "$1" ]; then kill -s "$QA_SIGNAL" "$$"; fi
  [ "$QA_FAIL_AT" = "$1" ]
}
panel_tree() {
  # What install.py leaves of the panel, as far as the script looks at it
  # afterwards: the tree's adminPass.py (QA_TREE=old: one that cannot read the
  # password from a file).
  mkdir -p "$QA_ROOT/etc/cyberpanel" "$QA_ROOT/usr/local/CyberCP/plogical"
  printf '%s\n' "parser.add_argument('--password', help='New Password')" > "$QA_ROOT/usr/local/CyberCP/plogical/adminPass.py"
  if [ "$QA_TREE" != old ]; then
    printf '%s\n' "parser.add_argument('--password-file')" >> "$QA_ROOT/usr/local/CyberCP/plogical/adminPass.py"
  fi
}
Main_Installation() {
  # What cyberpanel.sh does here is covered by test_install_exit_status. This
  # stands in for install.py: the real status module, driven by the name of
  # the run that the script exported.
  phase Main_Installation
  python3 -I "$QA_DRIVER" "$QA_INSTALL_DIRECTORY" "$QA_EVENTS" $QA_PYTHON_STEPS
  Install_Status=$?
  if [[ "$Install_Status" -ne 0 ]]; then
    exit "$Install_Status"
  fi
  [[ "$QA_FAIL_AT" = "No_Completion_Marker" ]] && exit 1
  panel_tree
  return 0
}
'''

# Stand-in for the interpreter the script runs after install.py. Given the
# tree's adminPass.py it records how it was called; given a program to read
# ("-": the check of the admin password) it keeps that program. Each ends with
# the status the test asks for.
INSTALLER_PYTHON = '''#!/bin/sh
if [ "$1" = - ]; then
  printf 'password-check\\n' >> "$QA_CALLS"
  cat > "$QA_PASSWORD_CHECK"
  exit "$QA_PASSWORD_CHECK_EXIT"
fi
printf '%s\\n' "$@" > "$QA_ADMINPASS_CALL"
exit "$QA_ADMINPASS_EXIT"
'''

PYTHON_DRIVER = '''
import sys
sys.path.insert(0, sys.argv[1])
import install_events
install_events.EVENTS_FILE = sys.argv[2]
for directive in sys.argv[3:]:
    action, _, value = directive.partition(':')
    if action == 'step':
        install_events.step(value)
    elif action == 'skip':
        install_events.step(value, False)
    elif action == 'finish':
        install_events.finish()
    elif action == 'exit':
        sys.exit(int(value))
'''

DEFAULT_PYTHON_STEPS = 'step:php step:database step:ftp step:dns step:email step:panel finish'


def as_a_terminal_starts_it(mask):
    """What the script's process is given before it starts: signals as a
    terminal leaves them (a test run that was itself started in the background
    has interrupts ignored, and a shell cannot react to a signal it was started
    to ignore), and the file mode mask the test asks for."""
    def prepare():
        for number in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
            signal.signal(number, signal.SIG_DFL)
        if mask is not None:
            os.umask(mask)
    return prepare


def parse_as_python_36(source, interpreter=None):
    """Parse Python source as the interpreter of AlmaLinux 8 (3.6) would.

    From Python 3.8 on the parser can be told to refuse syntax that 3.6 does
    not have. Python 3.6 and 3.7 have no such switch, and there the proof is
    that the running interpreter parses the source. ``interpreter`` is the
    version to behave as; it is the running one unless a test says otherwise.
    """
    if (interpreter or sys.version_info) >= (3, 8):
        return ast.parse(source, feature_version=(3, 6))
    return ast.parse(source)


def stand_in_interpreter(path):
    """A file at ``path`` that runs this Python with the arguments it is given.

    It takes the place of an interpreter that the script names. The tests can
    themselves be run by an interpreter that lives where those names point (the
    panel's own, on a server that has a panel); the name of the running
    interpreter is therefore never put into text of the script, where a later
    replacement of a path could change it.
    """
    path.write_text('#!/bin/sh\nexec "%s" "$@"\n' % sys.executable, encoding='utf-8')
    path.chmod(0o755)
    return path


def with_stand_ins(text, stand_ins):
    """``text`` with every name in ``stand_ins`` replaced by its stand-in.

    One pass: what a replacement put in is not looked at again, so a stand-in
    that holds one of the names stays as it is. Where one name begins with
    another, the longer one is taken. Every name has to be in the text.
    """
    table = dict((str(real), str(stand_in)) for real, stand_in in stand_ins)
    for real in table:
        if real not in text:
            raise AssertionError('%s is not in the text' % real)
    names = sorted(table, key=len, reverse=True)
    return re.sub('|'.join(re.escape(name) for name in names), lambda match: table[match.group(0)], text)


def script_parts(source=None):
    """The function definitions and the top level of the installer script."""
    if source is None:
        source = (ROOT / 'cyberpanel.sh').read_text(encoding='utf-8')
    start = source.index(TOP_LEVEL_START)
    return source[:start + 1], source[start + 1:]


def top_level_functions(top_level):
    """Names of the script's own functions that its top level calls."""
    names = []
    for line in top_level.splitlines():
        for match in re.finditer(r'(?:^|\|\| |&& |; |then |else )\s*([A-Z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+)(?=\s|$)', line):
            names.append(match.group(1))
    return names


class Installer:
    """One temporary machine and what a run of the installer left in it."""

    def __init__(self, test):
        self.directory = tempfile.TemporaryDirectory()
        test.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for path in ('bin', 'etc', 'var/log', 'usr/local', 'tmp', 'home'):
            (self.root / path).mkdir(parents=True)
        for tool in HARMLESS_TOOLS:
            found = shutil.which(tool)
            if found:
                (self.root / 'bin' / tool).symlink_to(found)
        self.os_release(UBUNTU_22)
        self.calls = self.root / 'calls'
        self.phases = self.root / 'phases'
        self.events_file = self.root / 'var/log/cyberpanel/install_events.log'
        self.install_log = self.root / 'var/log/installLogs.txt'
        self.driver = self.root / 'driver.py'
        self.driver.write_text(PYTHON_DRIVER)
        self.stored_password = self.root / 'etc/cyberpanel/adminPass'
        self.adminpass_call = self.root / 'adminpass-call'
        self.password_check = self.root / 'password-check.py'
        installer_python = self.root / 'usr/local/CyberPanel/bin/python'
        installer_python.parent.mkdir(parents=True)
        installer_python.write_text(INSTALLER_PYTHON)
        installer_python.chmod(0o755)

    def os_release(self, content):
        (self.root / 'etc/os-release').write_text(content)

    def path(self, absolute):
        return self.root / absolute.lstrip('/')

    def relocate(self, text):
        return SYSTEM_PATH.sub(lambda match: '%s/%s/' % (self.root, match.group(1)), text)

    def harness(self):
        functions, top_level = script_parts()
        # Of Post_Install_Tweak, the parts that decide how a run ends are the
        # real ones, in their order: setting and confirming the admin password,
        # starting the panel, and the hostname step.
        start = functions.index('\nPost_Install_Tweak() {\n')
        body = functions[start:functions.index('\n}\n', start)]
        password = body[body.index('\nif ! Set_Admin_Password; then\n'):
                        body.index('\nConfigure_Default_PHP_CLI || return 1\n') + 1]
        rest = body[body.index('\nConfigure_Default_PHP_CLI || return 1\n'):]
        password += rest[rest.index('\nStart_Panel\n'):][:len('\nStart_Panel\n')]
        tweak = rest[rest.index('\nInstall_Step hostname_ssl\n'):]
        if rest.index('\nStart_Panel\n') > rest.index('\nInstall_Step hostname_ssl\n'):
            raise AssertionError('the panel is started after the hostname step')
        stubs = [COMMAND_STUBS]
        for name, failure in sorted(STUBBED_PHASES.items()):
            stubs.append('%s() { phase %s && { %s; }; return 0; }\n' % (name, name, failure))
        stubs.append('Post_Install_Tweak() {\nphase Post_Install_Tweak%s%s\n}\n'
                     % (self.relocate(password), self.relocate(tweak)))
        return self.relocate(functions) + ''.join(stubs) + self.relocate(top_level)

    def run(self, *arguments, **options):
        """Run the installer with these arguments; returns the finished process."""
        stdin = options.pop('stdin', '')
        process = self.start(*arguments, **options)
        try:
            output, errors = process.communicate(stdin, timeout=120)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise
        return subprocess.CompletedProcess(process.args, process.returncode, output, errors)

    def start(self, *arguments, **options):
        """Start the installer with these arguments; returns the running process."""
        environment = {
            'PATH': str(self.root / 'bin'),
            'HOME': str(self.root / 'home'),
            'QA_CALLS': str(self.calls),
            'QA_PHASES': str(self.phases),
            'QA_DRIVER': str(self.driver),
            'QA_INSTALL_DIRECTORY': str(ROOT / 'install'),
            'QA_EVENTS': str(self.events_file),
            'QA_VERSION': options.pop('version', '{"version":"3.0","build":11}'),
            'QA_IP': options.pop('ip', '192.0.2.10'),
            'QA_UID': str(options.pop('uid', 0)),
            'QA_PANEL_EXIT': str(options.pop('panel_exit', 0)),
            'QA_PANEL_HANGS': str(int(options.pop('panel_hangs', False))),
            'QA_ACTIVE_SERVICE': options.pop('active_service', ''),
            'QA_DNS': str(int(options.pop('dns', False))),
            'QA_CREATE_OUTPUT': options.pop('create_output', CLI_OK),
            'QA_TLS_OUTPUT': options.pop('tls_output', CLI_OK),
            'QA_TLS_SIGNAL': options.pop('tls_signal', ''),
            'QA_FAIL_AT': options.pop('fail_at', ''),
            'QA_SIGNAL_AT': options.pop('signal_at', ''),
            'QA_SIGNAL': options.pop('signal', 'TERM'),
            'QA_PYTHON_STEPS': options.pop('python_steps', DEFAULT_PYTHON_STEPS),
            'QA_ROOT': str(self.root),
            'QA_TREE': options.pop('tree', 'new'),
            'QA_ADMINPASS_CALL': str(self.adminpass_call),
            'QA_ADMINPASS_EXIT': str(options.pop('adminpass_exit', 0)),
            'QA_PASSWORD_CHECK': str(self.password_check),
            'QA_PASSWORD_CHECK_EXIT': str(options.pop('password_check_exit', 0)),
        }
        environment.update(options.pop('environment', {}))
        # With trace=True every command that runs is written to the error output.
        shell = [shutil.which('bash')] + (['-x'] if options.pop('trace', False) else [])
        mask = options.pop('umask', None)
        if options:
            raise TypeError('Unknown options: %s' % sorted(options))
        script = self.root / 'harness.sh'
        script.write_text(self.harness(), encoding='utf-8')
        return subprocess.Popen(
            shell + [str(script)] + list(arguments), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8',
            env=environment, cwd=str(self.root / 'home'), preexec_fn=as_a_terminal_starts_it(mask))

    def events(self):
        """The event lines without time and run name, in order."""
        return [' '.join(line.split()[2:]) for line in self.event_lines()]

    def event_lines(self):
        if not self.events_file.exists():
            return []
        return self.events_file.read_text().splitlines()

    def recorded(self, record):
        return record.read_text().splitlines() if record.exists() else []

    def panel_service_calls(self):
        """What was done to the panel's service, and when the panel was asked
        whether its administrator has the password, in order."""
        return [call for call in self.recorded(self.calls)
                if call == 'password-check' or (call.startswith('systemctl ') and call.endswith(' lscpd'))]

    def everything_written(self):
        """All text the run left in files, for searches for a secret. The one
        file that is there to hold the admin password is left out."""
        text = []
        for path in sorted(self.root.rglob('*')):
            if path.is_file() and not path.is_symlink() and path not in (self.root / 'harness.sh', self.stored_password):
                text.append(path.read_text(errors='replace'))
        return '\n'.join(text)
