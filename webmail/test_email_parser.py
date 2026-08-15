import unittest
from urllib.parse import parse_qs, urlparse

from webmail.services.email_parser import EmailParser
from webmail.services.imap_client import IMAPClient


class MimeDecodingTests(unittest.TestCase):

    def test_unknown_header_charset_uses_safe_fallback(self):
        value = '=?unknown-8bit?Q?Invoice_=E9?='

        self.assertEqual(EmailParser._decode_header_value(value), 'Invoice �')
        self.assertEqual(IMAPClient._decode_header_value(None, value), 'Invoice �')

    def test_unknown_body_charset_does_not_break_message_view(self):
        message = (
            b'Subject: =?unknown-8bit?Q?Invoice_=E9?=\r\n'
            b'Content-Type: text/plain; charset="unknown-8bit"\r\n'
            b'Content-Transfer-Encoding: 8bit\r\n'
            b'\r\n'
            b'Payment received: \xe9\r\n'
        )

        parsed = EmailParser.parse_message(message)

        self.assertEqual(parsed['subject'], 'Invoice �')
        self.assertEqual(parsed['body_text'], 'Payment received: �\r\n')

    def test_valid_declared_charset_remains_supported(self):
        message = (
            b'Content-Type: text/plain; charset="iso-8859-1"\r\n'
            b'Content-Transfer-Encoding: 8bit\r\n'
            b'\r\n'
            b'Payment received: \xe9\r\n'
        )

        self.assertEqual(
            EmailParser.parse_message(message)['body_text'],
            'Payment received: é\r\n',
        )


class HtmlSanitizationTests(unittest.TestCase):

    def test_dangerous_elements_and_event_handlers_are_removed(self):
        sanitized = EmailParser.sanitize_html(
            '<p onclick="run()">Hello</p>'
            '<script>run()</script>'
            '<svg><foreignObject><img src=x onerror="run()"></foreignObject></svg>'
            '<math><mtext><img src=x onerror="run()"></mtext></math>'
        )

        self.assertIn('<p>Hello</p>', sanitized)
        self.assertNotIn('onclick', sanitized.lower())
        self.assertNotIn('onerror', sanitized.lower())
        self.assertNotIn('<script', sanitized.lower())
        self.assertNotIn('<svg', sanitized.lower())
        self.assertNotIn('<math', sanitized.lower())

    def test_encoded_active_url_and_css_are_removed(self):
        sanitized = EmailParser.sanitize_html(
            '<a href="j&#x61;vascript:run()" style="background:url(javascript:run())">Open</a>'
        )

        self.assertNotIn('javascript:', sanitized.lower())
        self.assertNotIn('style=', sanitized.lower())
        self.assertIn('href=""', sanitized)

    def test_external_images_use_the_authenticated_proxy(self):
        source = 'https://images.example.net/news/banner.png?campaign=1'
        sanitized = EmailParser.sanitize_html(
            '<img src="%s" alt="News">' % source
        )

        parsed = urlparse(sanitized.split('src="', 1)[1].split('"', 1)[0])
        self.assertEqual('/webmail/api/proxyImage', parsed.path)
        self.assertIn('url', parse_qs(parsed.query))
        self.assertNotIn(source, sanitized)

    def test_protocol_relative_images_are_proxied_and_relative_panel_urls_are_blocked(self):
        sanitized = EmailParser.sanitize_html(
            '<img src="//images.example.net/banner.png">'
            '<img src="/websites/saveSSHAccessChanges">'
        )

        self.assertIn('/webmail/api/proxyImage?url=', sanitized)
        self.assertIn('src=""', sanitized)
        self.assertNotIn('src="//images.example.net', sanitized)
        self.assertNotIn('src="/websites/', sanitized)

    def test_links_opened_in_new_tab_are_isolated(self):
        sanitized = EmailParser.sanitize_html(
            '<a href="https://example.net" target="_blank">Open</a>'
        )

        self.assertIn('target="_blank"', sanitized)
        self.assertIn('rel="noopener noreferrer"', sanitized)

    def test_malformed_dangerous_markup_does_not_survive_reparsing(self):
        sanitized = EmailParser.sanitize_html(
            '<noscript><p title="</noscript><img src=x onerror=run()>">Text</p>'
        )
        reparsed = EmailParser.sanitize_html(sanitized)

        self.assertNotIn('onerror', reparsed.lower())
        self.assertNotIn('<noscript', reparsed.lower())
