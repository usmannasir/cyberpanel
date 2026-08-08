import os
import pathlib
import tempfile
import unittest

from plogical.ftpConfiguration import pure_ftpd_service_name, write_chroot_everyone


class FTPConfigurationTests(unittest.TestCase):

    def test_all_ubuntu_variants_use_mysql_service(self):
        ubuntu_distros = (0, 3)
        self.assertEqual('pure-ftpd-mysql', pure_ftpd_service_name(0, ubuntu_distros))
        self.assertEqual('pure-ftpd-mysql', pure_ftpd_service_name(3, ubuntu_distros))
        self.assertEqual('pure-ftpd', pure_ftpd_service_name(2, ubuntu_distros))

    def test_chroot_setting_is_written(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = write_chroot_everyone(os.path.join(directory, 'conf'))
            with open(config_path) as handle:
                self.assertEqual('yes\n', handle.read())

    def test_data_hub_links_to_ftp_deletion(self):
        repository = pathlib.Path(__file__).parents[1]
        hub = (repository / 'baseTemplate' / 'templates' / 'baseTemplate' / 'hub.html').read_text()
        self.assertIn("{% url 'deleteFTPAccount' %}", hub)
        self.assertIn('admin or deleteFTPAccount', hub)


if __name__ == '__main__':
    unittest.main()
