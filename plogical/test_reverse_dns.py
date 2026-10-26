import json
import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests
from plogical.reverseDNS import reverse_dns_lookup


def response(data):
    return Mock(json=Mock(return_value=data), raise_for_status=Mock())


class ReverseDNSChecks(unittest.TestCase):
    def fallback(self, get, run=None):
        child = run or Mock(return_value=SimpleNamespace(stdout=json.dumps(['Mail.Example.test.'])))
        with patch('plogical.reverseDNS.requests.get', get), patch('plogical.reverseDNS.subprocess.run', child):
            result = reverse_dns_lookup('192.0.2.10')
        return result, child

    def test_listing_timeout_falls_back_and_is_bounded(self):
        get = Mock(side_effect=requests.Timeout())
        result, child = self.fallback(get)
        self.assertEqual(['mail.example.test'], result)
        self.assertEqual(5, get.call_args.kwargs['timeout'])
        self.assertEqual(5, child.call_args.kwargs['timeout'])
        self.assertEqual('192.0.2.10', child.call_args.args[0][-1])

    def test_provider_failure_falls_back(self):
        get = Mock(side_effect=[response({'urls':['https://dns.example.test']}), requests.ConnectionError()])
        result, child = self.fallback(get)
        self.assertEqual(['mail.example.test'], result)
        self.assertEqual({'ip':'192.0.2.10'}, get.call_args.kwargs['params'])
        child.assert_called_once()

    def test_malformed_and_empty_results_fall_back(self):
        for payload in [None, {'urls':None}, {'urls':[]}, {'urls':['https://dns.example.test']}]:
            with self.subTest(payload=payload):
                get = Mock(side_effect=[response(payload), response({'status':1,'results':{'8.8.8.8':''}})])
                self.assertEqual(['mail.example.test'], self.fallback(get)[0])

    def test_successful_provider_deduplicates_without_fallback(self):
        get = Mock(side_effect=[response({'urls':['https://dns.example.test']}),
                               response({'status':1,'results':{'8.8.8.8':'Mail.Example.test.',
                                                            '1.1.1.1':'mail.example.test','9.9.9.9':None}})])
        result, child = self.fallback(get)
        self.assertEqual(['mail.example.test'], result)
        child.assert_not_called()

    def test_local_failure_or_timeout_returns_empty(self):
        for error in [subprocess.TimeoutExpired('resolver',5), subprocess.CalledProcessError(1,'resolver'), OSError()]:
            with self.subTest(error=type(error).__name__):
                self.assertEqual([], self.fallback(Mock(side_effect=requests.Timeout()), Mock(side_effect=error))[0])

    def test_invalid_ip_never_starts_lookup(self):
        with patch('plogical.reverseDNS.requests.get') as get, patch('plogical.reverseDNS.subprocess.run') as run:
            self.assertEqual([], reverse_dns_lookup('example.test;id'))
            get.assert_not_called(); run.assert_not_called()

    def test_ipv6_is_passed_as_a_single_argument(self):
        with patch('plogical.reverseDNS.requests.get',side_effect=requests.Timeout()), patch('plogical.reverseDNS.subprocess.run',return_value=SimpleNamespace(stdout='["mail.example.test."]')) as run:
            self.assertEqual(['mail.example.test'],reverse_dns_lookup('2001:db8::1'))
            self.assertEqual('2001:db8::1',run.call_args.args[0][-1])

    def test_invalid_local_output_does_not_pass_hostname_check(self):
        for value in ['not json','{}','["192.0.2.10", "bad host", "-bad.test"]']:
            self.assertEqual([],self.fallback(Mock(side_effect=requests.Timeout()),Mock(return_value=SimpleNamespace(stdout=value)))[0])


if __name__ == '__main__':
    unittest.main()
