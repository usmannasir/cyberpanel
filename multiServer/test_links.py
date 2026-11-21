"""A controller's record of a managed server: sealed to its row, re-checked when opened, and silent about its keys.

Everything here runs without Django or a database. The rows themselves, and
hello() against a server standing in for a node, are in
multiServer/test_links_database.py.
"""
import ast
import base64
import copy
import json
from pathlib import Path
import pickle
import socket
import sys
import traceback
import types
import unittest
from unittest import mock

from cryptography.fernet import Fernet

from multiServer import audit, crypto, entitlement, keys, links, schema, transport
from multiServer import test_transport

MASTER = base64.urlsafe_b64encode(b'm' * 32)
OTHER_MASTER = base64.urlsafe_b64encode(b'o' * 32)
LINK, OTHER_LINK = 'a1' * 16, 'b2' * 16
PRIVATE = b'controller-private-key-material!'
NODE_KEY = crypto.public_key(b'n' * 32)
NODE_ID = crypto.node_id(NODE_KEY)
OTHER_NODE_KEY = crypto.public_key(b'o' * 32)
PIN = 'd4' * 32
HOST = '93.184.216.34'
LONGEST_HOST = 'a' * 63 + '.' + 'b' * 63 + '.' + 'c' * 63 + '.' + 'd' * 61
ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'


def record(**changes):
    fields = dict(node_id=NODE_ID, host=HOST, port=8090, node_key=NODE_KEY, private_key=PRIVATE, tls_pin=PIN)
    fields.update(changes)
    return links.Record(**fields)


def plain(*extra, **changes):
    """The lines that are sealed for LINK, with any of them changed or more of them added."""
    names = ('type', 'link_id', 'node_id', 'host', 'port', 'node_key', 'private_key', 'tls_pin')
    fields = dict(type=links.RECORD, link_id=LINK, node_id=NODE_ID, host=HOST, port='8090',
                  node_key=NODE_KEY.hex(), private_key=PRIVATE.hex(), tls_pin=PIN)
    fields.update(changes)
    return '\n'.join([fields[name] for name in names] + list(extra))


def sealed_as_is(text, key=MASTER):
    """Whatever `text` is, sealed with the master key: what only the holder of that key could produce."""
    data = text if isinstance(text, bytes) else text.encode('utf-8')
    return Fernet(key).encrypt(data).decode('ascii')


class Sealing(unittest.TestCase):
    SECRETS = (PRIVATE.decode(), PRIVATE.hex(), base64.b64encode(PRIVATE).decode(), NODE_KEY.hex(), PIN,
               MASTER.decode(), OTHER_MASTER.decode(), 'm' * 32)

    def refused(self, error, call, *arguments, **named):
        """The call ends in exactly this error, and the error shows no key, pin, master key or sealed text."""
        with self.assertRaises((links.LinkError, transport.TransportError)) as caught:
            call(*arguments, **named)
        self.assertIs(error, type(caught.exception), repr(caught.exception))
        texts = [text for text in arguments if isinstance(text, str) and len(text) > 40]
        self.assert_no_secret(caught.exception, *texts)
        return caught.exception

    def assert_no_secret(self, error, *more):
        shown = [''.join(traceback.format_exception(type(error), error, error.__traceback__))]
        while error is not None:
            shown += [str(error), repr(error), repr(error.args)]
            error = error.__cause__ or error.__context__
        for secret in self.SECRETS + more:
            self.assertNotIn(secret, '\n'.join(shown))


