# -*- coding: utf-8 -*-
from django.test import TestCase
from panelAccess.apps import read_panel_csrf_origins, get_panel_csrf_origins_file
import os
import tempfile


class PanelAccessOriginsTest(TestCase):
    def test_read_empty_missing_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'nonexistent.conf')
            orig = os.environ.get('PANEL_CSRF_ORIGINS_FILE')
            try:
                os.environ['PANEL_CSRF_ORIGINS_FILE'] = path
                self.assertEqual(read_panel_csrf_origins(), [])
            finally:
                if orig is not None:
                    os.environ['PANEL_CSRF_ORIGINS_FILE'] = orig
                else:
                    os.environ.pop('PANEL_CSRF_ORIGINS_FILE', None)

    def test_read_origins_skips_comments_and_blanks(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write('# comment\n\nhttps://a.com\n  \nhttp://b.com\n')
            path = f.name
        try:
            orig = os.environ.get('PANEL_CSRF_ORIGINS_FILE')
            try:
                os.environ['PANEL_CSRF_ORIGINS_FILE'] = path
                self.assertEqual(read_panel_csrf_origins(), ['https://a.com', 'http://b.com'])
            finally:
                if orig is not None:
                    os.environ['PANEL_CSRF_ORIGINS_FILE'] = orig
                else:
                    os.environ.pop('PANEL_CSRF_ORIGINS_FILE', None)
        finally:
            os.unlink(path)
