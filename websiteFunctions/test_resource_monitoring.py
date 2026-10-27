import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
from websiteFunctions import resource_monitoring as resource

class ResourceUsageTests(unittest.TestCase):
    def setUp(self):
        self.site=NS(domain='domain.example',externalApp='siteuser')
        self.process=patch.object(resource,'process_usage',return_value=(25,6.25));self.process.start();self.addCleanup(self.process.stop)
        self.execute=patch.object(resource.ProcessUtilities,'outputExecutioner',side_effect=[(1,'5120\t/home/domain.example/public_html\n'),(1,'Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/test 1048576 10 1048566 1% /\n')]).start();self.addCleanup(patch.stopall)
    def test_domain_document_root_is_measured_instead_of_unix_username(self):
        data=resource.get_website_resource_usage(self.site)
        self.assertEqual(1,data['status']);self.assertEqual(5,data['disk_used']);self.assertEqual(1024,data['disk_total'])
        command=self.execute.call_args_list[0].args[0]
        self.assertIn('/home/domain.example/public_html',command);self.assertNotIn('/home/siteuser/',command)
        self.assertIn('/usr/bin/timeout 5 ',command);self.assertFalse(self.execute.call_args.kwargs['shell'])
    def test_disk_command_failure_is_unavailable_not_zero_usage(self):
        self.execute.side_effect=[(0,'permission denied')]
        data=resource.get_website_resource_usage(self.site);self.assertEqual(0,data['status']);self.assertNotIn('disk_used',data)
    def test_malformed_disk_output_is_unavailable(self):
        self.execute.side_effect=[(1,'not-a-number')];self.assertEqual(0,resource.get_website_resource_usage(self.site)['status'])
    def test_invalid_domain_does_not_run_commands(self):
        self.site.domain='../other';self.assertEqual(0,resource.get_website_resource_usage(self.site)['status']);self.execute.assert_not_called()
    def test_document_root_escape_does_not_run_commands(self):
        with patch.object(resource.os.path,'realpath',side_effect=lambda p:'/outside' if p.endswith('/public_html') else p):
            self.assertEqual(0,resource.get_website_resource_usage(self.site)['status'])
        self.execute.assert_not_called()
    def test_unreadable_process_usage_is_not_reported_as_zero(self):
        resource.process_usage.side_effect=ValueError('unavailable')
        self.assertEqual(0,resource.get_website_resource_usage(self.site)['status']);self.execute.assert_not_called()

    def test_missing_unix_account_is_unavailable(self):
        resource.process_usage.side_effect=KeyError('missing user')
        self.assertEqual(0,resource.get_website_resource_usage(self.site)['status']);self.execute.assert_not_called()

    def test_process_iterator_access_denied_is_unavailable(self):
        self.process.stop()
        def denied(*args):
            raise resource.psutil.AccessDenied(pid=123)
            yield
        with patch.object(resource.pwd,'getpwnam',return_value=NS(pw_uid=1001)),patch.object(resource.psutil,'process_iter',side_effect=denied):
            self.assertEqual(0,resource.get_website_resource_usage(self.site)['status'])
        self.execute.assert_not_called()

