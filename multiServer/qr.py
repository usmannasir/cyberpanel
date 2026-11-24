"""The QR code of a two-factor key, for an authenticator app to scan.

Multi-Server pages run no script of their own, so the code is drawn on the
server: the page receives the rows of dark squares and draws them as SVG
rectangles. Nothing is fetched from elsewhere, so it works on a server that
cannot reach the internet.
"""
from multiServer import qrcodegen


def runs(text):
    """(size, [(x, y, width), ...]): the dark squares of the QR code of `text`, one run per row segment."""
    code = qrcodegen.QrCode.encode_text(text, qrcodegen.QrCode.Ecc.MEDIUM)
    size = code.get_size()
    found = []
    for y in range(size):
        x = 0
        while x < size:
            if code.get_module(x, y):
                start = x
                while x < size and code.get_module(x, y):
                    x += 1
                found.append((start, y, x - start))
            else:
                x += 1
    return size, found