class RecordTests(Sealing):
    def test_a_record_holds_exactly_what_it_was_built_from(self):
        built = record()
        self.assertEqual((NODE_ID, HOST, 8090, NODE_KEY, PRIVATE, PIN),
                         tuple(getattr(built, name) for name in links.Record.__slots__))
        for host in ('node-1.example.com', 'xn--80ak6aa92e.com', '1.1.1.1', '2a01:4f8::1', LONGEST_HOST):
            self.assertEqual(host, record(host=host).host)
        for port in (1, 65535):
            self.assertEqual(port, record(port=port).port)

    def test_what_the_transport_would_not_connect_with_is_not_a_record(self):
        refused = (
            dict(node_id=crypto.node_id(OTHER_NODE_KEY)), dict(node_id=NODE_ID.upper()), dict(node_id=NODE_ID[:-2]),
            dict(node_id=None), dict(node_key=OTHER_NODE_KEY), dict(node_key=NODE_KEY[:31]),
            dict(node_key=NODE_KEY.hex()), dict(node_key=None),
            dict(private_key=PRIVATE[:31]), dict(private_key=PRIVATE + b'!'), dict(private_key=PRIVATE.hex()),
            dict(private_key=bytearray(PRIVATE)), dict(private_key=None),
            dict(tls_pin=PIN.upper()), dict(tls_pin=PIN[:-2]), dict(tls_pin=PIN + '\n'), dict(tls_pin=b'\xd4' * 32),
            dict(tls_pin=None),
            dict(port=0), dict(port=65536), dict(port=-1), dict(port='8090'), dict(port=8090.0), dict(port=True),
            dict(port=None),
            dict(host=''), dict(host='localhost'), dict(host='node'), dict(host='Node-1.example.com'),
            dict(host='node_1.example.com'), dict(host='node-1.example.com.'), dict(host='node-1.example.com:8090'),
            dict(host='node-1.example.com\n'), dict(host='a' + LONGEST_HOST), dict(host=b'node-1.example.com'),
            dict(host=None), dict(host='127.1'), dict(host='2130706433'), dict(host='0x7f000001'),
            dict(host='010.0.0.1'), dict(host='1.1.1.1 '), dict(host='[2a01:4f8::1]'), dict(host='2A01:4F8::1'),
            dict(host='2a01:4f8:0:0:0:0:0:1'), dict(host='2a01:4f8::1%eth0'),
        )
        with mock.patch.object(socket, 'getaddrinfo') as lookup, mock.patch.object(socket, 'socket') as made:
            for change in refused:
                with self.subTest(change=repr(change)[:60]):
                    self.refused(links.InvalidRecord, record, **change)
            lookup.assert_not_called()
            made.assert_not_called()

    def test_an_address_a_link_may_not_connect_to_is_refused_by_its_kind(self):
        for address, kind in test_transport.AddressRuleTests.REFUSED:
            error = self.refused(transport.RefusedAddress, record, host=address)
            self.assertEqual('A link may not connect to this address (%s).' % kind, str(error), address)

    def test_a_record_cannot_be_changed_printed_with_its_secrets_or_stored_unsealed(self):
        built = record()
        for name in links.Record.__slots__ + ('other',):
            with self.assertRaises(AttributeError):
                setattr(built, name, getattr(built, name, None))
            with self.assertRaises(AttributeError):
                delattr(built, name)
        self.assertFalse(hasattr(built, '__dict__'))
        self.assertEqual(PRIVATE, built.private_key)
        for text in (repr(built), str(built), '%s' % [built], '%r' % (built,)):
            self.assertEqual('Record(%s port 8090)' % HOST, text.strip('[]'))
        for store in (pickle.dumps, copy.copy, copy.deepcopy):
            with self.assertRaises(TypeError):
                store(built)


