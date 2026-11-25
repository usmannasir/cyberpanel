import json
import os
import tempfile
from unittest import mock

from django.test import RequestFactory, SimpleTestCase

from baseTemplate import views


# Ubuntu 26.04 rsyslog (ISO timestamps) and classic syslog (AlmaLinux), as on real servers.
UBUNTU_2604_AUTH_LOG = """2026-11-25T16:28:50.694516+00:00 cpqa-sw26 sshd-session[78601]: Failed password for root from 176.53.159.197 port 52732 ssh2
2026-11-25T16:30:49.342072+00:00 cpqa-sw26 sudo: pam_unix(sudo:session): session closed for user root
2026-11-25T16:30:50.609569+00:00 cpqa-sw26 sudo:     root : PWD=/tmp/lscpd ; USER=root ; COMMAND=/usr/bin/tail -n 2000 /var/log/auth.log
2026-11-25T16:31:02.000001+00:00 cpqa-sw26 sshd-session[78700]: Accepted publickey for root from 136.243.211.211 port 50950 ssh2
"""
ALMALINUX_SECURE = """Nov 25 16:31:28 cpqa-sw10 sshd-session[70630]: Received disconnect from 136.243.211.211 port 56664:11: disconnected by user
Nov  5 06:01:02 cpqa-sw10 sshd[900]: Accepted password for root from 203.0.113.7 port 22 ssh2
Nov 25 16:31:29 cpqa-sw10 sudo[70700]: pam_unix(sudo:session): session opened for user root
"""


class SshLogLinesTests(SimpleTestCase):

    def test_iso_timestamps_keep_the_whole_message(self):
        logs = views.parse_ssh_log_lines(UBUNTU_2604_AUTH_LOG)

        self.assertEqual(['Nov 25 16:28:50', 'Nov 25 16:31:02'], [row['timestamp'] for row in logs])
        self.assertEqual('sshd-session[78601]: Failed password for root from 176.53.159.197 port 52732 ssh2',
                         logs[0]['message'])
        self.assertTrue(logs[1]['message'].startswith('sshd-session[78700]: Accepted publickey'))

    def test_classic_syslog_lines(self):
        logs = views.parse_ssh_log_lines(ALMALINUX_SECURE)

        self.assertEqual(['Nov 25 16:31:28', 'Nov  5 06:01:02'], [row['timestamp'] for row in logs])
        self.assertEqual('sshd[900]: Accepted password for root from 203.0.113.7 port 22 ssh2', logs[1]['message'])

    def test_other_programs_and_error_text_are_left_out(self):
        text = UBUNTU_2604_AUTH_LOG + "tail: cannot open '/var/log/auth.log' for reading: No such file or directory\n"
        messages = [row['message'] for row in views.parse_ssh_log_lines(text)]

        self.assertFalse([m for m in messages if 'sudo' in m or 'tail:' in m])

    def test_the_last_lines_are_kept(self):
        text = ''.join('Nov 25 10:%02d:00 h sshd[1]: line %d\n' % (n % 60, n) for n in range(150))
        logs = views.parse_ssh_log_lines(text)

        self.assertEqual(100, len(logs))
        self.assertTrue(logs[-1]['message'].endswith('line 149'))


class SshLogsViewTests(SimpleTestCase):

    def get(self):
        request = RequestFactory().get('/base/getRecentSSHLogs')
        request.session = {'userID': 1}
        return request

    @mock.patch('baseTemplate.views.ACLManager.loadedACL', return_value={'admin': 1})
    def test_ubuntu_2604_log(self, unused_acl):
        with mock.patch('plogical.processUtilities.ProcessUtilities.decideDistro', return_value=3), \
                mock.patch('plogical.processUtilities.ProcessUtilities.outputExecutioner',
                           return_value=UBUNTU_2604_AUTH_LOG) as run:
            response = views.getRecentSSHLogs(self.get())

        logs = json.loads(response.content)['logs']
        self.assertEqual('tail -n 2000 /var/log/auth.log', run.call_args_list[0].args[0])
        self.assertEqual(2, len(logs))
        self.assertIn('Failed password', logs[0]['message'])

    @mock.patch('baseTemplate.views.ACLManager.loadedACL', return_value={'admin': 1})
    def test_no_log_file_reads_the_journal(self, unused_acl):
        journal = '2026-11-25T14:02:09+00:00 host sshd-session[812]: Accepted publickey for root from 203.0.113.7 port 1 ssh2\n'
        answers = ["tail: cannot open '/var/log/auth.log' for reading: No such file or directory", journal]
        with mock.patch('plogical.processUtilities.ProcessUtilities.decideDistro', return_value=3), \
                mock.patch('plogical.processUtilities.ProcessUtilities.outputExecutioner', side_effect=answers) as run, \
                mock.patch('baseTemplate.views.os.path.exists', return_value=False):
            response = views.getRecentSSHLogs(self.get())

        logs = json.loads(response.content)['logs']
        self.assertTrue(run.call_args_list[1].args[0].startswith('journalctl '))
        self.assertEqual(['Nov 25 14:02:09'], [row['timestamp'] for row in logs])


class DiskIoTests(SimpleTestCase):

    def test_each_disk_counts_once(self):
        # vda with three partitions, an LVM volume on top, a CD-ROM and a loop device.
        stats = '\n'.join([
            ' 252 0 vda 100 0 1000 0 200 0 2000 0 0 0 0',
            ' 252 1 vda1 60 0 600 0 150 0 1500 0 0 0 0',
            ' 252 14 vda14 1 0 8 0 0 0 0 0 0 0 0',
            ' 252 15 vda15 39 0 392 0 50 0 500 0 0 0 0',
            ' 253 0 dm-0 60 0 600 0 150 0 1500 0 0 0 0',
            '  11 0 sr0 5 0 50 0 0 0 0 0 0 0 0',
            '   7 0 loop0 9 0 90 0 0 0 0 0 0 0 0',
            ' 259 0 nvme0n1 10 0 300 0 20 0 400 0 0 0 0',
        ]) + '\n'
        with tempfile.TemporaryDirectory() as root:
            for disk in ('vda', 'sr0', 'loop0', 'dm-0', 'nvme0n1'):
                os.makedirs(os.path.join(root, 'block', disk))
            for disk in ('vda', 'sr0', 'nvme0n1'):
                os.makedirs(os.path.join(root, 'block', disk, 'device'))
            path = os.path.join(root, 'diskstats')
            with open(path, 'w') as f:
                f.write(stats)

            self.assertEqual((1300, 2400), views.disk_io_sectors(path, os.path.join(root, 'block')))


class StatusFallbackTests(SimpleTestCase):

    @mock.patch('baseTemplate.views.ACLManager.loadedACL', side_effect=Exception('database unavailable'))
    def test_an_error_reports_nothing_instead_of_made_up_hardware(self, unused_acl):
        request = RequestFactory().get('/base/getSystemStatus')
        request.session = {'userID': 1}

        data = json.loads(views.getSystemStatus(request).content)

        self.assertEqual((0, 0, 0, 0), (data['cpuCores'], data['ramTotalMB'], data['diskTotalGB'], data['diskFreeGB']))
        self.assertEqual('N/A', data['uptime'])
