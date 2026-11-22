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
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

TOP_LEVEL_START = '\nCheck_Usage "$@"\n'

# Functions of the script that run as they are.
REAL_FUNCTIONS = (
    'Check_Usage', 'Read_Admin_Password_File', 'Mask_Arguments', 'Use_Admin_Password_File',
    'Set_Default_Variables', 'Check_Root', 'Check_Server_IP',
    'Check_OS', 'Check_Virtualization', 'Check_Panel', 'Check_Process', 'Check_Provider',
    'Check_Argument', 'Argument_Mode', 'Interactive_Mode', 'Validate_Remote_MySQL',
    'Fail_Install', 'Install_Step', 'Pre_Install_Setup_Git_URL',
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
    *127.0.0.1:8090*) return "$QA_PANEL_EXIT" ;;
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
sleep() { :; }
timeout() { return 1; }
reboot() { note "reboot"; }
hostname() { printf '%s\n' 'qa.example.test'; }
dig() { if [ "$QA_DNS" = 1 ]; then printf '%s\n' '192.0.2.1'; fi; }
cyberpanel() {
  note "cyberpanel $*"
  if [ "$1" = createWebsite ]; then printf '%s\n' "$QA_CREATE_OUTPUT"; fi
  if [ "$1" = hostNameSSL ]; then printf '%s\n' "$QA_TLS_OUTPUT"; fi
  return 0
}
phase() {
  printf '%s\n' "$1" >> "$QA_PHASES"
  [ "$QA_FAIL_AT" = "$1" ]
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
  return 0
}
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


def script_parts(source=None):
    """The function definitions and the top level of the installer script."""
    if source is None:
        source = (ROOT / 'cyberpanel.sh').read_text()
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

    def os_release(self, content):
        (self.root / 'etc/os-release').write_text(content)

    def path(self, absolute):
        return self.root / absolute.lstrip('/')

    def relocate(self, text):
        return SYSTEM_PATH.sub(lambda match: '%s/%s/' % (self.root, match.group(1)), text)

    def harness(self):
        functions, top_level = script_parts()
        tweak = functions[functions.index('\nInstall_Step hostname_ssl\n'):]
        tweak = tweak[:tweak.index('\n}\n')]
        stubs = [COMMAND_STUBS]
        for name, failure in sorted(STUBBED_PHASES.items()):
            stubs.append('%s() { phase %s && { %s; }; return 0; }\n' % (name, name, failure))
        stubs.append('Post_Install_Tweak() {\nphase Post_Install_Tweak%s\n}\n' % tweak)
        return self.relocate(functions) + ''.join(stubs) + self.relocate(top_level)

    def run(self, *arguments, **options):
        """Run the installer with these arguments; returns the finished process."""
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
            'QA_ACTIVE_SERVICE': options.pop('active_service', ''),
            'QA_DNS': str(int(options.pop('dns', False))),
            'QA_CREATE_OUTPUT': options.pop('create_output', CLI_OK),
            'QA_TLS_OUTPUT': options.pop('tls_output', CLI_OK),
            'QA_FAIL_AT': options.pop('fail_at', ''),
            'QA_PYTHON_STEPS': options.pop('python_steps', DEFAULT_PYTHON_STEPS),
        }
        environment.update(options.pop('environment', {}))
        stdin = options.pop('stdin', '')
        # With trace=True every command that runs is written to the error output.
        shell = [shutil.which('bash')] + (['-x'] if options.pop('trace', False) else [])
        if options:
            raise TypeError('Unknown options: %s' % sorted(options))
        script = self.root / 'harness.sh'
        script.write_text(self.harness())
        return subprocess.run(
            shell + [str(script)] + list(arguments), input=stdin,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
            env=environment, cwd=str(self.root / 'home'), timeout=120)

    def events(self):
        """The event lines without time and run name, in order."""
        return [' '.join(line.split()[2:]) for line in self.event_lines()]

    def event_lines(self):
        if not self.events_file.exists():
            return []
        return self.events_file.read_text().splitlines()

    def recorded(self, record):
        return record.read_text().splitlines() if record.exists() else []

    def everything_written(self):
        """All text the run left in files, for searches for a secret."""
        text = []
        for path in sorted(self.root.rglob('*')):
            if path.is_file() and not path.is_symlink() and path.name != 'harness.sh':
                text.append(path.read_text(errors='replace'))
        return '\n'.join(text)
