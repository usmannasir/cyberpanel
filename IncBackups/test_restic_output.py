import unittest

from IncBackups.resticOutput import extract_snapshot_id


class ResticOutputTests(unittest.TestCase):

    def test_snapshot_id_is_read_before_a_trailing_warning(self):
        output = '''
processed 4294 files, 85.552 MiB in 0:00
snapshot 181bf81f saved
Warning: at least one source file could not be read
'''

        self.assertEqual(extract_snapshot_id(output), '181bf81f')

    def test_full_snapshot_id_is_supported(self):
        snapshot_id = 'a' * 64
        self.assertEqual(
            extract_snapshot_id('snapshot %s saved\n' % snapshot_id),
            snapshot_id,
        )

    def test_missing_snapshot_id_is_rejected(self):
        with self.assertRaises(ValueError):
            extract_snapshot_id('Fatal: unable to open repository')


if __name__ == '__main__':
    unittest.main()