class SealTests(Sealing):
    def assert_same(self, expected, opened):
        self.assertIs(links.Record, type(opened))
        for name in links.Record.__slots__:
            self.assertEqual(getattr(expected, name), getattr(opened, name), name)

    def test_a_sealed_record_opens_in_its_own_row_with_the_same_key(self):
        for host, port in ((HOST, 8090), ('2a01:4f8::1', 1), ('node-1.example.com', 65535), (LONGEST_HOST, 443)):
            original = record(host=host, port=port)
            text = links.seal(LINK, original, MASTER)
            self.assertIs(str, type(text))
            self.assert_same(original, links.unseal(LINK, text, MASTER))

    def test_the_longest_record_fits_the_column_with_room_to_spare(self):
        column = dict(dict((table.name, table) for table in schema.TABLES)['ms_nodes'].columns)['sealed']
        self.assertEqual('varchar(2048) NOT NULL', column)
        longest = links.seal(LINK, record(host=LONGEST_HOST, port=65535), MASTER)
        self.assertEqual(253, len(LONGEST_HOST))
        self.assertEqual((844, 844), (len(longest), links.MAX_SEALED))
        with self.assertRaises(links.InvalidRecord):
            record(host='a' + LONGEST_HOST)
        # No host makes it longer: a name of every length a name can have, and the longest address.
        lengths = []
        for length in range(3, 254):
            name = ''
            while length - len(name) - 2 > 63:
                name += 'a' * (62 if length - len(name) - 2 == 64 else 63) + '.'
            name += 'a' * (length - len(name) - 2) + '.a'
            self.assertEqual(length, len(name))
            lengths.append(len(links.seal(LINK, record(host=name, port=65535), MASTER)))
        self.assertEqual(sorted(lengths), lengths)
        self.assertEqual((504, 844), (lengths[0], lengths[-1]))
        self.assertLess(len(links.seal(LINK, record(host='2a01:4f8:ffff:ffff:ffff:ffff:ffff:ffff'), MASTER)), 844)

    def test_the_sealed_text_shows_nothing_of_the_record_and_is_new_each_time(self):
        original = record(host='node-1.example.com')
        first, second = links.seal(LINK, original, MASTER), links.seal(LINK, original, MASTER)
        self.assertNotEqual(first, second)
        for text in (first, second):
            self.assertRegex(text, r'\AgAAAAA[A-Za-z0-9_-]+={0,2}\Z')
            raw = base64.urlsafe_b64decode(text)
            for shown in (b'node-1.example.com', LINK.encode(), NODE_ID.encode(), PRIVATE, PRIVATE.hex().encode(),
                          NODE_KEY, NODE_KEY.hex().encode(), PIN.encode(), links.RECORD.encode()):
                self.assertNotIn(shown, raw)
            self.assert_same(original, links.unseal(LINK, text, MASTER))

    def test_a_text_moved_to_another_row_is_refused(self):
        text = links.seal(LINK, record(), MASTER)
        self.refused(links.MovedRecord, links.unseal, OTHER_LINK, text, MASTER)
        for row in (LINK.upper(), LINK[:-1], LINK + '0', '', None, 0, LINK.encode(), [LINK]):
            self.refused(links.MovedRecord, links.unseal, row, text, MASTER)
        # Two rows that swap their texts: neither opens.
        other = links.seal(OTHER_LINK, record(), MASTER)
        self.refused(links.MovedRecord, links.unseal, LINK, other, MASTER)
        self.assertEqual(HOST, links.unseal(OTHER_LINK, other, MASTER).host)

    def test_a_text_cut_short_anywhere_is_refused(self):
        text = links.seal(LINK, record(), MASTER)
        for length in range(len(text)):
            self.refused(links.NotSealed, links.unseal, LINK, text[:length], MASTER)

    def test_a_text_with_any_one_character_changed_is_refused(self):
        for host in (HOST, 'node-1.exampleexampleexample.com'):
            text = links.seal(LINK, record(host=host), MASTER)
            for position, character in enumerate(text):
                if character == '=':
                    changed = 'A'
                else:
                    changed = ALPHABET[(ALPHABET.index(character) + 1) % 64]
                self.refused(links.NotSealed, links.unseal, LINK, text[:position] + changed + text[position + 1:],
                             MASTER)
        # The second host was chosen so that the token ends in padding, which is checked as well.
        self.assertTrue(text.endswith('=='))

    def test_another_spelling_of_the_same_token_is_refused(self):
        text = links.seal(LINK, record(host='node-1.exampleexampleexample.com'), MASTER)
        self.assertTrue(text.endswith('=='))
        last = ALPHABET.index(text[-3])
        # The last character before the padding carries four bits that decode to nothing.
        respelled = text[:-3] + ALPHABET[last ^ 1] + '=='
        self.assertEqual(base64.urlsafe_b64decode(text), base64.urlsafe_b64decode(respelled))
        standard = base64.b64encode(base64.urlsafe_b64decode(text)).decode('ascii')
        self.assertNotEqual(text, standard)
        for other in (respelled, text[:-2], text[:-1], text + '=', text + '\n', '\n' + text, ' ' + text, text + ' ',
                      text[:76] + '\n' + text[76:], text[:10] + ' ' + text[10:], text[:10] + '!' + text[10:],
                      standard, text + text, text + 'AAAA', 'AAAA' + text,
                      text.encode('ascii'), bytearray(text.encode('ascii')), [text], None, 0, '', '=', '====',
                      'gAAAAA', 'A' * 844, 'A' * 845, text + 'A' * (845 - len(text))):
            self.refused(links.NotSealed, links.unseal, LINK, other, MASTER)
        self.assertEqual('node-1.exampleexampleexample.com', links.unseal(LINK, text, MASTER).host)

    def test_a_longer_text_than_any_record_gives_is_refused_unread(self):
        oversized = sealed_as_is(plain() + '\n' + 'f' * 600)
        self.assertGreater(len(oversized), links.MAX_SEALED)
        with mock.patch.object(Fernet, 'decrypt') as decrypt:
            self.refused(links.NotSealed, links.unseal, LINK, oversized, MASTER)
            decrypt.assert_not_called()

    def test_a_text_sealed_with_another_master_key_is_refused(self):
        text = links.seal(LINK, record(), OTHER_MASTER)
        self.refused(links.NotSealed, links.unseal, LINK, text, MASTER)
        self.assertEqual(HOST, links.unseal(LINK, text, OTHER_MASTER).host)

    def test_without_a_usable_master_key_nothing_is_sealed_or_opened(self):
        text = links.seal(LINK, record(), MASTER)
        for key in (None, b'', b'short', MASTER[:-4], MASTER + b'AAAA', MASTER + b'\n', b' ' + MASTER,
                    MASTER[:-1], MASTER[:-1] + b'A', MASTER.replace(b'b', b'+'), MASTER.decode(), bytearray(MASTER),
                    b'm' * 32, [MASTER], 0):
            self.refused(links.NoMasterKey, links.seal, LINK, record(), key)
            self.refused(links.NoMasterKey, links.unseal, LINK, text, key)

    def test_only_a_checked_record_and_a_real_row_are_sealed(self):
        built = record()
        link = transport.Link(LINK, NODE_ID, HOST, 8090, NODE_KEY, PRIVATE, PIN)
        imitation = types.SimpleNamespace(node_id=NODE_ID, host='127.0.0.1', port=8090, node_key=NODE_KEY,
                                          private_key=PRIVATE, tls_pin=PIN)
        with mock.patch.object(Fernet, 'encrypt') as encrypt:
            for other in (None, link, imitation, tuple(getattr(built, name) for name in links.Record.__slots__),
                          dict(host=HOST), links.Record):
                self.refused(links.InvalidRecord, links.seal, LINK, other, MASTER)
            for row in (LINK.upper(), LINK[:-1], LINK + '0', LINK + '\n', '', None, 0, LINK.encode()):
                self.refused(links.InvalidRecord, links.seal, row, built, MASTER)
            encrypt.assert_not_called()

    def test_a_record_with_a_field_out_of_its_pattern_is_refused_after_decryption(self):
        """Sealed with the right key and for the right row, so only the checks on what was opened stand in the way."""
        self.assertEqual(HOST, links.unseal(LINK, sealed_as_is(plain()), MASTER).host)
        out_of_pattern = (
            dict(type='CPMS1-REQ'), dict(type='cpms1-node'), dict(type=''),
            dict(link_id=LINK.upper()), dict(link_id=LINK[:-2]), dict(link_id=''),
            dict(node_id=crypto.node_id(OTHER_NODE_KEY)), dict(node_id=NODE_ID.upper()), dict(node_id=NODE_ID[:-2]),
            dict(node_key=OTHER_NODE_KEY.hex()), dict(node_key=NODE_KEY.hex().upper()),
            dict(node_key=NODE_KEY.hex()[:-2]), dict(node_key=NODE_KEY.hex() + '00'),
            dict(private_key=PRIVATE.hex().upper()), dict(private_key=PRIVATE.hex()[:-2]),
            dict(private_key=PRIVATE.hex() + '00'), dict(private_key=PRIVATE.decode()),
            dict(tls_pin=PIN.upper()), dict(tls_pin=PIN[:-2]), dict(tls_pin=PIN + 'd4'), dict(tls_pin=''),
            dict(port='0'), dict(port='08090'), dict(port='65536'), dict(port='70000'), dict(port='99999'),
            dict(port='100000'), dict(port='-1'), dict(port='8090 '), dict(port='+8090'), dict(port='80.90'),
            dict(port=''), dict(port='\u0668\u0660\u0669\u0660'),
            dict(host='10.0.0.5'), dict(host='127.0.0.1'), dict(host='169.254.169.254'), dict(host='192.168.1.9'),
            dict(host='0.0.0.0'), dict(host='::1'), dict(host='fd00::1'), dict(host='::ffff:8.8.8.8'),
            dict(host='localhost'), dict(host='node'), dict(host='Node-1.example.com'), dict(host='2A01:4F8::1'),
            dict(host='2a01:04f8::1'), dict(host='127.1'), dict(host='2130706433'), dict(host='010.0.0.1'),
            dict(host='1.2.3'), dict(host='node-1.example.com.'), dict(host='node-1.example.com:8090'),
            dict(host='node_1.example.com'), dict(host=' ' + HOST), dict(host=''), dict(host='a' + LONGEST_HOST),
            dict(host='n\xf6de.example.com'),
        )
        for change in out_of_pattern:
            with self.subTest(**change):
                self.refused(links.InvalidRecord, links.unseal, LINK, sealed_as_is(plain(**change)), MASTER)
        other_shapes = (
            plain() + '\n', '\n' + plain(), plain().replace('\n', '\r\n'), plain('true'), plain(''),
            plain('loopback'), '\n'.join(plain().split('\n')[:-1]), '\n'.join(plain().split('\n')[1:]),
            plain().replace('\n', ' '), plain().upper(), plain() + '\x00', '\ufeff' + plain(), '',
            json.dumps(dict(link_id=LINK, host=HOST, port=8090)), plain().encode('ascii') + b'\xff',
            links.RECORD.encode('utf-16'),
        )
        for number, text in enumerate(other_shapes):
            with self.subTest(shape=number):
                self.refused(links.InvalidRecord, links.unseal, LINK, sealed_as_is(text), MASTER)

    def test_a_record_for_another_row_is_refused_whatever_else_it_holds(self):
        self.refused(links.MovedRecord, links.unseal, LINK, sealed_as_is(plain(link_id=OTHER_LINK)), MASTER)
        self.refused(links.MovedRecord, links.unseal, LINK,
                     sealed_as_is(plain(link_id=OTHER_LINK, host='10.0.0.5')), MASTER)

    def test_the_search_for_secrets_would_find_one(self):
        text = links.seal(LINK, record(), MASTER)
        for secret in self.SECRETS + (text,):
            with self.assertRaises(AssertionError):
                self.assert_no_secret(links.LinkError('Refused: %s.' % secret), text)
            try:
                try:
                    raise ValueError(secret)
                except ValueError:
                    raise links.LinkError('Refused.')
            except links.LinkError as error:
                with self.assertRaises(AssertionError):
                    self.assert_no_secret(error, text)


