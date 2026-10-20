import json
from unittest.mock import patch
from django.test import SimpleTestCase, RequestFactory
from managePHP.phpManager import PHPManager
from managePHP import views


class SignedPHPLimitTests(SimpleTestCase):
    def test_readers_preserve_signed_values_and_ignore_commented_limits(self):
        cases = [('-1', '-1', '30'), ('512M', '-1', '0'),
                 ('+256M', '+60', '+120'), ('"-1"', "'-1'", '30'),
                 ('0', '0', '0')]
        for memory, input_time, execution_time in cases:
            config = '\n'.join([
                'allow_url_fopen = On', 'display_errors = Off',
                'file_uploads = On', 'allow_url_include = Off',
                'memory_limit = ' + memory,
                'max_input_time = ' + input_time,
                'max_execution_time = ' + execution_time,
                'upload_max_filesize = 64M', 'post_max_size = 128M',
                '; memory_limit = 1', '; max_input_time = 999',
                '; max_execution_time = 999', 'max_memory_limit = 2G',
            ])
            expected = {k: v.strip('\"\'') for k, v in {
                'memory_limit': memory, 'max_input_time': input_time,
                'max_execution_time': execution_time}.items()}
            with self.subTest(values=expected):
                with patch.object(PHPManager, 'FindPHPFPMPath', return_value='/fixture.ini'), \
                     patch.object(views.ProcessUtilities, 'outputExecutioner', return_value=config), \
                     patch.object(views.ACLManager, 'loadedACL', return_value={'admin': 1}), \
                     patch('ApachController.ApacheVhosts.ApacheVhost.DecidePHPPathforManager', return_value='/fixture.ini'):
                    request = RequestFactory().post('/managephp/getCurrentPHPConfig',
                        data=json.dumps({'phpSelection': 'PHP 8.3'}), content_type='application/json')
                    request.session = {'userID': 1}
                    responses = [views.getCurrentPHPConfig(request), PHPManager.getCurrentPHPConfig('PHP 8.3')]
                for response in responses:
                    data = json.loads(response.content)
                    self.assertEqual(1, data['fetchStatus'])
                    for key, value in expected.items():
                        self.assertEqual(value, data[key])
                    self.assertEqual('64M', data['upload_max_filesize'])
                    self.assertEqual('128M', data['post_max_size'])
