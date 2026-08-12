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


if __name__ == '__main__':
    unittest.main()
