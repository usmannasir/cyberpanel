import json
import os
import tempfile
from unittest import mock

from django.test import RequestFactory, SimpleTestCase

from databases import views


class DatabaseSecurityTests(SimpleTestCase):

    def post(self, path, payload):
        request = RequestFactory().post(
            path,
            data=json.dumps(payload),
            content_type='application/json',
        )
        request.session = {'userID': 1}
        return request

    @mock.patch('databases.views.ACLManager.loadedACL', return_value={'admin': 1})
    def test_mariadb_upgrade_rejects_unlisted_version(self, unused_acl):
        request = self.post(
            '/dataBases/upgrademysqlnow',
            {'mysqlversion': '10.11;id'},
        )

        with mock.patch('databases.views.ProcessUtilities.popenExecutioner') as execute:
            response = views.upgrademysqlnow(request)

        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(0, result['status'])
        execute.assert_not_called()

    @mock.patch('databases.views.ACLManager.loadedACL', return_value={'admin': 1})
    def test_mariadb_status_rejects_paths_outside_private_status_directory(self, unused_acl):
        request = self.post(
            '/dataBases/upgrademysqlstatus',
            {'statusfile': '/etc/passwd'},
        )

        with mock.patch('databases.views.ProcessUtilities.outputExecutioner') as read_status, \
                mock.patch('databases.views.ProcessUtilities.executioner') as remove_status:
            response = views.upgrademysqlstatus(request)

        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(0, result['status'])
        read_status.assert_not_called()
        remove_status.assert_not_called()

    @mock.patch('databases.views.ACLManager.loadedACL', return_value={'admin': 1})
    def test_mariadb_status_reads_and_removes_valid_completed_file_without_shell(
            self,
            unused_acl):
        with tempfile.TemporaryDirectory() as directory:
            status_path = os.path.join(directory, 'mysql-upgrade-safe123')
            with open(status_path, 'w', encoding='utf-8') as status_file:
                status_file.write('Completed [200]\n')
            os.chmod(status_path, 0o600)
            request = self.post(
                '/dataBases/upgrademysqlstatus',
                {'statusfile': status_path},
            )

            with mock.patch(
                    'databases.views.get_mysql_upgrade_status_path',
                    return_value=status_path,
            ), mock.patch('databases.views.ProcessUtilities.outputExecutioner') as read_status, \
                    mock.patch('databases.views.ProcessUtilities.executioner') as remove_status:
                response = views.upgrademysqlstatus(request)

            result = json.loads(response.content.decode('utf-8'))
            self.assertEqual(1, result['installed'])
            self.assertFalse(os.path.exists(status_path))
            read_status.assert_not_called()
            remove_status.assert_not_called()
