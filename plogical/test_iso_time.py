"""parse_iso_datetime must match fromisoformat() on the fallback path used by Python 3.6."""
from datetime import datetime, timedelta, timezone
import unittest

from plogical.isoTime import parse_iso_datetime


class ParseIsoDatetimeTests(unittest.TestCase):
    SAMPLES = (
        datetime(2026, 10, 3, 10, 5, 7, tzinfo=timezone.utc),
        datetime(2026, 10, 3, 10, 5, 7, 123456, tzinfo=timezone.utc),
        datetime(2026, 10, 3, 10, 5, 7, tzinfo=timezone(timedelta(hours=5, minutes=30))),
        datetime(2026, 10, 3, 10, 5, 7, tzinfo=timezone(-timedelta(hours=4))),
        datetime(2026, 10, 3, 10, 5, 7),
        datetime(2026, 10, 3, 10, 5, 7, 42),
    )

    def test_fallback_round_trips_isoformat_output(self):
        for sample in self.SAMPLES:
            for sep in ('T', ' '):
                with self.subTest(value=sample.isoformat(sep)):
                    parsed = parse_iso_datetime(sample.isoformat(sep), _native=False)
                    self.assertEqual(parsed, sample)
                    self.assertEqual(parsed.utcoffset(), sample.utcoffset())

    def test_fallback_parses_date_only(self):
        self.assertEqual(parse_iso_datetime('2026-10-03', _native=False), datetime(2026, 10, 3))

    def test_fallback_raises_like_fromisoformat(self):
        with self.assertRaises(ValueError):
            parse_iso_datetime('not a date', _native=False)
        with self.assertRaises(TypeError):
            parse_iso_datetime(None, _native=False)

    def test_native_path_matches_fallback(self):
        for sample in self.SAMPLES:
            text = sample.isoformat()
            self.assertEqual(parse_iso_datetime(text), parse_iso_datetime(text, _native=False))


if __name__ == '__main__':
    unittest.main()