class ProcessUsageTests(unittest.TestCase):
    def test_cpu_is_sampled_and_normalized_to_host_capacity(self):
        process=Mock();process.info={'uids':NS(effective=1001),'cpu_times':NS(user=1.0,system=0)}
        process.cpu_times.return_value=NS(user=1.1,system=0);process.memory_info.return_value=NS(rss=64*1024*1024)
        with patch.object(resource.pwd,'getpwnam',return_value=NS(pw_uid=1001)),patch.object(resource.psutil,'process_iter',return_value=[process]),patch.object(resource.psutil,'cpu_count',return_value=4),patch.object(resource.psutil,'virtual_memory',return_value=NS(total=1024*1024*1024)),patch.object(resource.time,'sleep'),patch.object(resource.time,'monotonic',side_effect=[0,0,0,0.1]):
            cpu,memory=resource.process_usage('siteuser');self.assertAlmostEqual(25,cpu);self.assertEqual(6.25,memory)
    def test_each_process_uses_its_own_sampling_interval(self):
        first,second=Mock(),Mock()
        for process,after in ((first,1.2),(second,1.1)):
            process.info={'uids':NS(effective=1001),'cpu_times':NS(user=1.0,system=0)}
            process.cpu_times.return_value=NS(user=after,system=0);process.memory_info.return_value=NS(rss=0)
        with patch.object(resource.pwd,'getpwnam',return_value=NS(pw_uid=1001)),patch.object(resource.psutil,'process_iter',return_value=[first,second]),patch.object(resource.psutil,'cpu_count',return_value=4),patch.object(resource.psutil,'virtual_memory',return_value=NS(total=1024)),patch.object(resource.time,'sleep'),patch.object(resource.time,'monotonic',side_effect=[0,0,0,0.1,0.1,0.2,0.2]):
            cpu,memory=resource.process_usage('siteuser');self.assertAlmostEqual(50,cpu);self.assertEqual(0,memory)
    def test_invalid_system_user_refuses_before_sampling(self):
        for user in ('root','site;command','../user'):
            with self.assertRaises(ValueError):resource.process_usage(user)
    def test_idle_account_has_zero_process_usage(self):
        with patch.object(resource.pwd,'getpwnam',return_value=NS(pw_uid=1001)),patch.object(resource.psutil,'process_iter',return_value=[]),patch.object(resource.time,'sleep'):
            self.assertEqual((0,0),resource.process_usage('siteuser'))

class ResourceLimitDisplayTests(unittest.TestCase):
    def test_cpu_percent_is_not_mislabeled_as_core_count(self):
        self.assertEqual('2 cores (200%)',resource.format_resource_limits({'cpu':'200'})['cpu'])
    def test_fractional_cpu_is_preserved(self):
        self.assertEqual('0.5 cores (50%)',resource.format_resource_limits({'cpu':'50%'})['cpu'])
    def test_unlimited_values_are_labeled(self):
        result=resource.format_resource_limits({'cpu':'-1','mem':'','io':'infinity','tasks':'max'})
        self.assertEqual(['Unlimited']*4,[result[k] for k in ('cpu','memory','io','tasks')])
    def test_invalid_cpu_is_unavailable(self):
        self.assertEqual('Unavailable',resource.format_resource_limits({'cpu':'bad'})['cpu'])

    def test_nonfinite_and_negative_cpu_are_unavailable(self):
        for value in ('NaN','inf','-5'):
            self.assertEqual('Unavailable',resource.format_resource_limits({'cpu':value})['cpu'])
    def test_missing_values_are_not_claimed_unlimited(self):
        self.assertEqual({'Unavailable'},set(resource.format_resource_limits({}).values()))


class AccountBridgeTests(unittest.TestCase):
    def test_service_user_samples_through_authenticated_bridge(self):
        with patch.object(resource.os,'geteuid',return_value=1000),patch.object(resource,'process_usage') as direct,patch.object(resource.ProcessUtilities,'outputExecutioner',return_value=(1,'{"cpu_usage":25,"memory_usage":2}')) as execute:
            self.assertEqual((25,2),resource.account_usage('siteuser'));direct.assert_not_called()
            self.assertIn('--account-usage siteuser',execute.call_args.args[0]);self.assertFalse(execute.call_args.kwargs['shell'])
    def test_bridge_failure_is_not_zero(self):
        with patch.object(resource.os,'geteuid',return_value=1000),patch.object(resource.ProcessUtilities,'outputExecutioner',return_value=(0,'denied')):
            with self.assertRaises(ValueError):resource.account_usage('siteuser')
    def test_invalid_bridge_metrics_are_rejected(self):
        for output in ('{}','{"cpu_usage":NaN,"memory_usage":2}','{"cpu_usage":true,"memory_usage":2}'):
            with patch.object(resource.os,'geteuid',return_value=1000),patch.object(resource.ProcessUtilities,'outputExecutioner',return_value=(1,output)):
                with self.assertRaises((ValueError,KeyError)):resource.account_usage('siteuser')
    def test_invalid_user_never_reaches_bridge(self):
        with patch.object(resource.os,'geteuid',return_value=1000),patch.object(resource.ProcessUtilities,'outputExecutioner') as execute:
            with self.assertRaises(ValueError):resource.account_usage('root')
            execute.assert_not_called()
