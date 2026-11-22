"""Every page loads the script that defines the Angular controllers it names.

A page whose controller is not defined shows its raw `{{ }}` text and every
label at once, and none of its buttons work. The base template loads a fixed
list of module scripts; a page of any other module has to load its own.

The check reads the templates as text. It follows `extends`, block overrides
(with and without `block.super`) and `include`, collects the scripts the
finished page loads, and looks in those for the controllers the page names.
"""
import re
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TAG = re.compile(r'{%-?\s*(block|endblock|extends|include)\b([^%]*?)-?%}')
COMMENT = re.compile(r'<!--.*?-->|{#.*?#}|{%-?\s*comment\b.*?{%-?\s*endcomment\s*-?%}', re.S)
SCRIPT = re.compile(r'<script\b([^>]*)>(.*?)</script\s*>', re.S | re.I)
SOURCE = re.compile(r'''\bsrc\s*=\s*(?:"([^"]*)"|'([^']*)')''', re.I)
STATIC = re.compile(r'''{%\s*static\s+['"]([^'"]+)['"]\s*%}''')
NAMED = re.compile(r'''\b(?:data-)?ng-controller\s*=\s*(?:"([^"]*)"|'([^']*)')''')
DEFINED = re.compile(r'''\.controller\(\s*['"]([\w$]+)['"]''')
SUPER = re.compile(r'{{\s*block\.super\s*}}')
QUOTED = re.compile(r'''['"]([^'"]+)['"]''')

# Pages that name a controller no loaded script defines, and why each is left as it is.
# An entry that stops being true fails the test, so the list cannot go stale.
KNOWN = {
    ('WebTerminal/WebTerminal.html', 'webTerminal'):
        'the page cannot be opened: the URLs of its app are not included in CyberCP/urls.py',
    ('websiteFunctions/DockerSiteHome_fixed.html', 'ListDockersitecontainer'):
        'no view renders this template',
    ('websiteFunctions/installMagento.html', 'installMagentoCTRL'):
        'no script in the panel defines this controller',
}


class Templates:
    """The templates and static files below one folder of Django apps."""

    def __init__(self, root):
        self.root = Path(root)
        self.files = {}
        for folder in sorted(self.root.glob('*/templates')) + [self.root / 'templates']:
            if folder.is_dir():
                for path in sorted(folder.rglob('*.html')):
                    self.files.setdefault(path.relative_to(folder).as_posix(), path)
        self.scripts = {}
        self.parsed = {}

    def parse(self, name):
        """(the template it extends, its content as text, blocks and includes)."""
        if name not in self.parsed:
            self.parsed[name] = self.read(name)
        return self.parsed[name]

    def read(self, name):
        text = COMMENT.sub('', self.files[name].read_text(errors='replace'))
        extends, top = None, []
        open_blocks = [top]
        position = 0
        for tag in TAG.finditer(text):
            open_blocks[-1].append(text[position:tag.start()])
            position = tag.end()
            kind, rest = tag.group(1), tag.group(2)
            quoted = QUOTED.search(rest)
            if kind == 'extends':
                extends = quoted.group(1) if quoted else None
            elif kind == 'include':
                open_blocks[-1].append(('include', quoted.group(1) if quoted else None))
            elif kind == 'block':
                block = ('block', rest.split()[0], [])
                open_blocks[-1].append(block)
                open_blocks.append(block[2])
            elif len(open_blocks) > 1:
                open_blocks.pop()
        open_blocks[-1].append(text[position:])
        return extends, top

    def blocks(self, content, found):
        for part in content:
            if isinstance(part, tuple) and part[0] == 'block':
                found[part[1]] = part[2]
                self.blocks(part[2], found)
        return found

    def text(self, content, overrides, seen):
        out = []
        for part in content:
            if isinstance(part, str):
                out.append(part)
            elif part[0] == 'include':
                if part[1] in self.files and part[1] not in seen:
                    out.append(self.page(part[1], seen))
            else:
                inherited = self.text(part[2], overrides, seen)
                # Each override replaces what it inherits, unless it asks for it.
                for override in overrides.get(part[1], ()):
                    inherited = SUPER.sub(lambda match: inherited, self.text(override, overrides, seen))
                out.append(inherited)
        return ''.join(out)

    def page(self, name, seen=()):
        """The page a template makes, as far as its text tells: its own text with every parent's around it."""
        seen = tuple(seen) + (name,)
        overrides = {}
        while True:
            extends, content = self.parse(name)
            if extends not in self.files or extends in seen:
                return self.text(content, overrides, seen)
            for block, body in self.blocks(content, {}).items():
                # The nearest parent's override is applied first, the page's own last.
                overrides.setdefault(block, []).insert(0, body)
            name = extends
            seen += (name,)

    def is_page(self, name):
        text = self.files[name].read_text(errors='replace')
        return bool(re.search(r'{%-?\s*extends\b', text)) or '<html' in text.lower()

    def script(self, path):
        path = path.split('?')[0].split('#')[0]
        if path not in self.scripts:
            # An app's own static folder is what gets collected and served.
            found = sorted(self.root.glob('*/static/' + path)) + [self.root / 'static' / path]
            found = [candidate for candidate in found if candidate.is_file()]
            self.scripts[path] = found[0].read_text(errors='replace') if found else ''
        return self.scripts[path]

    def defined(self, page):
        """The controllers defined by the scripts a page loads or carries."""
        names = set()
        for attributes, body in SCRIPT.findall(page):
            source = SOURCE.search(attributes)
            if not source:
                names.update(DEFINED.findall(body))
                continue
            value = source.group(1) or source.group(2) or ''
            static = STATIC.search(value)
            if static:
                names.update(DEFINED.findall(self.script(static.group(1))))
            elif value.startswith('/static/'):
                names.update(DEFINED.findall(self.script(value[len('/static/'):])))
        return names

    def named(self, page):
        """The controllers a page names. A name the template computes is not one the text can check."""
        names = set()
        for first, second in NAMED.findall(page):
            name = (first or second).split(' as ')[0].strip()
            if re.match(r'^[\w$]+$', name):
                names.add(name)
        return names

    def undefined(self):
        """(template, controller) for every page that names a controller none of its scripts defines."""
        missing = set()
        for name in sorted(self.files):
            if self.is_page(name):
                page = self.page(name)
                missing.update((name, controller) for controller in self.named(page) - self.defined(page))
        return missing


class PanelTemplateTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.templates = Templates(ROOT)
        cls.undefined = cls.templates.undefined()

    def test_every_page_loads_the_script_of_each_controller_it_names(self):
        unexpected = sorted(self.undefined - set(KNOWN))
        self.assertEqual([], unexpected,
                         'These pages name a controller that no script they load defines. Load the script in the '
                         'page, for example in a `module_scripts` block that keeps `{{ block.super }}`.')

    def test_known_exceptions_are_still_exceptions(self):
        self.assertEqual([], sorted(set(KNOWN) - self.undefined))

    def test_check_looks_at_the_panel_s_pages(self):
        pages = [name for name in self.templates.files if self.templates.is_page(name)]
        self.assertGreater(len(pages), 150)
        # The base template's own list of module scripts is seen through `extends`.
        page = self.templates.page('websiteFunctions/listWebsites.html')
        self.assertIn('listWebsites', self.templates.defined(page) & self.templates.named(page))

    def test_backup_pages_load_the_backup_controllers(self):
        for name, controller in (('IncBackups/CreateV2Backup.html', 'CreateV2Backup'),
                                 ('IncBackups/RestoreV2Backup.html', 'restorev2backupoage'),
                                 ('IncBackups/ScheduleV2Backup.html', 'ScheduleV2Backup'),
                                 ('IncBackups/DeleteV2repo.html', 'DeleteBackuprepo'),
                                 ('IncBackups/ConfigureV2Backup.html', 'ConfigureV2Backup'),
                                 ('IncBackups/backupSchedule.html', 'scheduleBackupInc'),
                                 ('IncBackups/restoreRemoteBackups.html', 'restoreRemoteBackupsInc'),
                                 ('IncBackups/createBackup.html', 'createIncrementalBackups'),
                                 ('IncBackups/incrementalDestinations.html', 'incrementalDestinations')):
            page = self.templates.page(name)
            self.assertTrue("{% static 'IncBackups/IncBackups.js' %}" in page, name)
            self.assertEqual({controller}, self.templates.named(page) - self.templates.named(
                self.templates.page('baseTemplate/index.html')), name)
            self.assertIn(controller, self.templates.defined(page), name)


