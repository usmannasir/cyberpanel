"""Standalone bandwidth worker regressions using real temporary log/metadata files."""
import importlib.util
import json
from pathlib import Path
import resource
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


def load_worker():
    spec = importlib.util.spec_from_file_location('bandwidth_worker_test',
                                                Path(__file__).with_name('findBWUsage.py'))
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {'validators': SimpleNamespace(domain=lambda name: '.' in name)}):
        spec.loader.exec_module(module)
    return module


worker = load_worker()
BW = worker.findBWUsage


def record(size, request='GET / HTTP/1.1'):
    return f'127.0.0.1 - - [19/Sep/2026:10:00:00 +0000] "{request}" 200 {size} "-" "test agent"\n'


class BandwidthTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.home = Path(self.directory.name)
        self.domain = 'example.test'
        self.log = self.home / self.domain / 'logs' / (self.domain + '.access_log')
        self.log.parent.mkdir(parents=True)
        (self.home / 'cyberpanel').mkdir()
        self.meta = self.home / 'cyberpanel' / (self.domain + '.bwmeta')
        for patcher in (patch.object(BW, 'HOME_DIRECTORY', str(self.home)),
                        patch.object(worker.logging.CyberCPLogFileWriter, 'writeToFile')):
            patcher.start()
            self.addCleanup(patcher.stop)

    def calculate(self):
        return BW.calculateBandwidth(self.domain)

    def totals(self):
        return [int(value) for value in self.meta.read_text().splitlines()[:2]]

    def test_parser_handles_configured_format_and_ignores_trailing_numbers(self):
        for request in ('GET / HTTP/1.1', '-', '', r'GET /a\"b HTTP/1.1'):
            with self.subTest(request=request):
                self.assertEqual(BW.parse_last_digits(record(123, request)), 123)
        self.assertEqual(BW.parse_last_digits(record('-')), 0)
        self.assertEqual(BW.parse_last_digits(record(0)), 0)
        self.assertEqual(BW.parse_last_digits(record(12).replace(' - - ', '\t-  -\t')), 12)

    def test_parser_rejects_invalid_and_negative_sizes(self):
        for line in ('', 'garbage 123', None, record(-10), record('bad'), record('1.5')):
            with self.subTest(line=line):
                self.assertIsNone(BW.parse_last_digits(line))

    def test_incremental_runs_count_every_physical_line_once(self):
        self.log.write_text(record(10) + '\nshort\n' + record('-') + record(20))
        self.assertEqual(self.calculate(), 1)
        self.assertEqual(self.totals(), [30, 5])
        self.assertEqual(self.calculate(), 1)
        self.assertEqual(self.totals(), [30, 5])
        with self.log.open('a') as stream:
            stream.write(record(7))
        self.assertEqual(self.calculate(), 1)
        self.assertEqual(self.totals(), [37, 6])
        self.assertEqual(self.meta.stat().st_mode & 0o777, 0o600)

    def test_legacy_metadata_migrates_without_recounting(self):
        self.log.write_text(record(10) + record(20))
        self.meta.write_text('10\n1\n')
        self.assertEqual(self.calculate(), 1)
        self.assertEqual(self.totals(), [30, 2])
        self.assertEqual(json.loads(self.meta.read_text().splitlines()[2])['offset'], self.log.stat().st_size)

    def test_legacy_truncated_log_preserves_monthly_total(self):
        self.log.write_text(record(5))
        self.meta.write_text('100\n10\n')
        self.assertEqual(self.calculate(), 1)
        self.assertEqual(self.totals(), [105, 1])

    def test_replaced_log_with_more_lines_preserves_total(self):
        self.log.write_text(record(10))
        self.calculate()
        self.log.rename(self.log.with_suffix('.old'))
        self.log.write_text(record(4) + record(5))
        self.assertEqual(self.calculate(), 1)
        self.assertEqual(self.totals(), [19, 2])

    def test_copy_truncation_and_regrowth_are_detected(self):
        self.log.write_text(record(10))
        self.calculate()
        self.log.write_text(record(40) + record(50))
        self.assertEqual(self.calculate(), 1)
        self.assertEqual(self.totals(), [100, 2])

    def test_empty_rotated_log_does_not_reset_total(self):
        self.log.write_text(record(10))
        self.calculate()
        self.log.write_text('')
        self.assertEqual(self.calculate(), 1)
        self.assertEqual(self.totals(), [10, 0])
        self.log.write_text(record(5))
        self.calculate()
        self.assertEqual(self.totals(), [15, 1])

    def test_partial_line_is_retried_after_writer_finishes(self):
        self.log.write_text(record(10) + record(20).rstrip('\n'))
        self.calculate()
        self.assertEqual(self.totals(), [10, 1])
        with self.log.open('a') as stream:
            stream.write('\n')
        self.calculate()
        self.assertEqual(self.totals(), [30, 2])

    def test_missing_and_oversized_logs_leave_metadata_unchanged(self):
        self.meta.write_text('10\n1\n')
        self.assertEqual(self.calculate(), 0)
        self.log.write_text(record(10))
        with patch.object(BW, 'MAX_FILE_SIZE_MB', 0):
            self.assertEqual(self.calculate(), 0)
        self.assertEqual(self.meta.read_text(), '10\n1\n')

    def test_corrupt_metadata_fails_without_destroying_totals(self):
        self.log.write_text(record(10))
        for contents in ('99\nbad\n', '99\n', '-1\n0\n', '99\n1\n{}\n'):
            with self.subTest(contents=contents):
                self.meta.write_text(contents)
                self.assertEqual(self.calculate(), 0)
                self.assertEqual(self.meta.read_text(), contents)

    def test_failed_atomic_replace_preserves_old_metadata_and_cleans_tempfile(self):
        self.log.write_text(record(10) + record(20))
        self.meta.write_text('10\n1\n')
        with patch.object(worker.os, 'replace', side_effect=OSError('disk full')):
            self.assertEqual(self.calculate(), 0)
        self.assertEqual(self.meta.read_text(), '10\n1\n')
        self.assertEqual(list(self.meta.parent.iterdir()), [self.meta])
        self.assertEqual(self.calculate(), 1)
        self.assertEqual(self.totals(), [30, 2])

    def test_failed_metadata_flush_preserves_old_metadata(self):
        self.log.write_text(record(10) + record(20))
        self.meta.write_text('10\n1\n')
        with patch.object(worker.os, 'fsync', side_effect=OSError('disk full')):
            self.assertEqual(self.calculate(), 0)
        self.assertEqual(self.meta.read_text(), '10\n1\n')
        self.assertEqual(list(self.meta.parent.iterdir()), [self.meta])

    def test_log_growth_during_processing_waits_until_next_run(self):
        self.log.write_text(record(10))
        parse = BW.parse_last_digits
        def append_while_parsing(line):
            with self.log.open('a') as stream:
                stream.write(record(20))
            return parse(line)
        with patch.object(BW, 'parse_last_digits', side_effect=append_while_parsing):
            self.assertEqual(self.calculate(), 1)
        self.assertEqual(self.totals(), [10, 1])
        self.calculate()
        self.assertEqual(self.totals(), [30, 2])

    def test_log_read_error_preserves_metadata(self):
        self.log.write_text(record(10))
        self.meta.write_text('10\n1\n')
        real_open = open
        def failing_open(path, *args, **kwargs):
            if str(path) == str(self.log):
                raise PermissionError('unreadable log')
            return real_open(path, *args, **kwargs)
        with patch('builtins.open', side_effect=failing_open):
            self.assertEqual(self.calculate(), 0)
        self.assertEqual(self.meta.read_text(), '10\n1\n')

    def test_timeout_saves_progress_and_next_run_resumes(self):
        self.log.write_text(record(10) + record(20))
        with patch.object(worker.time, 'monotonic', side_effect=[0, 0, 301]):
            self.assertEqual(self.calculate(), 1)
        self.assertEqual(self.totals(), [10, 1])
        self.calculate()
        self.assertEqual(self.totals(), [30, 2])

    def test_timeout_during_legacy_skip_preserves_checkpoint(self):
        self.log.write_text(record(10) + record(20))
        self.meta.write_text('10\n1\n')
        with patch.object(worker.time, 'monotonic', side_effect=[0, 301]):
            self.assertEqual(self.calculate(), 0)
        self.assertEqual(self.meta.read_text(), '10\n1\n')

    def test_memory_pressure_saves_progress(self):
        self.log.write_text(record(10) + record(20))
        process = SimpleNamespace(memory_info=lambda: SimpleNamespace(rss=1024 * 1024 * 1024))
        with patch.dict(sys.modules, {'psutil': SimpleNamespace(Process=lambda: process)}), \
                patch.object(BW, 'MAX_LOG_LINES_PER_BATCH', 1):
            self.assertEqual(self.calculate(), 1)
        self.assertEqual(self.totals(), [10, 1])
        self.calculate()
        self.assertEqual(self.totals(), [30, 2])

    def test_missing_optional_psutil_does_not_stop_work(self):
        self.log.write_text(record(10) + record(20))
        with patch.dict(sys.modules, {'psutil': None}), patch.object(BW, 'MAX_LOG_LINES_PER_BATCH', 1):
            self.assertEqual(self.calculate(), 1)
        self.assertEqual(self.totals(), [30, 2])

    def test_import_does_not_scan_domains_or_set_process_limits(self):
        with patch.object(worker.os, 'listdir') as listing, patch.object(resource, 'setrlimit') as limit:
            load_worker()
        listing.assert_not_called()
        limit.assert_not_called()

    def test_worker_continues_after_one_domain_fails(self):
        with patch.object(BW, 'set_memory_limit'), \
                patch.object(worker.os, 'listdir', return_value=['cyberpanel', 'a.test', 'b.test']), \
                patch.object(BW, 'calculateBandwidth', side_effect=[OSError('broken domain'), 1]) as calculate:
            self.assertEqual(BW.startCalculations(), 1)
        self.assertEqual([call.args[0] for call in calculate.call_args_list], ['a.test', 'b.test'])


class ResourceLimitTests(unittest.TestCase):
    def test_memory_limit_preserves_hard_limit_and_stricter_soft_limit(self):
        megabyte = 1024 * 1024
        for existing, expected in (
            ((resource.RLIM_INFINITY, resource.RLIM_INFINITY), (512 * megabyte, resource.RLIM_INFINITY)),
            ((256 * megabyte, 1024 * megabyte), (256 * megabyte, 1024 * megabyte)),
            ((resource.RLIM_INFINITY, 128 * megabyte), (128 * megabyte, 128 * megabyte)),
        ):
            with self.subTest(existing=existing), patch.object(resource, 'getrlimit', return_value=existing), \
                    patch.object(resource, 'setrlimit') as setter:
                BW.set_memory_limit()
                setter.assert_called_once_with(resource.RLIMIT_AS, expected)

    def test_unsupported_resource_limit_is_logged_and_nonfatal(self):
        with patch.object(resource, 'getrlimit', side_effect=ValueError('unsupported')), \
                patch.object(worker.logging.CyberCPLogFileWriter, 'writeToFile') as logger:
            BW.set_memory_limit()
        logger.assert_called_once()


if __name__ == '__main__':
    unittest.main()
