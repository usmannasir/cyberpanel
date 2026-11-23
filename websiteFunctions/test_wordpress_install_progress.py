"""A finished WordPress job shows 100% on the pages that show its progress, a running one its own number."""
import ast
import json
from pathlib import Path
import re
from types import SimpleNamespace as NS
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = (ROOT / 'websiteFunctions/static/websiteFunctions/websiteFunctions.js',
           ROOT / 'static/websiteFunctions/websiteFunctions.js')
TEMPLATES = ROOT / 'websiteFunctions/templates/websiteFunctions'


def method(path, name):
    return next(node for node in ast.walk(ast.parse(path.read_text()))
                if isinstance(node, ast.FunctionDef) and node.name == name)


def controller(path, name):
    """The source of the controller of this name that the page uses: the last one registered."""
    text = path.read_text()
    start = [match.start() for match in re.finditer(r"app\.controller\('%s'" % name, text)][-1]
    end = text.find('app.controller(', start + 1)
    return text[start:end if end > -1 else len(text)]


class StatusReaderProgressTests(unittest.TestCase):
    def setUp(self):
        self.removed = mock.Mock()
        namespace = {'ACLManager': NS(CheckStatusFilleLoc=mock.Mock(return_value=True)),
                     'subprocess': NS(call=self.removed), 'shlex': __import__('shlex'), 'json': json,
                     'HttpResponse': json.loads}
        node = method(ROOT / 'websiteFunctions/website.py', 'installWordpressStatus')
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'website.py', 'exec'), namespace)
        self.read = namespace['installWordpressStatus']

    def status(self, content):
        with mock.patch('plogical.statusUtilities.read_status_file', return_value=content):
            return self.read(None, 1, {'statusFile': '/home/cyberpanel/1234'})

    def test_the_last_status_of_every_wordpress_job_reads_as_finished_at_100(self):
        installer = (ROOT / 'plogical/applicationInstaller.py').read_text()
        staging = (ROOT / 'websiteFunctions/StagingSetup.py').read_text()
        finals = (('WordPress installed..,[200]', installer),      # WordPress Manager deployment
                  ('Successfully Installed. [200]', installer),     # one-click install on a website
                  ('Staging site created successfully!,100[200]', installer),
                  ('Completed,[200]', staging))                     # Clone/Staging of a website
        for final, source in finals:
            self.assertIn(final, source)
            result = self.status('Installing WordPress....,50\n' + final + '\n')
            self.assertEqual((1, 1, '100'), (result['abort'], result['installStatus'],
                                             result['installationProgress']), final)

    def test_a_running_job_shows_the_number_of_its_last_line(self):
        for line, progress in (('Creating Website...,10', '10'), ('Installing WordPress....,30', '30'),
                               ('WordPress installed..,70', '70')):
            result = self.status(line)
            self.assertEqual((0, progress, line.split(',')[0]),
                             (result['abort'], result['installationProgress'], result['currentStatus']))

    def test_a_failed_job_reads_as_failed_at_0(self):
        result = self.status('Failed to install WordPress: error: the download failed. [404]')
        self.assertEqual((1, 0, '0'), (result['abort'], result['installStatus'], result['installationProgress']))
        self.removed.assert_not_called()


class ProgressLabelTests(unittest.TestCase):
    def test_no_progress_bar_shows_a_fixed_percentage(self):
        checked = 0
        for template in sorted(TEMPLATES.glob('*.html')):
            text = template.read_text()
            for match in re.finditer(r'<div id="installProgress[^"]*"[^>]*>(.*?)</div>', text, re.S):
                for span in re.finditer(r'<span(?![^>]*sr-only)[^>]*>([^<]*)</span>', match.group(1)):
                    checked += 1
                    self.assertNotRegex(span.group(1), r'^\s*\d+%\s*$', template.name)
                    self.assertIn('installPercentage', span.group(1), template.name)
        self.assertGreaterEqual(checked, 2)

    def test_deployment_pages_bind_the_label_to_the_reported_progress(self):
        for name in ('WPCreate.html', 'CreateDockerSite.html'):
            text = (TEMPLATES / name).read_text()
            self.assertIn('<span>{$ installPercentage || 0 $}%</span>', text)
            self.assertNotIn("websiteFunctions.js' %}?v={{ CP_VERSION }}-20260909\"", text)

    def test_the_scripts_set_100_when_finished_and_0_when_going_back(self):
        for name in ('createWordpress', 'createDockerSite'):
            copies = [controller(path, name) for path in SCRIPTS]
            # Both copies of the script hold the same controller.
            self.assertEqual(copies[0], copies[1], name)
            source = copies[0]
            self.assertRegex(source, r'installStatus === 1\) \{[^}]*\$scope\.installPercentage = "100";')
            back = source[source.index('$scope.goBack = function'):]
            back = back[:back.index('};')]
            self.assertIn('$scope.installPercentage = "0";', back)
            self.assertIn('$scope.installPercentage = response.data.installationProgress;', source)


if __name__ == '__main__':
    unittest.main()
