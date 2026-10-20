"""Embedded videos identify the panel origin without leaking page paths (#1979)."""
from html.parser import HTMLParser
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class Iframes(HTMLParser):
    def __init__(self):
        super().__init__()
        self.youtube = []
    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if tag == 'iframe' and data.get('src', '').startswith('https://www.youtube.com/embed/'):
            self.youtube.append(data)

class VideoEmbedPolicyTests(unittest.TestCase):
    def test_youtube_frames_identify_origin_without_disclosing_page_url(self):
        frames = []
        for directory in ('websiteFunctions', 'manageSSL', 'IncBackups'):
            for path in (ROOT / directory / 'templates').rglob('*.html'):
                parser = Iframes()
                parser.feed(path.read_text())
                for frame in parser.youtube:
                    with self.subTest(template=str(path.relative_to(ROOT))):
                        self.assertEqual(frame.get('referrerpolicy'), 'strict-origin-when-cross-origin')
                    frames.append(frame)
        self.assertGreaterEqual(len(frames), 8)

if __name__ == '__main__':
    unittest.main()