class LinkOfTests(Sealing):
    def row(self, link_id=LINK, **changes):
        return types.SimpleNamespace(link_id=link_id, sealed=links.seal(link_id, record(**changes), MASTER),
                                     status='paused')

    def test_a_row_gives_the_link_the_transport_sends_on(self):
        link = links.link_of(self.row(host='node-1.example.com'), MASTER)
        self.assertIs(transport.Link, type(link))
        self.assertEqual((LINK, NODE_ID, 'node-1.example.com', 8090, 'node-1.example.com:8090', NODE_KEY, PRIVATE,
                          PIN), tuple(getattr(link, name) for name in transport.Link.__slots__[:-1]))

    def test_the_master_key_comes_from_the_key_directory_unless_one_is_given(self):
        with mock.patch.object(keys, 'master_key', return_value=MASTER) as read:
            self.assertEqual(HOST, links.link_of(self.row()).host)
            read.assert_called_once_with()
            self.assertEqual(HOST, links.link_of(self.row(), MASTER).host)
            read.assert_called_once_with()
        with mock.patch.object(keys, 'master_key', return_value=None):
            self.refused(links.NoMasterKey, links.link_of, self.row())
        with mock.patch.object(keys, 'master_key', return_value=OTHER_MASTER):
            self.refused(links.NotSealed, links.link_of, self.row())

    def test_a_row_holding_another_rows_text_gives_no_link(self):
        row, other = self.row(), self.row(OTHER_LINK, host='node-1.example.com')
        row.sealed, other.sealed = other.sealed, row.sealed
        self.refused(links.MovedRecord, links.link_of, row, MASTER)
        self.refused(links.MovedRecord, links.link_of, other, MASTER)

    def test_no_stored_link_is_ever_allowed_to_lead_to_this_machine(self):
        """The transport's allowance for its own tests is a word this module does not contain."""
        source = Path(links.__file__).read_text()
        self.assertNotIn('loopback_for_tests', source)
        self.assertNotIn('LOOPBACK', source)
        # A link is described in one place, from seven plain values and nothing more.
        tree = ast.parse(source)
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Attribute) and node.func.attr == 'Link']
        self.assertEqual([(7, [], [])], [(len(call.args), call.keywords, [
            argument for argument in call.args if isinstance(argument, ast.Starred)]) for call in calls])
        # Nothing else names the class, so nothing else can build one or hand it on under another name.
        named = [node for node in ast.walk(tree) if isinstance(node, ast.Attribute) and node.attr == 'Link']
        self.assertEqual([calls[0].func], named)
        self.assertEqual([], [node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and node.id == 'Link'])
        self.assertIs(False, links.link_of(self.row(), MASTER).allow_loopback_for_tests)
        for field in ('true', 'True', '1', 'loopback', 'allow_loopback_for_tests'):
            self.refused(links.InvalidRecord, links.link_of,
                         types.SimpleNamespace(link_id=LINK, sealed=sealed_as_is(plain(field))), MASTER)
        for host in ('127.0.0.1', '127.0.0.2', '::1'):
            self.refused(links.InvalidRecord, links.link_of,
                         types.SimpleNamespace(link_id=LINK, sealed=sealed_as_is(plain(host=host))), MASTER)


