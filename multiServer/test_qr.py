"""The QR code of a two-factor key is drawn on the server, as rows of dark squares."""
import random
import string
import unittest

from multiServer import qr, qrcodegen

KEY_URI = ('otpauth://totp/CyberPanel:admin%20%2874.81.48.19%29?secret=JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP'
           '&issuer=CyberPanel')


class QrTests(unittest.TestCase):
    def modules(self, text):
        code = qrcodegen.QrCode.encode_text(text, qrcodegen.QrCode.Ecc.MEDIUM)
        size = code.get_size()
        return size, {(x, y) for y in range(size) for x in range(size) if code.get_module(x, y)}

    def drawn(self, runs):
        squares = set()
        for x, y, width in runs:
            self.assertGreater(width, 0)
            for offset in range(width):
                self.assertNotIn((x + offset, y), squares)  # no square is drawn twice
                squares.add((x + offset, y))
        return squares

    def test_the_runs_draw_exactly_the_dark_modules(self):
        rng = random.Random(3)
        texts = [KEY_URI, ''] + [''.join(rng.choice(string.printable) for _ in range(rng.randint(1, 200)))
                                 for _ in range(50)]
        for text in texts:
            with self.subTest(text=text[:20]):
                size, dark = self.modules(text)
                drawn_size, runs = qr.runs(text)
                self.assertEqual(size, drawn_size)
                self.assertEqual(dark, self.drawn(runs))
                # A run never crosses a row and never leaves the symbol.
                for x, y, width in runs:
                    self.assertTrue(0 <= y < size and 0 <= x and x + width <= size)

    def test_a_key_fits_a_small_symbol(self):
        size, runs = qr.runs(KEY_URI)
        self.assertLessEqual(size, 49)  # version 8 or below: readable on a phone at 200 pixels
        self.assertLess(len(runs), size * size // 2)

    def test_the_symbol_starts_with_the_three_finder_patterns(self):
        size, runs = qr.runs(KEY_URI)
        dark = self.drawn(runs)
        for left, top in ((0, 0), (size - 7, 0), (0, size - 7)):
            for offset in range(7):
                for x, y in ((left + offset, top), (left + offset, top + 6), (left, top + offset), (left + 6, top + offset)):
                    self.assertIn((x, y), dark)


if __name__ == '__main__':
    unittest.main()