class CheckTests(unittest.TestCase):
    """The check itself, on a small panel made for it."""

    BASE = ('<html><head><script src="{% static \'base/app.js\' %}"></script></head><body ng-controller="shell">'
            '{% block content %}{% endblock %}'
            '{% block module_scripts %}<script defer src="{% static \'sites/sites.js\' %}?v=1"></script>{% endblock %}'
            '</body></html>')

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='controller-scripts-test-'))
        self.addCleanup(shutil.rmtree, str(self.root), True)
        self.write('base/templates/base/index.html', self.BASE)
        self.write('base/static/base/app.js', "app.controller('shell', function () {});")
        self.write('sites/static/sites/sites.js', "app.controller('listSites', function () {});")
        self.write('backups/static/backups/backups.js', 'app.controller("createBackup", function () {});')

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def undefined(self, **pages):
        for name, text in pages.items():
            self.write('backups/templates/backups/%s.html' % name, text)
        return sorted(Templates(self.root).undefined())

    def test_page_of_a_module_the_base_loads_is_complete(self):
        self.assertEqual([], self.undefined(
            sites='{% extends "base/index.html" %}{% block content %}<div ng-controller="listSites"></div>'
                  '{% endblock %}'))

    def test_page_that_does_not_load_its_module_is_found(self):
        self.assertEqual([('backups/create.html', 'createBackup')], self.undefined(
            create='{% extends "base/index.html" %}{% block content %}<div ng-controller="createBackup"></div>'
                   '{% endblock %}'))

    def test_page_that_adds_its_module_to_the_base_s_is_complete(self):
        self.assertEqual([], self.undefined(
            create='{% extends "base/index.html" %}{% block content %}<div ng-controller="createBackup">'
                   '<p ng-controller="listSites"></p></div>{% endblock %}'
                   '{% block module_scripts %}{{ block.super }}'
                   '<script defer src="{% static \'backups/backups.js\' %}?v=2"></script>{% endblock %}'))

    def test_page_that_replaces_the_base_s_modules_loses_them(self):
        self.assertEqual([('backups/create.html', 'listSites')], self.undefined(
            create='{% extends "base/index.html" %}{% block content %}<div ng-controller="createBackup">'
                   '<p ng-controller="listSites"></p></div>{% endblock %}'
                   '{% block module_scripts %}<script src="/static/backups/backups.js"></script>{% endblock %}'))

    def test_controller_defined_in_the_page_or_in_an_included_part_counts(self):
        self.write('backups/templates/backups/part.html',
                   '<script src="{% static \'backups/backups.js\' %}"></script>')
        self.assertEqual([], self.undefined(
            inline='{% extends "base/index.html" %}{% block content %}<div ng-controller="local as vm"></div>'
                   '<script>app.controller(\'local\', function () {});</script>{% endblock %}',
            included='{% extends "base/index.html" %}{% block content %}<div data-ng-controller="createBackup"></div>'
                     '{% include "backups/part.html" %}{% endblock %}'))

    def test_script_in_a_comment_is_not_loaded(self):
        self.assertEqual([('backups/create.html', 'createBackup')], self.undefined(
            create='{% extends "base/index.html" %}{% block content %}<div ng-controller="createBackup"></div>'
                   '<!-- <script src="{% static \'backups/backups.js\' %}"></script> -->'
                   '{% comment %}<script src="{% static \'backups/backups.js\' %}"></script>{% endcomment %}'
                   '{% endblock %}'))

    def test_parts_and_a_grandchild_page_are_read_through_their_parents(self):
        self.write('backups/templates/backups/part.html', '<div ng-controller="createBackup"></div>')
        self.assertEqual([('backups/child.html', 'createBackup')], self.undefined(
            middle='{% extends "base/index.html" %}{% block module_scripts %}{{ block.super }}'
                   '<script src="{% static \'backups/backups.js\' %}"></script>{% endblock %}',
            grandchild='{% extends "backups/middle.html" %}{% block content %}{% include "backups/part.html" %}'
                       '{% endblock %}',
            child='{% extends "base/index.html" %}{% block content %}{% include "backups/part.html" %}'
                  '{% endblock %}'))


if __name__ == '__main__':
    unittest.main()
