#!/usr/bin/python3
# -*- coding: utf-8 -*-

import DNS
import unittest
try:
    import ipaddress
except ImportError:
    import ipaddr as ipaddress

def assertIsByte(b):
    assert b >= 0
    assert b <= 255
    
class TestBase(unittest.TestCase):
    def testParseResolvConf(self):
        # reset elments set by Base._DiscoverNameServers
        DNS.defaults['server'] = []
        if 'domain' in  DNS.defaults:
            del DNS.defaults['domain']
        self.assertEqual(len(DNS.defaults['server']), 0)
        resolv = ['# a comment',
                  'domain example.org',
                  'nameserver 127.0.0.1',
                 ]
        DNS.ParseResolvConfFromIterable(resolv)
        self.assertEqual(len(DNS.defaults['server']), 1)
        self.assertEqual(DNS.defaults['server'][0], '127.0.0.1')
        self.assertEqual(DNS.defaults['domain'], 'example.org')
        
    def testDnsRequestA(self):
        # try with asking for strings, and asking for bytes
        dnsobj = DNS.DnsRequest('example.org')
        
        a_response = dnsobj.qry(qtype='A', resulttype='text', timeout=1)
        self.assertTrue(a_response.answers)
        # is the result vaguely ipv4 like?
        self.assertEqual(a_response.answers[0]['data'].count('.'), 3)
        self.assertEqual(a_response.answers[0]['data'],'93.184.215.14')

        # Default result type for .qry object is an ipaddress object
        ad_response = dnsobj.qry(qtype='A', timeout=1)
        self.assertTrue(ad_response.answers)
        self.assertEqual(ad_response.answers[0]['data'],ipaddress.IPv4Address('93.184.215.14'))

        ab_response = dnsobj.qry(qtype='A', resulttype='binary', timeout=1)
        self.assertTrue(ab_response.answers)
        # is the result ipv4 binary like?
        self.assertEqual(len(ab_response.answers[0]['data']), 4)
        for b in ab_response.answers[0]['data']:
            assertIsByte(b)
        self.assertEqual(ab_response.answers[0]['data'],b']\xb8\xd7\x0e')

        ai_response = dnsobj.qry(qtype='A', resulttype='integer', timeout=1)
        self.assertTrue(ai_response.answers)
        self.assertEqual(ai_response.answers[0]['data'],1572394766)


    def testDnsRequestAAAA(self):
        dnsobj = DNS.DnsRequest('example.org')
        
        aaaa_response = dnsobj.qry(qtype='AAAA', resulttype='text', timeout=1)
        self.assertTrue(aaaa_response.answers)
        # does the result look like an ipv6 address?
        self.assertTrue(':' in aaaa_response.answers[0]['data'])
        self.assertEqual(aaaa_response.answers[0]['data'],'2606:2800:21f:cb07:6820:80da:af6b:8b2c')

        # default is returning ipaddress object
        aaaad_response = dnsobj.qry(qtype='AAAA', timeout=1)
        self.assertTrue(aaaad_response.answers)
        self.assertEqual(aaaad_response.answers[0]['data'],ipaddress.IPv6Address('2606:2800:21f:cb07:6820:80da:af6b:8b2c'))
        
        aaaab_response = dnsobj.qry(qtype='AAAA', resulttype='binary', timeout=1)
        self.assertTrue(aaaab_response.answers)
        # is it ipv6 looking?
        self.assertEqual(len(aaaab_response.answers[0]['data']) , 16)
        for b in aaaab_response.answers[0]['data']:
            assertIsByte(b)
        self.assertEqual(aaaab_response.answers[0]['data'],b'&\x06(\x00\x02\x1f\xcb\x07h \x80\xda\xafk\x8b,')
        # IPv6 decimal
        aaaai_response = dnsobj.qry(qtype='AAAA', resulttype='integer', timeout=1)
        self.assertTrue(aaaai_response.answers)
        self.assertEqual(aaaai_response.answers[0]['data'], 50542628918019563700009922510424083244)

    def testDnsRequestEmptyMX(self):
        dnsobj = DNS.DnsRequest('mail.kitterman.org')

        mx_empty_response = dnsobj.qry(qtype='MX', timeout=1)
        self.assertFalse(mx_empty_response.answers)

    def testDnsRequestMX(self):
        dnsobj = DNS.DnsRequest('ietf.org')
        mx_response = dnsobj.qry(qtype='MX', timeout=1)
        self.assertTrue(mx_response.answers[0])
        # is hard coding a remote address a good idea?
        # I think it's unavoidable. - sk
        self.assertEqual(mx_response.answers[0]['data'], (0, 'mail.ietf.org'))

        m = DNS.mxlookup('ietf.org', timeout=1)
        self.assertEqual(mx_response.answers[0]['data'], m[0])

    def testDnsRequestSrv(self):
        dnsobj = DNS.Request(qtype='srv')
        respdef = dnsobj.qry('_ldap._tcp.openldap.org', timeout=1)
        self.assertTrue(respdef.answers)
        data = respdef.answers[0]['data']
        self.assertEqual(len(data), 4)
        self.assertEqual(data[2], 389)
        self.assertTrue('openldap.org' in data[3])

    def testDkimRequest(self):
        q = '20161025._domainkey.google.com'
        dnsobj = DNS.Request(q, qtype='txt')
        resp = dnsobj.qry(timeout=1)
        
        self.assertTrue(resp.answers)
        # should the result be bytes or a string? (Bytes, we finally settled on bytes)
        data = resp.answers[0]['data']
        self.assertFalse(isinstance(data[0], str))
        self.assertTrue(data[0].startswith(b'k=rsa'))

    def testDNSRequestTXT(self):
        dnsobj = DNS.DnsRequest('fail.kitterman.org')

        respdef = dnsobj.qry(qtype='TXT', timeout=1)
        self.assertTrue(respdef.answers)
        data = respdef.answers[0]['data']
        self.assertEqual(data, [b'v=spf1 -all'])

        resptext = dnsobj.qry(qtype='TXT', resulttype='text', timeout=1)
        self.assertTrue(resptext.answers)
        data = resptext.answers[0]['data']
        self.assertEqual(data, ['v=spf1 -all'])

        respbin = dnsobj.qry(qtype='TXT', resulttype='binary', timeout=1)
        self.assertTrue(respbin.answers)
        data = respbin.answers[0]['data']
        self.assertEqual(data, [b'\x0bv=spf1 -all'])

    def testIDN(self):
        """Can we lookup an internationalized domain name?"""
        dnsobj = DNS.DnsRequest('xn--bb-eka.at')
        unidnsobj = DNS.DnsRequest('öbb.at')
        a_resp = dnsobj.qry(qtype='A', resulttype='text', timeout=1)
        ua_resp = unidnsobj.qry(qtype='A', resulttype='text', timeout=1)
        self.assertTrue(a_resp.answers)
        self.assertTrue(ua_resp.answers)
        self.assertEqual(ua_resp.answers[0]['data'], 
                         a_resp.answers[0]['data'])

    def testNS(self):
        """Lookup NS record from SOA"""
        dnsob = DNS.DnsRequest('kitterman.com')
        resp = dnsob.qry(qtype='SOA', timeout=1)
        self.assertTrue(resp.answers)
        primary = resp.answers[0]['data'][0]
        self.assertEqual(primary, 'ns1.pairnic.com')
        resp = dnsob.qry(qtype='NS',server=primary,aa=1)
        nslist = [x['data'].lower() for x in resp.answers]
        nslist.sort()
        self.assertEqual(nslist, ['ns1.pairnic.com', 'ns2.pairnic.com'])

    # Test defaults with legacy DNS.req

    def testDnsRequestAD(self):
        # try with asking for strings, and asking for bytes
        dnsob = DNS.DnsRequest('example.org')

        ad_response = dnsob.req(qtype='A', timeout=1)
        self.assertTrue(ad_response.answers)
        # is the result vaguely ipv4 like?
        self.assertEqual(ad_response.answers[0]['data'].count('.'), 3)
        self.assertEqual(ad_response.answers[0]['data'],'93.184.215.14')

    def testDnsRequestAAAAD(self):
        dnsob = DNS.DnsRequest('example.org')
        
        # default is returning binary instead of text
        aaaad_response = dnsob.req(qtype='AAAA', timeout=1)
        self.assertTrue(aaaad_response.answers)
        # does the result look like a binary ipv6 address?
        self.assertEqual(len(aaaad_response.answers[0]['data']) , 16)
        for b in aaaad_response.answers[0]['data']:
            assertIsByte(b)
        self.assertEqual(aaaad_response.answers[0]['data'],b'&\x06(\x00\x02\x1f\xcb\x07h \x80\xda\xafk\x8b,')
        
    def testDnsRequestEmptyMXD(self):
        dnsob = DNS.DnsRequest('mail.kitterman.org')

        mx_empty_response = dnsob.req(qtype='MX', timeout=1)
        self.assertFalse(mx_empty_response.answers)

    def testDnsRequestMXD(self):
        dnsob = DNS.DnsRequest('ietf.org')
        mx_response = dnsob.req(qtype='MX', timeout=1)
        self.assertTrue(mx_response.answers[0])
        # is hard coding a remote address a good idea?
        # I think it's unavoidable. - sk
        self.assertEqual(mx_response.answers[0]['data'], (0, 'mail.ietf.org'))

        m = DNS.mxlookup('ietf.org', timeout=1)
        self.assertEqual(mx_response.answers[0]['data'], m[0])

    def testDnsRequestSrvD(self):
        dnsob = DNS.Request(qtype='srv')
        respdef = dnsob.req('_ldap._tcp.openldap.org', timeout=1)
        self.assertTrue(respdef.answers)
        data = respdef.answers[0]['data']
        self.assertEqual(len(data), 4)
        self.assertEqual(data[2], 389)
        self.assertTrue('openldap.org' in data[3])

    def testDkimRequestD(self):
        q = '20161025._domainkey.google.com'
        dnsob = DNS.Request(q, qtype='txt')
        resp = dnsob.req(timeout=1)
        
        self.assertTrue(resp.answers)
        # should the result be bytes or a string? (Bytes, we finally settled on bytes)
        data = resp.answers[0]['data']
        self.assertFalse(isinstance(data[0], str))
        self.assertTrue(data[0].startswith(b'k=rsa'))

    def testDNSRequestTXTD(self):
        dnsob = DNS.DnsRequest('fail.kitterman.org')

        respdef = dnsob.req(qtype='TXT', timeout=1)
        self.assertTrue(respdef.answers)
        data = respdef.answers[0]['data']
        self.assertEqual(data, [b'v=spf1 -all'])

    def testIDND(self):
        """Can we lookup an internationalized domain name?"""
        dnsob = DNS.DnsRequest('xn--bb-eka.at')
        unidnsob = DNS.DnsRequest('öbb.at')
        a_resp = dnsob.req(qtype='A', resulttype='text', timeout=1)
        ua_resp = unidnsob.req(qtype='A', resulttype='text', timeout=1)
        self.assertTrue(a_resp.answers)
        self.assertTrue(ua_resp.answers)
        self.assertEqual(ua_resp.answers[0]['data'], 
                         a_resp.answers[0]['data'])

    def testNSD(self):
        """Lookup NS record from SOA"""
        dnsob = DNS.DnsRequest('kitterman.com')
        resp = dnsob.req(qtype='SOA', timeout=1)
        self.assertTrue(resp.answers)
        primary = resp.answers[0]['data'][0]
        self.assertEqual(primary, 'ns1.pairnic.com')
        resp = dnsob.req(qtype='NS',server=primary,aa=1, timeout=1)
        nslist = [x['data'].lower() for x in resp.answers]
        nslist.sort()
        self.assertEqual(nslist, ['ns1.pairnic.com', 'ns2.pairnic.com'])

def test_suite():
    from unittest import TestLoader
    return TestLoader().loadTestsFromName(__name__)

if __name__ == "__main__":
    unittest.main()
