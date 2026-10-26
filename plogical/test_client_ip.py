import hashlib
import hmac
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from plogical import clientIP
from install.proxy_identity import ensure_pma_peer_key


class ClientIPTests(unittest.TestCase):
    def request(self, remote='203.0.113.1', cf=None, **meta):
        meta['REMOTE_ADDR'] = remote
        if cf is not None:
            meta['HTTP_CF_CONNECTING_IP'] = cf
        return SimpleNamespace(META=meta, path='/base/', method='GET', body=b'', COOKIES={})

    def test_direct_peer_ignores_all_forwarded_headers(self):
        for address in ('203.0.113.1', '2001:db8::1', '::ffff:203.0.113.1'):
            request = self.request(address, '192.0.2.5', HTTP_X_FORWARDED_FOR='192.0.2.6', HTTP_X_CYBERPANEL_PEER='173.245.48.1')
            self.assertEqual('203.0.113.1' if '203.0.113.1' in address else address, clientIP.get_client_ip(request))

    def test_cloudflare_ipv4_and_ipv6_canonical_client(self):
        for peer in ('173.245.48.1', '2606:4700::1', '::ffff:173.245.48.1'):
            for client, expected in (('192.0.2.1', '192.0.2.1'), ('::ffff:192.0.2.1', '192.0.2.1'), ('2001:0DB8::1', '2001:db8::1')):
                self.assertEqual(expected, clientIP.get_client_ip(self.request(peer, client)))

    def test_invalid_trusted_header_cannot_bind_edge_address(self):
        for value in (None, '', 'not-ip', '192.0.2.1, 192.0.2.2', 'fe80::1%eth0', '192.0.2.1\r\nX: y'):
            self.assertIsNone(clientIP.get_client_ip(self.request('173.245.48.1', value)))

    def test_network_boundaries_do_not_widen_cloudflare_trust(self):
        for peer in ('173.245.47.255', '173.245.64.0', '2606:46ff::1', '2606:4701::1'):
            self.assertEqual(peer, clientIP.get_client_ip(self.request(peer, '192.0.2.2')))

    def test_invalid_socket_peer_cannot_use_headers(self):
        for peer in (None, '', 'bad', '::1%lo', '127.0.0.1,192.0.2.1'):
            self.assertIsNone(clientIP.get_client_ip(self.request(peer, '192.0.2.2')))

    def test_unsigned_loopback_proxy_headers_are_untrusted(self):
        for peer in ('127.0.0.1', '::1', '127.0.0.2'):
            request = self.request(peer, '192.0.2.2', HTTP_X_CYBERPANEL_PEER='173.245.48.1')
            request.path = '/dataBases/validatePHPMYAdminSession'
            request.method = 'POST'
            self.assertEqual(peer, clientIP.get_client_ip(request))

    def signed(self, key, peer='203.0.113.5', cf='', age=0):
        request = self.request('127.0.0.1', cf, HTTP_X_CYBERPANEL_PEER=peer)
        request.path = '/dataBases/validatePHPMYAdminSession'; request.method = 'POST'
        request.body = b'username=fixture&grant=synthetic'
        request.COOKIES = {'cyberpanel_sessionid': 'syntheticsession123456'}
        timestamp = str(int(time.time()) + age)
        request.META['HTTP_X_CYBERPANEL_PEER_TIME'] = timestamp
        message = '\n'.join(('pma-peer-v1', timestamp, request.method, request.path, request.COOKIES['cyberpanel_sessionid'], peer, cf, hashlib.sha256(request.body).hexdigest()))
        request.META['HTTP_X_CYBERPANEL_PEER_SIGNATURE'] = hmac.new(key, message.encode('ascii'), hashlib.sha256).hexdigest()
        return request

    def test_signed_pma_direct_and_cloudflare(self):
        with patch.object(clientIP, '_peer_key', return_value=b'a'*64):
            self.assertEqual('203.0.113.5', clientIP.get_client_ip(self.signed(b'a'*64)))
            self.assertEqual('192.0.2.2', clientIP.get_client_ip(self.signed(b'a'*64, '2606:4700::1', '192.0.2.2')))
            self.assertEqual('203.0.113.5', clientIP.get_client_ip(self.signed(b'a'*64, cf='192.0.2.2')))

    def test_signed_pma_cannot_be_repurposed(self):
        with patch.object(clientIP, '_peer_key', return_value=b'a'*64):
            for field, value in (('path','/base/'), ('method','GET'), ('body',b'username=someoneelse')):
                request = self.signed(b'a'*64); setattr(request, field, value)
                self.assertEqual('127.0.0.1', clientIP.get_client_ip(request))
            for name, value in (('HTTP_CF_CONNECTING_IP','192.0.2.9'), ('HTTP_X_CYBERPANEL_PEER','198.51.100.9'), ('HTTP_X_CYBERPANEL_PEER_SIGNATURE','f'*64)):
                request = self.signed(b'a'*64);request.META[name]=value
                self.assertEqual('127.0.0.1', clientIP.get_client_ip(request))
            request = self.signed(b'a'*64);request.COOKIES['cyberpanel_sessionid']='otherpanelsession1234'
            self.assertEqual('127.0.0.1', clientIP.get_client_ip(request))
            request = self.signed(b'a'*64);request.META['REMOTE_ADDR']='198.51.100.5'
            self.assertEqual('198.51.100.5', clientIP.get_client_ip(request))
            for age in (-31, 31):
                self.assertEqual('127.0.0.1', clientIP.get_client_ip(self.signed(b'a'*64, age=age)))

    def test_missing_key_fails_closed(self):
        with patch.object(clientIP, '_peer_key', return_value=None):
            self.assertEqual('127.0.0.1', clientIP.get_client_ip(self.signed(b'a'*64)))