class LabelTests(unittest.TestCase):
    def test_a_label_is_short_plain_text(self):
        for label in ('Frankfurt 1', 'a', '7', 'node-1.example.com', 'db_primary', 'A' * 64, 'a b  c', 'x.y-z_0'):
            self.assertEqual(label, links.check_label(label))

    def test_anything_a_page_could_read_as_more_than_text_is_refused(self):
        for label in ('', ' ', ' a', 'a ', 'a\n', 'a\tb', 'a\nb', 'A' * 65, '-a', 'a-', '.a', '_a', 'a.',
                      '<b>a</b>', 'a<script>', '{{7*7}}', '{$ 7*7 $}', 'a{b', 'a}b', 'a&amp;b', 'a"b', "a'b", 'a`b',
                      'a/b', 'a\\b', 'a;b', 'a:b', 'a=b', 'a(b)', 'a%41', 'a\x00b', 'a\u202eb', 'Fr\xe4nkfurt',
                      '\uff21', b'Frankfurt', None, 7, ['a'], ('a',)):
            with self.assertRaises(links.InvalidLabel, msg=repr(label)):
                links.check_label(label)


class AnswerTests(unittest.TestCase):
    """What hello() makes of a reply once the transport has verified who sent it."""
    JSON = 'application/json'

    def answer(self, *pairs, **changes):
        fields = dict(version='3.0', build=10, role='node', capabilities=['hello', 'inventory'])
        fields.update(changes)
        return json.dumps(dict(list(fields.items()) + list(pairs)), sort_keys=True, separators=(',', ':')).encode()

    def test_the_reply_a_node_gives_is_read_as_its_version_and_capabilities(self):
        self.assertEqual(b'{"build":10,"capabilities":["hello","inventory"],"role":"node","version":"3.0"}',
                         self.answer())
        self.assertEqual(('3.0.10', ('hello', 'inventory')), links._answer(self.JSON, self.answer()))
        self.assertEqual(('2.4.0', ()), links._answer(self.JSON, self.answer(
            version='2.4', build=0, capabilities=[])))
        self.assertEqual(('999.999.9999', tuple('c%d' % number for number in range(16))), links._answer(
            self.JSON, self.answer(version='999.999', build=9999,
                                   capabilities=['c%d' % number for number in range(16)])))
        spaced = b' {\n "role": "node", "version": "3.0",\t"build": 10, "capabilities": ["a_1", "' \
                 + b'a' * 24 + b'"] }\r\n'
        self.assertEqual(('3.0.10', ('a_1', 'a' * 24)), links._answer(self.JSON, spaced))

    def test_every_kept_value_is_digits_dots_lower_case_letters_and_underscores(self):
        version, capabilities = links._answer(self.JSON, self.answer())
        for kept in (version,) + capabilities:
            self.assertRegex(kept, r'\A[a-z0-9._]{1,32}\Z')
        self.assertLessEqual(len('999.999.9999'), 32)

    def test_a_reply_of_any_other_shape_is_not_an_answer(self):
        not_answers = dict(
            missing_version=b'{"build":10,"capabilities":[],"role":"node"}',
            missing_build=b'{"capabilities":[],"role":"node","version":"3.0"}',
            missing_role=b'{"build":10,"capabilities":[],"version":"3.0"}',
            missing_capabilities=b'{"build":10,"role":"node","version":"3.0"}',
            an_extra_name=self.answer(('hostname', 'node-1.example.com')),
            an_extra_empty_name=self.answer(('', 1)),
            a_name_in_another_case=self.answer().replace(b'"role"', b'"Role"'),
            a_name_twice=self.answer().replace(b'"role":"node"', b'"role":"node","role":"node"'),
            a_name_twice_with_an_escape=self.answer().replace(b'"role":"node"', b'"role":"x","rol\\u0065":"node"'),
            a_list=b'[' + self.answer() + b']', a_list_of_values=b'["3.0",10,"node",[]]', a_string=b'"node"',
            a_number=b'10', null=b'null', true=b'true', an_empty_object=b'{}', nothing=b'', a_space=b' ',
            two_objects=self.answer() + self.answer(), an_object_and_more=self.answer() + b'x',
            a_byte_order_mark=b'\xef\xbb\xbf' + self.answer(), a_byte_above_ascii=self.answer() + b'\xc2\xa0',
            utf_16=self.answer().decode().encode('utf-16'), a_zero_byte=self.answer() + b'\x00',
            html=b'<!DOCTYPE html><html><body>CyberPanel</body></html>',
            text=b'This request need session.', python=b"{'build': 10}", a_comment=b'/**/' + self.answer(),
            a_trailing_comma=self.answer()[:-1] + b',}', single_quotes=self.answer().replace(b'"', b"'"),
            nested_too_deep=b'[' * 1000, nested_objects=b'{"a":' * 200 + b'1' + b'}' * 200,
            not_a_number=self.answer().replace(b'10', b'NaN'), infinity=self.answer().replace(b'10', b'Infinity'),
            role_controller=self.answer(role='controller'), role_off=self.answer(role='off'),
            role_in_upper_case=self.answer(role='Node'), role_spaced=self.answer(role='node '),
            role_empty=self.answer(role=''), role_null=self.answer(role=None), role_true=self.answer(role=True),
            role_list=self.answer(role=['node']), role_number=self.answer(role=1),
            version_with_build=self.answer(version='3.0.10'), version_one_part=self.answer(version='3'),
            version_markup=self.answer(version='3.0<script>alert(1)</script>'),
            version_template=self.answer(version='{{7*7}}'), version_panel_template=self.answer(version='{$ 7*7 $}'),
            version_escaped_markup=self.answer().replace(b'"3.0"', b'"3.0\\u003cb\\u003e"'),
            version_leading_zero=self.answer(version='03.0'), version_minor_zero=self.answer(version='3.00'),
            version_four_digits=self.answer(version='1000.0'), version_spaced=self.answer(version=' 3.0'),
            version_line=self.answer(version='3.0\n'), version_letter=self.answer(version='3.0b'),
            version_empty=self.answer(version=''), version_number=self.answer(version=3.0),
            version_null=self.answer(version=None), version_list=self.answer(version=['3.0']),
            version_other_digits=self.answer(version='\u0663.\u0660'),
            version_long=self.answer(version='3.' + '0' * 40),
            build_text=self.answer(build='10'), build_fraction=self.answer(build=10.0),
            build_exponent=self.answer().replace(b'10', b'1e1'), build_negative=self.answer(build=-1),
            build_too_large=self.answer(build=10000), build_huge=self.answer().replace(b'10', b'1' + b'0' * 300),
            build_true=self.answer(build=True), build_null=self.answer(build=None), build_list=self.answer(build=[10]),
            capabilities_text=self.answer(capabilities='hello'), capabilities_object=self.answer(capabilities={}),
            capabilities_null=self.answer(capabilities=None), capabilities_number=self.answer(capabilities=1),
            capabilities_seventeen=self.answer(capabilities=['c%d' % number for number in range(17)]),
            capability_twice=self.answer(capabilities=['hello', 'hello']),
            capability_in_upper_case=self.answer(capabilities=['Hello']),
            capability_markup=self.answer(capabilities=['<img src=x onerror=alert(1)>']),
            capability_template=self.answer(capabilities=['{{constructor}}']),
            capability_spaced=self.answer(capabilities=['hello world']),
            capability_dashed=self.answer(capabilities=['one-click']),
            capability_leading_digit=self.answer(capabilities=['1hello']),
            capability_leading_underscore=self.answer(capabilities=['_hello']),
            capability_empty=self.answer(capabilities=['']), capability_long=self.answer(capabilities=['a' * 25]),
            capability_number=self.answer(capabilities=[1]), capability_null=self.answer(capabilities=[None]),
            capability_list=self.answer(capabilities=[['hello']]),
            capability_object=self.answer(capabilities=[{'name': 'hello'}]),
            capability_other_letters=self.answer(capabilities=['h\xe9llo']),
        )
        for name, body in sorted(not_answers.items()):
            with self.subTest(name):
                self.assertIsNone(links._answer(self.JSON, body))

    def test_a_reply_that_is_not_called_json_is_not_an_answer(self):
        for content_type in ('text/html', 'text/plain', 'text/json', 'application/javascript', '-', '', None,
                             'application/json; charset=utf-8', 'Application/JSON', b'application/json'):
            self.assertIsNone(links._answer(content_type, self.answer()), content_type)

    def test_a_body_that_is_not_bytes_is_not_an_answer(self):
        for body in (None, self.answer().decode(), dict(role='node'), 10, [self.answer()]):
            self.assertIsNone(links._answer(self.JSON, body))

    def test_the_largest_true_answer_is_within_the_size_a_reply_may_have(self):
        largest = self.answer(version='999.999', build=9999, capabilities=[
            chr(97 + number) * 24 for number in range(16)])
        self.assertIsNotNone(links._answer(self.JSON, largest))
        self.assertLess(len(largest), links.MAX_HELLO)
        self.assertEqual((1024, 16, 9999), (links.MAX_HELLO, links.MAX_CAPABILITIES, links.MAX_BUILD))


