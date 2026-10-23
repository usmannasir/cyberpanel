import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from plogical.virtualHostUtilities import virtualHostUtilities


class VirtualHostLogUtilitiesTests(unittest.TestCase):

    @patch('plogical.virtualHostUtilities.os.path.islink', return_value=False)
    @patch('plogical.virtualHostUtilities.ProcessUtilities.outputExecutioner')
    @patch('builtins.print')
    def test_error_logs_read_valid_wc_output(self, printed, execute, islink):
        log_path = '/home/example.com/logs/example.com.error_log'
        execute.side_effect = ['2 ' + log_path, 'first log line\nsecond log line']

        result = virtualHostUtilities.getErrorLogs(log_path, 1, 'example')

        self.assertEqual('first log line\nsecond log line', result)
        self.assertEqual(
            [
                (('wc -l -- ' + log_path, 'example'),),
                (('cat -- ' + log_path, 'example'),),
            ],
            [(call.args,) for call in execute.call_args_list],
        )

    @patch('plogical.virtualHostUtilities.logging.CyberCPLogFileWriter.writeToFile')
    @patch('plogical.virtualHostUtilities.os.path.islink', return_value=False)
    @patch('plogical.virtualHostUtilities.ProcessUtilities.outputExecutioner',
           return_value='wc: permission denied')
    @patch('builtins.print')
    def test_error_logs_handle_unreadable_log_count(self, printed, execute, islink, write_log):
        result = virtualHostUtilities.getErrorLogs(
            '/home/example.com/logs/example.com.error_log', 1, 'example')

        self.assertEqual('1,None', result)
        write_log.assert_called_once()


    @patch('builtins.print')
    def test_log_pages_use_real_commands_and_stop_at_eof(self, printed):
        def execute(command, user):
            return subprocess.check_output(command, shell=True, text=True,
                                           stderr=subprocess.STDOUT)

        with tempfile.TemporaryDirectory() as directory:
            log_path = os.path.join(directory, "customer's access log")
            for total in (0, 2, 25, 26, 50, 135):
                lines = ['row %s\n' % number for number in range(total)]
                with open(log_path, 'w') as log:
                    log.writelines(lines)
                for helper in (virtualHostUtilities.getAccessLogs,
                               virtualHostUtilities.getErrorLogs):
                    with self.subTest(total=total, helper=helper.__name__), patch(
                            'plogical.virtualHostUtilities.ProcessUtilities.outputExecutioner',
                            side_effect=execute):
                        pages = []
                        for page in range(1, (total + 24) // 25 + 3):
                            result = helper(log_path, page, 'example')
                            end = max(0, total - (page - 1) * 25)
                            expected = ''.join(lines[max(0, end - 25):end])
                            self.assertEqual(expected, result)
                            pages.append(result.splitlines(keepends=True))
                        self.assertEqual(lines, [line for page in reversed(pages)
                                                 for line in page])

    @patch('builtins.print')
    @patch('plogical.virtualHostUtilities.logging.CyberCPLogFileWriter.writeToFile')
    @patch('plogical.virtualHostUtilities.ProcessUtilities.outputExecutioner',
           return_value='135 example.log')
    def test_invalid_pages_fail_without_reading_log(self, execute, write_log, printed):
        for helper in (virtualHostUtilities.getAccessLogs,
                       virtualHostUtilities.getErrorLogs):
            for page in (0, -1, True, 1.5, '2'):
                execute.reset_mock()
                with self.subTest(helper=helper.__name__, page=page):
                    self.assertEqual('1,None', helper('/tmp/example.log', page, 'example'))
                    self.assertEqual(1, execute.call_count)

    @patch('builtins.print')
    @patch('plogical.virtualHostUtilities.os.path.islink', return_value=True)
    @patch('plogical.virtualHostUtilities.ProcessUtilities.outputExecutioner')
    def test_symlink_is_rejected_without_reading(self, execute, islink, printed):
        for helper in (virtualHostUtilities.getAccessLogs,
                       virtualHostUtilities.getErrorLogs):
            self.assertEqual(0, helper('/tmp/example.log', 1, 'example'))
        execute.assert_not_called()


if __name__ == '__main__':
    unittest.main()
