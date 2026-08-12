from types import SimpleNamespace
import unittest

import psutil

from serverStatus.views import get_service_memory_usage


class ProcessMemoryUsageTests(unittest.TestCase):

    def test_counts_mariadb_and_mysql_processes(self):
        processes = [
            SimpleNamespace(info={
                'name': 'mariadbd',
                'memory_info': SimpleNamespace(rss=4096),
            }),
            SimpleNamespace(info={
                'name': 'mysql-router',
                'memory_info': SimpleNamespace(rss=2048),
            }),
            SimpleNamespace(info={
                'name': 'unrelated-process',
                'memory_info': SimpleNamespace(rss=8192),
            }),
        ]

        memory_usage = get_service_memory_usage(
            ('mariadbd', 'mysqld', 'mysql'), lambda attrs: processes)

        self.assertEqual(6144, memory_usage)

    def test_skips_processes_that_cannot_be_inspected(self):
        class UnavailableProcess:
            @property
            def info(self):
                raise psutil.AccessDenied(pid=1)

        processes = [
            UnavailableProcess(),
            SimpleNamespace(info={
                'name': 'litespeed',
                'memory_info': SimpleNamespace(rss=1024),
            }),
        ]

        memory_usage = get_service_memory_usage(
            ('litespeed', 'lshttpd'), lambda attrs: processes)

        self.assertEqual(1024, memory_usage)


if __name__ == '__main__':
    unittest.main()