class FixedTextTests(unittest.TestCase):
    """What a failed hello() leaves on a row is chosen here, never written by a node or an exception."""

    def errors(self):
        return [value for value in vars(transport).values()
                if isinstance(value, type) and issubclass(value, transport.TransportError)]

    def test_every_refusal_of_the_transport_has_a_text_of_its_own_kind(self):
        named = [kind for kind, _, _ in links._FAILURES]
        self.assertEqual(sorted(set(self.errors()) - {transport.TransportError}, key=lambda kind: kind.__name__),
                         sorted(named, key=lambda kind: kind.__name__))
        for number, kind in enumerate(named):
            for earlier in named[:number]:
                self.assertFalse(issubclass(kind, earlier), '%s hides %s' % (earlier.__name__, kind.__name__))
        expected = {
            transport.TimedOut: 'timeout', transport.ConnectionFailed: 'unreachable',
            transport.CertificateMismatch: 'certificate', transport.RefusedAddress: 'not_allowed',
            transport.RedirectRefused: 'format', transport.ResponseTooLarge: 'size',
            transport.MalformedResponse: 'format', transport.BadSignature: 'signature',
            transport.InvalidRequest: 'format', transport.InvalidLink: 'internal'}
        for kind in self.errors():
            if kind is transport.TransportError:
                continue
            reason, text = links._failure(kind('reply-body-secret <script>'))
            self.assertEqual(expected[kind], reason)
            self.assertEqual([text], [entry[2] for entry in links._FAILURES if entry[0] is kind])

    def test_an_error_of_no_known_kind_gets_the_general_text(self):
        for error in (transport.TransportError('reply-body-secret'), RuntimeError('reply-body-secret'),
                      KeyError('x'), None):
            self.assertEqual(('internal', links.FAILED), links._failure(error))

    def test_the_text_of_an_error_is_never_taken_from_the_error(self):
        marker = 'node-supplied <script>alert(1)</script> {{7*7}}'
        for kind in self.errors():
            self.assertNotIn(marker, links._failure(kind(marker))[1])
            self.assertIn(links._failure(kind(marker))[1], links.STORED_ERRORS + (links.FAILED,))

    def test_every_text_is_plain_fits_its_column_and_has_no_varying_part(self):
        shown = links.STORED_ERRORS + (links.NOT_CONTROLLER, links.NO_LICENCE, links.NO_SUCH_SERVER,
                                       links.NOT_ACTIVE)
        self.assertEqual(len(shown), len(set(shown)))
        self.assertEqual(13, len(links.STORED_ERRORS))
        for text in shown:
            self.assertRegex(text, r'\A[A-Z][A-Za-z ,-]+\.(?: [A-Z][A-Za-z ,-]+\.)?\Z')
            self.assertLessEqual(len(text), 255)
            self.assertNotIn('%', text)
        for text in (links.UNREADABLE, links.REFUSED, links.TOO_LARGE, links.NOT_A_NODE, links.FAILED):
            self.assertIn(text, links.STORED_ERRORS)

    def test_every_audited_event_and_reason_is_one_the_audit_trail_knows(self):
        source = Path(links.__file__).read_text()
        used_events = {'pairing', 'link_approve', 'link_pause', 'link_resume', 'node_remove', 'request'}
        used_reasons = {'role', 'licence', 'link', 'internal', 'not_allowed', 'size', 'format', 'timeout',
                        'unreachable', 'certificate', 'signature'}
        for word in used_events | used_reasons:
            self.assertIn("'%s'" % word, source)
        self.assertTrue(used_events <= set(audit.EVENTS) and used_reasons <= set(audit.REASONS))
        for _, reason, _ in links._FAILURES:
            self.assertIn(reason, used_reasons)
        for outcome, reason in links._STORE_REFUSALS.values():
            self.assertIn(outcome, audit.OUTCOMES)
            self.assertIn(reason, used_reasons)
        # Every row this module can write is accepted whole by the audit trail.
        for event in used_events:
            for reason in used_reasons:
                self.assertEqual(0, audit.entry(event, dict(
                    outcome='refused', reason=reason, link_id=LINK, actor='admin', method='GET',
                    path=links.HELLO_PATH, status=403, size=links.MAX_HELLO))['dropped'])


