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

    def test_database_server_is_restarted_for_a_post_of_an_administrator_only(self):
        with mock.patch('databases.views.ACLManager.loadedACL', return_value={'admin': 1}), \
                mock.patch('databases.views.mysqlUtilities.restartMySQL', return_value=(1, 'None')) as restart:
            for method in ('get', 'head', 'put'):
                request = getattr(RequestFactory(), method)('/dataBases/restartMySQL')
                request.session = {'userID': 1}
                self.assertEqual(405, views.restartMySQL(request).status_code, method)
            restart.assert_not_called()
            response = views.restartMySQL(self.post('/dataBases/restartMySQL', {}))
            self.assertEqual(1, json.loads(response.content.decode('utf-8'))['status'])
            restart.assert_called_once_with()
        with mock.patch('databases.views.ACLManager.loadedACL', return_value={'admin': 0}), \
                mock.patch('databases.views.mysqlUtilities.restartMySQL') as restart:
            views.restartMySQL(self.post('/dataBases/restartMySQL', {}))
            restart.assert_not_called()

    def test_database_server_status_is_read_for_an_administrator_only(self):
        with mock.patch('databases.views.ACLManager.loadedACL', return_value={'admin': 0}), \
                mock.patch('databases.views.mysqlUtilities.showStatus') as status:
            views.getMysqlstatus(self.post('/dataBases/getMysqlstatus', {}))
            status.assert_not_called()
        with mock.patch('databases.views.ACLManager.loadedACL', return_value={'admin': 1}), \
                mock.patch('databases.views.mysqlUtilities.showStatus', return_value={'uptime': 1}) as status:
            response = views.getMysqlstatus(self.post('/dataBases/getMysqlstatus', {}))
            self.assertEqual({'uptime': 1}, json.loads(response.content.decode('utf-8')))
            status.assert_called_once_with()
