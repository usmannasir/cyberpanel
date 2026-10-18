import os
import tempfile
import unittest
from unittest.mock import patch

from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter


class StatusWriterTest(unittest.TestCase):
    def test_restore_without_status_file_does_not_log_an_error(self):
        with patch.object(CyberCPLogFileWriter, 'writeToFile') as error_log:
            CyberCPLogFileWriter.statusWriter(None, 'Creating configurations..,50')
        error_log.assert_not_called()

    def test_status_file_still_records_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'status')
            CyberCPLogFileWriter.statusWriter(path, 'Starting,10')
            CyberCPLogFileWriter.statusWriter(path, 'Completed. [200]', 1)
            with open(path) as status_file:
                self.assertEqual(status_file.read(), 'Starting,10\nCompleted. [200]\n')


if __name__ == '__main__':
    unittest.main()