class RefusalWithoutSendingTests(unittest.TestCase):
    """hello() before it reaches a row: decided here, so nothing of it needs a database."""

    def setUp(self):
        self.audited = []
        for patcher in (mock.patch.object(audit, 'record', side_effect=self.note),
                        mock.patch.object(transport, 'send', side_effect=AssertionError('nothing may be sent')),
                        mock.patch.object(socket, 'socket', side_effect=AssertionError('nothing may be opened')),
                        mock.patch.object(links, '_note', side_effect=AssertionError('no row may be touched'))):
            patcher.start()
            self.addCleanup(patcher.stop)

    def note(self, event, **fields):
        self.audited.append((event, fields))
        return True

    def test_a_server_that_is_not_a_controller_asks_nobody(self):
        for role in (keys.OFF, keys.NODE):
            with mock.patch.object(links.switch, 'active_role', return_value=role), \
                    mock.patch.object(entitlement, 'allowed', return_value=True):
                self.assertEqual(links.Hello(False, links.NOT_CONTROLLER, '', ()), links.hello(LINK, 'admin'))
        self.assertEqual([('request', dict(outcome='refused', reason='role', link_id=LINK, actor='admin',
                                           method='GET', path='/multiserver/gateway/hello'))] * 2, self.audited)

    def test_a_controller_without_the_licence_asks_nobody(self):
        for answer in (False, None, 0, 1, 'yes'):
            with mock.patch.object(links.switch, 'active_role', return_value=keys.CONTROLLER), \
                    mock.patch.object(entitlement, 'allowed', return_value=answer):
                self.assertEqual(links.Hello(False, links.NO_LICENCE, '', ()), links.hello(LINK, 'admin'))
        self.assertEqual([('request', dict(outcome='refused', reason='licence', link_id=LINK, actor='admin',
                                           method='GET', path='/multiserver/gateway/hello'))] * 5, self.audited)


