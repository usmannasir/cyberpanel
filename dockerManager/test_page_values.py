"""Values from Docker images and from page addresses stay text when the container pages are built."""
import re
import unittest
from pathlib import Path

from dockerManager.names import exposed_ports, valid_container_name, valid_image_name, valid_image_tag
from dockerManager.templatetags.docker_values import ngstring

HERE = Path(__file__).resolve().parent
TEMPLATES = ('templates/dockerManager/runContainer.html', 'templates/dockerManager/viewContainer.html')
## Values the panel computes itself and writes as numbers or true/false.
COMPUTED = {'cpuUsage', 'memoryUsage', 'memoryLimit', 'startOnReboot', 'forloop.counter0', 'port'}

HOSTILE = (
    "x');alert(1);//", '";alert(1);//', "\\'); alert(1); //", '</script><script>alert(1)</script>',
    "{$ constructor.constructor('alert(1)')() $}", '{{7*7}}', '&#39;);alert(1);//', "&apos;", 'a\nb', 'a\rb',
    'a\u2028b', 'a\u2029b', '`${x}`', 'line\\', "it's", 'plain-value_1.2', '', 'PATH=/usr/bin:/bin',
)


def decode(text):
    return re.sub(r'\\u([0-9A-Fa-f]{4})', lambda match: chr(int(match.group(1), 16)), text)


class FilterTests(unittest.TestCase):
    def test_nothing_that_ends_a_string_or_starts_an_expression_is_left(self):
        for value in HOSTILE:
            with self.subTest(value=value):
                written = str(ngstring(value))
                self.assertIsNone(re.search('[\'"<>&{}$`\n\r\u2028\u2029]', written), written)
                self.assertIsNone(re.search(r'\\(?!u[0-9A-F]{4})', written), written)

    def test_the_browser_reads_back_the_same_text(self):
        for value in HOSTILE:
            with self.subTest(value=value):
                self.assertEqual(value, decode(str(ngstring(value))))

    def test_ordinary_values_are_written_as_they_are(self):
        for value in ('nginx', 'my_container.1', 'latest', '8080', 'tcp', 'Yes'):
            self.assertEqual(value, str(ngstring(value)))

    def test_values_that_are_not_text(self):
        self.assertEqual('8080', str(ngstring(8080)))
        self.assertEqual('None', str(ngstring(None)))


class TemplateTests(unittest.TestCase):
    def test_every_value_inside_an_angular_expression_is_filtered(self):
        for name in TEMPLATES:
            text = (HERE / name).read_text(encoding='utf-8')
            self.assertIn('{% load docker_values %}', text)
            attributes = re.findall(r'\bng-[a-z-]+="([^"]*\{\{[^"]*)"', text)
            self.assertTrue(attributes, name)
            for attribute in attributes:
                for expression in re.findall(r'\{\{\s*(.*?)\s*\}\}', attribute):
                    with self.subTest(template=name, expression=expression):
                        if expression.endswith('|ngstring'):
                            continue
                        self.assertIn(expression, COMPUTED)

    def test_quoted_values_are_the_filtered_ones(self):
        for name in TEMPLATES:
            text = (HERE / name).read_text(encoding='utf-8')
            for attribute in re.findall(r'\bng-[a-z-]+="([^"]*\{\{[^"]*)"', text):
                for expression in re.findall(r"'\{\{\s*(.*?)\s*\}\}'", attribute):
                    with self.subTest(template=name, expression=expression):
                        if expression == 'port':
                            continue
                        self.assertTrue(expression.endswith('|ngstring'))


class NameTests(unittest.TestCase):
    def test_container_names(self):
        for name in ('web', 'my_container.1', 'a', 'n8n-n8n-1', 'A9'):
            self.assertTrue(valid_container_name(name), name)
        for name in ('', '-web', '.web', "web'", 'web/x', 'web x', "a');alert(1)//", '{$x$}', 'a\nb', None, 7,
                     ['web'], 'x' * 256):
            self.assertFalse(valid_container_name(name), name)

    def test_image_names_and_tags(self):
        for image in ('nginx', 'library/nginx', 'docker.n8n.io/n8nio/n8n', 'localhost:5000/team/app',
                      'cyberpanel/openlitespeed'):
            self.assertTrue(valid_image_name(image), image)
        for image in ('', "nginx'", 'nginx:latest', '/nginx', 'nginx/', 'a b', "x');alert(1)//", '{$x$}', None, 7,
                      'a//b', 'nginx\n'):
            self.assertFalse(valid_image_name(image), image)
        for tag in ('latest', '16-alpine', 'v1.2.3', '_x'):
            self.assertTrue(valid_image_tag(tag), tag)
        for tag in ('', '-x', '.x', "latest'", 'a b', 'latest (official)', None, 7, 'x' * 129, 'latest\n'):
            self.assertFalse(valid_image_tag(tag), tag)

    def test_exposed_ports_are_numbers_with_a_known_protocol(self):
        config = {'ExposedPorts': {'80/tcp': {}, '53/udp': {}, '8080': {}, "1];alert(1);//tcp": {},
                                   '443/x"y': {}, '0/tcp': {}, '70000/tcp': {}, '/tcp': {}}}
        self.assertEqual({'80': 'tcp', '53': 'udp', '8080': 'tcp'}, exposed_ports(config))
        for config in ({}, {'ExposedPorts': None}, {'ExposedPorts': {}}, None):
            self.assertEqual({}, exposed_ports(config))


class HandlerTests(unittest.TestCase):
    def body(self, name):
        source = (HERE / 'container.py').read_text(encoding='utf-8')
        start = source.index('    def %s(' % name)
        return source[start:source.index('\n    def ', start + 1)]

    def test_the_create_page_checks_image_and_tag_before_it_uses_them(self):
        body = self.body('createContainer')
        check = body.index('if not valid_image_name(image) or not valid_image_tag(tag):')
        self.assertLess(check, body.index('inspect_image'))
        self.assertLess(check, body.index('name = image'))
        self.assertIn("portConfig = exposed_ports(inspectImage['Config'])", body)

    def test_the_container_page_checks_the_name_before_it_looks_the_container_up(self):
        body = self.body('loadContainerHome')
        check = body.index('if not valid_container_name(name):')
        self.assertLess(check, body.index('client.containers.get(name)'))
        self.assertLess(check, body.index('checkContainerOwnership'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