@unittest.skipUnless(os.geteuid() == 0, 'native root ownership acceptance')
class PeerKeyTests(unittest.TestCase):
    def test_preservation_and_private_service_copies(self):
        with tempfile.TemporaryDirectory() as directory:
            a,b=Path(directory)/'panel',Path(directory)/'php'
            ensure_pma_peer_key(str(a),str(b),'root','root')
            value=a.read_bytes();self.assertEqual(value,b.read_bytes())
            self.assertEqual(64,len(value));self.assertEqual(0o640,a.stat().st_mode & 0o777)
            ensure_pma_peer_key(str(a),str(b),'root','root')
            self.assertEqual(value,a.read_bytes())
            with patch.object(clientIP,'PMA_PEER_KEY',str(a)):
                self.assertEqual(value,clientIP._peer_key())
                a.chmod(0o644);self.assertIsNone(clientIP._peer_key())
            with self.assertRaises(RuntimeError):ensure_pma_peer_key(str(a),str(b),'root','root')

    def test_bad_existing_key_never_rotates(self):
        with tempfile.TemporaryDirectory() as directory:
            a,b=Path(directory)/'panel',Path(directory)/'php'
            a.write_text('bad');a.chmod(0o600)
            with self.assertRaises(RuntimeError):ensure_pma_peer_key(str(a),str(b),'root','root')
            self.assertEqual('bad',a.read_text());self.assertFalse(b.exists())

    def test_mismatched_copies_and_symlinks_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            a,b=Path(directory)/'panel',Path(directory)/'php'
            ensure_pma_peer_key(str(a),str(b),'root','root')
            b.write_text('f'*64)
            with self.assertRaises(RuntimeError):ensure_pma_peer_key(str(a),str(b),'root','root')
            b.unlink();b.symlink_to(a)
            with self.assertRaises(OSError):ensure_pma_peer_key(str(a),str(b),'root','root')

    def test_real_php_signature_agrees_with_python(self):
        with tempfile.TemporaryDirectory() as directory:
            key=Path(directory)/'key';key.write_text('a'*64);key.chmod(0o640)
            root=Path(__file__).resolve().parents[1]
            php=r'''<?php
            define('PMA_SIGNON_LIBRARY_ONLY', true);
            define('PMA_PEER_KEY_PATH', $argv[1]);
            foreach (array('CURLOPT_POST','CURLOPT_POSTFIELDS','CURLOPT_COOKIE','CURLOPT_HTTPHEADER','CURLOPT_RETURNTRANSFER','CURLOPT_FOLLOWLOCATION','CURLOPT_CONNECTTIMEOUT','CURLOPT_TIMEOUT','CURLOPT_SSL_VERIFYPEER','CURLOPT_SSL_VERIFYHOST','CURLINFO_RESPONSE_CODE') as $i=>$v) define($v,$i+1);
            function curl_init($u) { return true; }
            function curl_setopt_array($r,$o) { $GLOBALS['options']=$o; }
            function curl_exec($r) {return '{"status":1}';}
            function curl_getinfo($r,$o) {return 200;}
            require $argv[2];
            $_COOKIE['cyberpanel_sessionid']='syntheticsession123456';
            $_SERVER['REMOTE_ADDR']='2606:4700::1';
            $_SERVER['HTTP_CF_CONNECTING_IP']='192.0.2.7';
            requestPMAPanel('https://127.0.0.1:8090/dataBases/validatePHPMYAdminSession',array('username'=>'fixture','grant'=>'abc'));
            echo json_encode($GLOBALS['options']);
            '''
            script=Path(directory)/'fixture.php';script.write_text(php)
            result=subprocess.check_output([os.environ.get('PHP_TEST_BIN','php'),'-n',str(script),str(key),str(root/'plogical/phpmyadminsignin.php')],text=True)
            options=json.loads(result);headers=dict(h.split(': ',1) for h in options['4'])
            request=ClientIPTests().request('127.0.0.1')
            request.path='/dataBases/validatePHPMYAdminSession';request.method='POST';request.body=options['2'].encode()
            request.COOKIES={'cyberpanel_sessionid':'syntheticsession123456'}
            request.META.update({'HTTP_'+k.upper().replace('-','_'):v for k,v in headers.items()})
            with patch.object(clientIP,'PMA_PEER_KEY',str(key)):
                self.assertEqual('192.0.2.7',clientIP.get_client_ip(request))


if __name__ == '__main__':unittest.main()