class CompatibilityTests(unittest.TestCase):
    """The panel also runs on Python 3.6 with Django 3.1 and cryptography 3.2.1 (AlmaLinux 8)."""
    DIRECTORY = Path(__file__).parent
    SOURCES = ('links.py', 'test_links.py', 'test_links_database.py')

    @unittest.skipUnless(sys.version_info >= (3, 8), 'ast cannot check for an older Python here')
    def test_sources_parse_as_python_3_6(self):
        for name in self.SOURCES:
            ast.parse((self.DIRECTORY / name).read_text(), feature_version=(3, 6))

    def test_nothing_is_imported_when_the_module_loads_but_the_standard_library_and_this_app(self):
        tree = ast.parse((self.DIRECTORY / 'links.py').read_text())
        at_load, on_use = set(), set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [node.module] if isinstance(node, ast.ImportFrom) else [alias.name for alias in node.names]
                (at_load if node in tree.body else on_use).update(names)
        self.assertEqual({'base64', 'collections', 'contextlib', 'json', 're', 'time', 'multiServer'}, at_load)
        self.assertEqual({'cryptography.fernet', 'django.db', 'multiServer'}, on_use)

    def test_nothing_newer_than_python_3_6_is_used(self):
        for name in self.SOURCES:
            tree = ast.parse((self.DIRECTORY / name).read_text())
            names = set(node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute))
            self.assertFalse(names & {'removeprefix', 'removesuffix', 'kwargs', 'capture_output', 'utcnow',
                                      'private_bytes_raw', 'public_bytes_raw'}, name)

    def test_the_module_writes_no_log_and_prints_nothing(self):
        source = (self.DIRECTORY / 'links.py').read_text()
        for word in ('logging', 'print(', 'CyberCPLogFileWriter', 'sys.stderr', 'traceback', 'warnings'):
            self.assertNotIn(word, source)


if __name__ == '__main__':
    unittest.main()
