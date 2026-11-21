"""A controller's servers as real rows, and hello() against a server that stands in for a node.

Runs only as root on a server marked as a disposable test server (see
multiServer/testing.py) and is skipped everywhere else. Each class works in a
database of its own that is dropped afterwards.

The node is the local TLS server of multiServer/test_transport.py. A stored
link never leads to this machine, so the record names a public address and the
test alone decides where that address leads (Asking.lead_here); the module
under test has no parameter, stored field or attribute for it.
"""
import ipaddress
import json
import socket
import threading
import time
import unittest
from unittest import mock

from multiServer import crypto, entitlement, keys, links, pairing, test_database, test_links, test_transport, transport

SKIP = test_database.SKIP
if SKIP is None:
    from django.db import connection, transaction
    from multiServer import models

MASTER, OTHER_MASTER = test_links.MASTER, test_links.OTHER_MASTER
LINK, OTHER_LINK, THIRD_LINK = test_links.LINK, test_links.OTHER_LINK, 'c3' * 16
PRIVATE, NODE_KEY, OTHER_NODE_KEY = test_links.PRIVATE, test_links.NODE_KEY, test_links.OTHER_NODE_KEY
HOST, PIN = test_links.HOST, test_links.PIN
NOW = 1795000000
PATH = '/multiserver/gateway/hello'
MARK = 'hostile-node-text'
ANSWER = b'{"build":10,"capabilities":["hello","inventory"],"role":"node","version":"3.0"}'
COLUMNS = ('link_id', 'label', 'status', 'sealed', 'panel_version', 'created_at', 'updated_at', 'last_seen_at',
           'last_error', 'last_error_at')


def setUpModule():
    if SKIP is None:
        test_transport.setUpModule()


def tearDownModule():
    if SKIP is None:
        test_transport.tearDownModule()


def said(**changes):
    """A node's answer to hello, with any of its four values changed or another added."""
    fields = dict(version='3.0', build=10, role='node', capabilities=['hello', 'inventory'])
    fields.update(changes)
    return json.dumps(fields, sort_keys=True, separators=(',', ':')).encode('ascii')


def hostile_replies():
    """What a node can say instead of the one true answer: (name, answer, fixed text, outcome, reason, status, size)."""
    reply = test_transport.reply
    page = ('<html><script>alert("%s")</script>{{7*7}}</html>' % MARK).encode()
    location = [('Location', 'https://%s.example.com/' % MARK)]
    not_valid = 'The server sent a reply that is not valid.'
    not_signed = 'The reply was not signed by the server. It may no longer accept this controller.'
    redirect = 'The server answered with a redirect instead of a signed reply.'

    def verified(name, text, outcome, reason, body, status=200, **options):
        """A reply the transport hands on: signed by the node for this request."""
        return name, reply(status=status, body=body, **options), text, outcome, reason, status, len(body)

    def unverified(name, text, reason, answer):
        return name, answer, text, 'error', reason, None, None
    return (
        verified('a value missing', links.NOT_A_NODE, 'error', 'format',
                 b'{"build":10,"capabilities":[],"role":"node"}'),
        verified('one name more', links.NOT_A_NODE, 'error', 'format', said(hostname=MARK)),
        verified('markup as the version', links.NOT_A_NODE, 'error', 'format',
                 said(version='3.0<script>%s</script>' % MARK)),
        verified('a template as the version', links.NOT_A_NODE, 'error', 'format', said(version='{{%s}}' % MARK)),
        verified('the build inside the version', links.NOT_A_NODE, 'error', 'format', said(version='3.0.10')),
        verified('text as the build', links.NOT_A_NODE, 'error', 'format', said(build=MARK)),
        verified('markup as a capability', links.NOT_A_NODE, 'error', 'format',
                 said(capabilities=['<b>%s</b>' % MARK])),
        verified('the role of a controller', links.NOT_A_NODE, 'error', 'format', said(role='controller')),
        verified('text that is not JSON', links.NOT_A_NODE, 'error', 'format',
                 ('This request need session. %s' % MARK).encode()),
        verified('a page called JSON', links.NOT_A_NODE, 'error', 'format', page),
        verified('a page called a page', links.NOT_A_NODE, 'error', 'format', page, content_type='text/html'),
        verified('the right answer called a page', links.NOT_A_NODE, 'error', 'format', ANSWER,
                 content_type='text/html'),
        verified('the right answer without a type', links.NOT_A_NODE, 'error', 'format', ANSWER,
                 content_type=None),
        verified('an empty body', links.NOT_A_NODE, 'error', 'format', b''),
        verified('one byte more than an answer may have', links.TOO_LARGE, 'error', 'size',
                 ANSWER + b' ' * (links.MAX_HELLO + 1 - len(ANSWER))),
        verified('a megabyte', links.TOO_LARGE, 'error', 'size',
                 b'{"role":"node","pad":"' + MARK.encode() * 60000 + b'"}'),
        verified('an error, signed', links.REFUSED, 'refused', 'not_allowed',
                 ('{"error":"%s"}' % MARK).encode(), status=500),
        verified('a refusal, signed', links.REFUSED, 'refused', 'not_allowed', b'{"error":"link"}', status=403),
        verified('not found, signed', links.REFUSED, 'refused', 'not_allowed', page, status=404,
                 content_type='text/html'),
        verified('the right answer under another status', links.REFUSED, 'refused', 'not_allowed', ANSWER,
                 status=201),
        unverified('more than any reply may be', links.TOO_LARGE, 'size',
                   reply(body=ANSWER, length=str(transport.MAX_RESPONSE), hold=True)),
        unverified('the right answer, unsigned', not_signed, 'signature', reply(body=ANSWER, signature=False)),
        unverified('an unsigned page', not_signed, 'signature',
                   reply(body=page, content_type='text/html', signature=False)),
        unverified('the right answer signed with another key', not_signed, 'signature',
                   reply(body=ANSWER, signed=dict(key=crypto.generate_private_key()))),
        unverified('the right answer signed for another link', not_signed, 'signature',
                   reply(body=ANSWER, signed=dict(link_id=OTHER_LINK))),
        unverified('a signature over another body', not_signed, 'signature',
                   reply(body=said(version='9.9'), signed=dict(body=ANSWER))),
        unverified('a redirect', redirect, 'format', reply(status=302, body=b'', extra=location,
                                                            signature=False)),
        unverified('a signed redirect', redirect, 'format', reply(status=307, body=ANSWER, extra=location)),
        unverified('a chunked answer', not_valid, 'format', reply(
            body=b'%x\r\n%s\r\n0\r\n\r\n' % (len(ANSWER), ANSWER), signed=dict(body=ANSWER), length=False,
            extra=[('Transfer-Encoding', 'chunked')])),
        unverified('an answer shorter than it says', not_valid, 'format',
                   reply(body=ANSWER, length=str(len(ANSWER) + 1))),
        unverified('two answers', not_valid, 'format', reply(body=ANSWER, mangle=lambda data: data + data)),
        unverified('a header that is not one', not_valid, 'format',
                   reply(body=ANSWER, extra=[('X-%s\r\nbroken' % MARK, 'x')])),
        unverified('no answer at all', 'The server could not be reached.', 'unreachable',
                   lambda node, connection, seen: None),
    )


class Controller(test_database.DjangoDatabase):
    """A licensed controller with its master key, a clock the test sets, and the real tables."""

    def setUp(self):
        super().setUp()
        self.role, self.master, self.licensed, self.now = keys.CONTROLLER, MASTER, True, NOW
        self.licence_asked = 0
        for patcher in (mock.patch.object(keys, 'role', side_effect=lambda: self.role),
                        mock.patch.object(keys, 'master_key', side_effect=lambda: self.master),
                        mock.patch.object(entitlement, 'allowed', side_effect=self.licence),
                        mock.patch.object(time, 'time', side_effect=lambda: self.now + 0.4)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def licence(self):
        self.licence_asked += 1
        return self.licensed

    def store(self, link_id=LINK, label='Frankfurt 1', actor='admin', **changes):
        fields = dict(host=HOST, port=8090, node_key=NODE_KEY, private_key=PRIVATE, tls_pin=PIN)
        fields.update(changes)
        links.store(label, link_id, actor=actor, **fields)

    def rows(self):
        return [dict(zip(COLUMNS, row)) for row in self.database.run(
            'SELECT %s FROM ms_nodes ORDER BY link_id' % ', '.join(COLUMNS))]

    def row(self, link_id=LINK):
        return dict((row['link_id'], row) for row in self.rows())[link_id]

    def alter(self, link_id=LINK, **columns):
        """Change a row behind the module's back, as someone who can only write to the database would."""
        self.database.run('UPDATE ms_nodes SET %s WHERE link_id = \'%s\'' % (
            ', '.join('%s = %s' % (name, 'NULL' if value is None else repr(value))
                      for name, value in sorted(columns.items())), link_id))

    def audited(self):
        """Every audit row as (event, outcome, reason, link, actor, method, path, status, size, dropped)."""
        rows = self.database.run('SELECT `at`, source_ip, event, outcome, reason, link_id, actor, method, path, '
                                 'status, size, dropped FROM ms_audit ORDER BY id')
        for row in rows:
            self.assertTrue(NOW <= row[0] <= self.now and row[1] == '', row)
        return [row[2:] for row in rows]

    def forget_audit(self):
        self.database.run('DELETE FROM ms_audit')

    def workers(self, calls):
        """Run every call at once, each in a thread and on a database connection of its own."""
        outcomes = [None] * len(calls)
        together = threading.Barrier(len(calls))

        def work(number, call):
            try:
                together.wait(10)
                outcomes[number] = call()
            except Exception as error:
                outcomes[number] = error
            finally:
                connection.close()
        threads = [threading.Thread(target=work, args=item) for item in enumerate(calls)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(60)
        return outcomes

    def unsealed(self, row):
        record = links.unseal(row['link_id'], row['sealed'], MASTER)
        return tuple(getattr(record, name) for name in links.Record.__slots__)


class StoreTests(Controller):
    def test_a_stored_server_is_one_pending_row_and_only_the_sealed_text_knows_how_to_reach_it(self):
        self.assertIsNone(links.store('Frankfurt 1', LINK, HOST, 8090, NODE_KEY, PRIVATE, PIN))
        (row,) = self.rows()
        sealed = row.pop('sealed')
        self.assertEqual(dict(link_id=LINK, label='Frankfurt 1', status='pending', panel_version='', created_at=NOW,
                              updated_at=NOW, last_seen_at=None, last_error='', last_error_at=None), row)
        self.assertRegex(sealed, r'\AgAAAAA[A-Za-z0-9_-]{400,838}={0,2}\Z')
        self.assertEqual((crypto.node_id(NODE_KEY), HOST, 8090, NODE_KEY, PRIVATE, PIN, None),
                         self.unsealed(dict(row, sealed=sealed)))
        self.assertIsNone(pairing.shown_number(models.Node.objects.get(pk=LINK)))
        link = links.link_of(models.Node.objects.get(pk=LINK))
        self.assertIs(transport.Link, type(link))
        self.assertEqual((LINK, crypto.node_id(NODE_KEY), HOST, 8090, HOST + ':8090', NODE_KEY, PRIVATE, PIN, False),
                         tuple(getattr(link, name) for name in transport.Link.__slots__))
        # The audit trail names the link and no part of the record. No actor was given, so none is noted.
        self.assertEqual([('pairing', 'ok', '', LINK, '', '', '', None, None, 0)], self.audited())

    def test_the_longest_record_is_stored_whole(self):
        self.store(host=test_links.LONGEST_HOST, port=65535, label='A' * 64, pairing=test_links.OF_PAIRING)
        row = self.row()
        self.assertEqual((1016, 'A' * 64), (len(row['sealed']), row['label']))
        self.assertEqual(test_links.LONGEST_HOST, links.link_of(models.Node.objects.get(pk=LINK)).host)

    def test_what_a_pairing_leaves_is_kept_sealed_and_gives_the_number_for_as_long_as_the_row_is_there(self):
        pairing_key, value = test_links.OF_PAIRING
        self.store(pairing=test_links.OF_PAIRING)
        row = self.row()
        self.assertEqual(test_links.OF_PAIRING, self.unsealed(row)[-1])
        for told in test_links.OF_PAIRING:
            self.assertNotIn(told, repr(row))
        number = pairing.confirmation_number(crypto.pair_confirmation_message(
            LINK, pairing_key, crypto.public_key(PRIVATE).hex(), NODE_KEY.hex(), value))
        self.assertEqual(number, pairing.shown_number(models.Node.objects.get(pk=LINK)))
        self.assertRegex(number, '^[0-9]{8}$')
        # Not for a row whose text was moved, altered or sealed elsewhere, and never an error.
        self.store(OTHER_LINK, node_key=OTHER_NODE_KEY, pairing=test_links.OF_PAIRING)
        self.assertNotEqual(number, pairing.shown_number(models.Node.objects.get(pk=OTHER_LINK)))
        self.alter(OTHER_LINK, sealed=row['sealed'])
        self.assertIsNone(pairing.shown_number(models.Node.objects.get(pk=OTHER_LINK)))
        self.master = test_links.OTHER_MASTER
        self.assertIsNone(pairing.shown_number(models.Node.objects.get(pk=LINK)))
        self.master = None
        self.assertIsNone(pairing.shown_number(models.Node.objects.get(pk=LINK)))

    def test_a_second_row_for_the_same_node_is_refused(self):
        self.store()
        first = self.rows()
        for change in (dict(), dict(host='node-2.example.com', port=9, label='Another name',
                                    private_key=b'p' * 32, tls_pin='e5' * 32)):
            with self.assertRaises(links.DuplicateNode) as refused:
                self.store(OTHER_LINK, **change)
            self.assertEqual('This server is already connected.', str(refused.exception))
        with self.assertRaises(links.DuplicateNode):
            self.store(LINK, node_key=OTHER_NODE_KEY)
        self.assertEqual(first, self.rows())
        self.assertEqual([('pairing', 'ok', '', LINK, 'admin', '', '', None, None, 0)]
                         + [('pairing', 'refused', 'link', OTHER_LINK, 'admin', '', '', None, None, 0)] * 2
                         + [('pairing', 'refused', 'link', LINK, 'admin', '', '', None, None, 0)], self.audited())
        # Another node is another row, even at the same address.
        self.store(OTHER_LINK, node_key=OTHER_NODE_KEY)
        self.assertEqual([LINK, OTHER_LINK], [row['link_id'] for row in self.rows()])
        # Once the first is removed, that node can be stored again.
        self.assertIs(True, links.remove(LINK))
        self.store(THIRD_LINK)
        self.assertEqual([OTHER_LINK, THIRD_LINK], [row['link_id'] for row in self.rows()])

    def test_an_address_a_link_may_not_connect_to_is_never_stored(self):
        for address, kind in test_transport.AddressRuleTests.REFUSED:
            with self.assertRaises(transport.RefusedAddress, msg=address) as refused:
                self.store(host=address)
            self.assertEqual('A link may not connect to this address (%s).' % kind, str(refused.exception))
        self.assertEqual([], self.rows())
        self.assertEqual([('pairing', 'refused', 'not_allowed', LINK, 'admin', '', '', None, None, 0)]
                         * len(test_transport.AddressRuleTests.REFUSED), self.audited())

    def test_anything_but_an_exact_description_is_never_stored(self):
        for label in ('', ' Frankfurt', 'Frankfurt<b>', '{{7*7}}', 'A' * 65, None, 7):
            with self.assertRaises(links.InvalidLabel, msg=repr(label)):
                self.store(label=label)
        for change in (dict(link_id=LINK.upper()), dict(link_id=LINK[:-1]), dict(link_id=''), dict(link_id=None),
                       dict(host='localhost'), dict(host='Node-1.example.com'), dict(host='127.1'), dict(host=''),
                       dict(host=None), dict(port=0), dict(port=65536), dict(port='8090'), dict(port=None),
                       dict(node_key=NODE_KEY[:31]), dict(node_key=NODE_KEY.hex()), dict(node_key=None),
                       dict(private_key=PRIVATE[:31]), dict(private_key=PRIVATE.hex()), dict(private_key=None),
                       dict(tls_pin=PIN.upper()), dict(tls_pin=PIN[:-1]), dict(tls_pin=None)):
            with self.assertRaises(links.InvalidRecord, msg=repr(change)):
                self.store(**change)
        self.assertEqual([], self.rows())
        self.assertEqual({('pairing', 'refused', 'format')}, set(row[:3] for row in self.audited()))
        self.assertEqual(29, len(self.audited()))

    def test_only_a_controller_that_has_its_master_key_stores(self):
        for role in (keys.OFF, keys.NODE):
            self.role = role
            with self.assertRaises(links.NotController):
                self.store()
        self.role = keys.CONTROLLER
        for master in (None, MASTER[:-1], MASTER.decode()):
            self.master = master
            with self.assertRaises(links.NoMasterKey):
                self.store()
        self.assertEqual([], self.rows())
        self.assertEqual([('pairing', 'refused', 'role', LINK, 'admin', '', '', None, None, 0)] * 2
                         + [('pairing', 'error', 'internal', LINK, 'admin', '', '', None, None, 0)] * 3,
                         self.audited())
        self.assertEqual(0, self.licence_asked)

    def test_a_row_that_cannot_be_read_stops_new_servers_until_it_is_removed(self):
        self.store()
        good = self.row()['sealed']
        damaged = dict(
            moved_from_another_row=links.seal(OTHER_LINK, test_links.record(), MASTER),
            sealed_with_another_key=links.seal(LINK, test_links.record(), OTHER_MASTER),
            cut_short=good[:-4],
            a_field_out_of_its_pattern=test_links.sealed_as_is(test_links.plain(host='10.0.0.5')),
            not_sealed_at_all='x',
        )
        for name, sealed in sorted(damaged.items()):
            with self.subTest(name):
                self.alter(sealed=sealed)
                with self.assertRaises(links.UnreadableRow) as refused:
                    self.store(OTHER_LINK, node_key=OTHER_NODE_KEY)
                self.assertNotIn(sealed, str(refused.exception))
                self.assertEqual([LINK], [row['link_id'] for row in self.rows()])
        self.assertEqual(('pairing', 'error', 'internal', OTHER_LINK), self.audited()[-1][:4])
        self.assertIs(True, links.remove(LINK))
        self.store(OTHER_LINK, node_key=OTHER_NODE_KEY)
        self.assertEqual([OTHER_LINK], [row['link_id'] for row in self.rows()])

    def test_one_node_stored_by_eight_workers_at_once_gets_one_row(self):
        for unused in range(3):
            self.database.run('DELETE FROM ms_nodes')
            ids = ['%02x' % number * 16 for number in range(8)]
            outcomes = self.workers([lambda link_id=link_id: self.store(link_id) for link_id in ids])
            self.assertEqual(['DuplicateNode'] * 7 + ['stored'], sorted(
                'stored' if outcome is None else type(outcome).__name__ for outcome in outcomes), outcomes)
            (row,) = self.rows()
            self.assertEqual(ids[outcomes.index(None)], row['link_id'])

    def test_eight_different_nodes_stored_at_once_are_all_stored(self):
        ids = ['%02x' % number * 16 for number in range(8)]
        outcomes = self.workers([
            lambda number=number: self.store(ids[number], node_key=crypto.public_key(bytes([65 + number]) * 32))
            for number in range(8)])
        self.assertEqual([None] * 8, outcomes)
        self.assertEqual(ids, [row['link_id'] for row in self.rows()])
        self.assertEqual(8, len(set(self.unsealed(row)[0] for row in self.rows())))

    def test_a_worker_waits_its_turn_and_gives_up_after_the_time_allowed(self):
        held, release = threading.Event(), threading.Event()

        def hold():
            try:
                with links._one_at_a_time():
                    held.set()
                    release.wait(20)
            finally:
                connection.close()
        holder = threading.Thread(target=hold)
        holder.start()
        try:
            self.assertTrue(held.wait(10))
            with mock.patch.object(links, 'LOCK_SECONDS', 0):
                with self.assertRaises(links.Busy):
                    self.store()
            self.assertEqual([], self.rows())
            self.assertEqual([('pairing', 'error', 'internal', LINK, 'admin', '', '', None, None, 0)], self.audited())
        finally:
            release.set()
            holder.join(20)
        free = "SELECT IS_FREE_LOCK(CONCAT(DATABASE(), '.ms_nodes'))"
        self.assertEqual(((1,),), self.database.run(free))
        self.store()
        self.assertEqual([LINK], [row['link_id'] for row in self.rows()])
        # The turn is given back when storing fails, too: asked on another connection, the lock is free.
        with self.assertRaises(links.DuplicateNode):
            self.store(OTHER_LINK)
        self.assertEqual(((1,),), self.database.run(free))

    def test_a_node_stored_but_not_yet_committed_makes_the_next_worker_wait_for_how_it_ends(self):
        class Undo(Exception):
            pass
        for commits, kept in ((True, LINK), (False, OTHER_LINK)):
            with self.subTest(commits=commits):
                self.database.run('DELETE FROM ms_nodes')
                stored, decided, outcome = threading.Event(), threading.Event(), []

                def first():
                    try:
                        with transaction.atomic():
                            self.store(LINK)
                            stored.set()
                            decided.wait(20)
                            if not commits:
                                raise Undo()
                    except Undo:
                        pass
                    finally:
                        connection.close()

                def second():
                    try:
                        outcome.append(self.store(OTHER_LINK, label='Second'))
                    except Exception as error:
                        outcome.append(error)
                    finally:
                        connection.close()
                threads = [threading.Thread(target=first), threading.Thread(target=second)]
                threads[0].start()
                try:
                    self.assertTrue(stored.wait(10))
                    threads[1].start()
                    threads[1].join(1)
                    self.assertEqual((True, []), (threads[1].is_alive(), outcome))
                finally:
                    decided.set()
                    for thread in threads:
                        if thread.ident is not None:
                            thread.join(20)
                self.assertEqual([links.DuplicateNode if commits else type(None)], [type(item) for item in outcome])
                self.assertEqual([kept], [row['link_id'] for row in self.rows()])

    def test_storing_goes_on_when_the_audit_trail_cannot_be_written(self):
        self.database.run('RENAME TABLE ms_audit TO ms_audit_away')
        try:
            self.store()
            with self.assertRaises(links.DuplicateNode):
                self.store(OTHER_LINK)
            self.alter(status='active')
            self.assertIs(True, links.pause(LINK, 'admin'))
            self.assertIs(True, links.resume(LINK, 'admin'))
            self.assertIs(True, links.remove(LINK, 'admin'))
            self.assertIs(False, links.remove(LINK, 'admin'))
        finally:
            self.database.run('RENAME TABLE ms_audit_away TO ms_audit')
        self.assertEqual(([], []), (self.rows(), self.audited()))


class PrepareTests(Controller):
    """What pairing asks before it uses a pairing code up: could the link be kept?"""
    NODE_ID = crypto.node_id(NODE_KEY)

    def prepare(self, link_id=LINK, label='Frankfurt 1', **changes):
        fields = dict(node_id=self.NODE_ID, host=HOST, port=8090, private_key=PRIVATE, tls_pin=PIN)
        fields.update(changes)
        return links.prepare(label, link_id, **fields)

    def refused(self, error, **changes):
        with self.assertRaises(error) as caught:
            self.prepare(**changes)
        self.assertIs(error, type(caught.exception))
        return str(caught.exception)

    def test_two_concurrent_codes_for_one_node_only_consume_one(self):
        def reply(endpoint, path, body, signature):
            link, pair_key, controller, timestamp, nonce = body.decode('ascii').splitlines()
            request = crypto.pair_request_message(link, pair_key, controller, self.NODE_ID, PIN,
                                                  endpoint.authority, int(timestamp), nonce)
            value = crypto.pair_value(b'n' * 32, pair_key)
            signed = crypto.sign(b'n' * 32, crypto.pair_response_message(request, NODE_KEY.hex(), value, CALLER))
            return 200, 'text/plain', '\n'.join((NODE_KEY.hex(), value, CALLER)).encode('ascii'), signed

        def code():
            seed = crypto.generate_private_key()
            value = crypto.pair_value(b'n' * 32, crypto.public_key(seed).hex())
            return pairing._encode(HOST, 8090, self.NODE_ID, PIN, seed,
                                   crypto.pair_commitment(value, '%s:8090' % HOST, PIN, CALLER))

        CALLER = '203.0.113.9'  # the controller address the node allows
        codes = [code() for _ in range(2)]
        with mock.patch.object(transport, 'exchange', side_effect=reply) as exchange:
            outcomes = self.workers([lambda code=code: pairing.start(code, 'Frankfurt', 'admin') for code in codes])
        self.assertEqual(1, exchange.call_count)
        self.assertEqual(['link'], [result.reason for result in outcomes if isinstance(result, pairing.PairingError)])
        self.assertEqual([row['link_id'] for row in self.rows()],
                         [result.link_id for result in outcomes if isinstance(result, pairing.Paired)])

    def test_what_can_be_kept_passes_and_nothing_is_stored_or_recorded(self):
        self.assertIsNone(self.prepare())
        self.assertIsNone(self.prepare(host='2a01:4f8::1', port=1))
        self.assertIsNone(self.prepare(host='a.' * 120 + 'example.com', port=65535, label='A' * 64))
        self.assertEqual(([], []), (self.rows(), self.audited()))
        # And then it is kept: the same values, and the key of the server that had not been known.
        self.store()
        self.assertEqual(1, len(self.rows()))

    def test_whatever_store_would_refuse_is_refused_by_the_same_name_before(self):
        cases = (
            (links.InvalidLabel, dict(label='')), (links.InvalidLabel, dict(label='<b>x</b>')),
            (links.InvalidLabel, dict(label='x' * 65)), (links.InvalidLabel, dict(label=None)),
            (links.InvalidRecord, dict(link_id=LINK.upper())), (links.InvalidRecord, dict(link_id=LINK[:-1])),
            (links.InvalidRecord, dict(link_id=None)),
            (links.InvalidRecord, dict(host='node 1.example.com')), (links.InvalidRecord, dict(host='127.1')),
            (links.InvalidRecord, dict(host='')), (links.InvalidRecord, dict(host=None)),
            (links.InvalidRecord, dict(port=0)), (links.InvalidRecord, dict(port=65536)),
            (links.InvalidRecord, dict(port='8090')), (links.InvalidRecord, dict(port=True)),
            (links.InvalidRecord, dict(private_key=PRIVATE[:-1])), (links.InvalidRecord, dict(private_key=None)),
            (links.InvalidRecord, dict(private_key=PRIVATE.hex())),
            (links.InvalidRecord, dict(tls_pin=PIN.upper())), (links.InvalidRecord, dict(tls_pin=PIN[:-1])),
            (links.InvalidRecord, dict(tls_pin=None)),
        )
        for error, changes in cases:
            with self.subTest(changes=changes):
                self.refused(error, **changes)
                with self.assertRaises(error):
                    self.store(**dict((name, value) for name, value in changes.items()))
        self.assertEqual([], self.rows())

    def test_the_name_of_the_server_must_be_one_too(self):
        # The server's key is not known yet; what names it has to be the fingerprint of some key.
        for node_id in ('', self.NODE_ID.upper(), self.NODE_ID[:-1], self.NODE_ID + 'a', None, NODE_KEY,
                        bytes.fromhex(self.NODE_ID)):
            self.refused(links.InvalidRecord, node_id=node_id)

    def test_an_address_a_link_may_not_connect_to_is_refused_by_its_kind(self):
        for address, kind in test_transport.AddressRuleTests.REFUSED:
            if ':' in address and transport._IPV6.fullmatch(address) is None:
                continue
            try:
                text = self.refused(transport.RefusedAddress, host=address)
            except AssertionError:
                # Spellings the transport does not take for a host at all are no record either.
                self.refused(links.InvalidRecord, host=address)
                continue
            self.assertEqual('A link may not connect to this address (%s).' % kind, text)
        self.assertEqual([], self.rows())

    def test_only_a_controller_that_has_its_master_key_is_told_yes(self):
        for role in (keys.OFF, keys.NODE):
            self.role = role
            self.assertEqual(links.NOT_CONTROLLER, self.refused(links.NotController))
        self.role = keys.CONTROLLER
        for master in (None, b'', MASTER[:-1], MASTER.decode(), b'not a key'):
            self.master = master
            self.refused(links.NoMasterKey)
        self.master = MASTER
        self.assertIsNone(self.prepare())

    def test_a_server_that_is_connected_already_is_refused_before_its_code_is_used(self):
        self.store()
        self.assertEqual('This server is already connected.', self.refused(links.DuplicateNode, link_id=OTHER_LINK))
        self.assertEqual('This server is already connected.',
                         self.refused(links.DuplicateNode, node_id=crypto.node_id(OTHER_NODE_KEY)))
        self.assertIsNone(self.prepare(OTHER_LINK, node_id=crypto.node_id(OTHER_NODE_KEY)))
        # Whatever its status: a server is connected until it is removed.
        for status in models.STATUSES:
            self.alter(status=status)
            self.refused(links.DuplicateNode, link_id=OTHER_LINK)
        self.assertIs(True, links.remove(LINK))
        self.assertIsNone(self.prepare(OTHER_LINK))

    def test_a_row_that_cannot_be_read_stops_it_as_it_stops_store(self):
        self.store()
        self.alter(sealed='not-a-sealed-text')
        text = self.refused(links.UnreadableRow, link_id=OTHER_LINK, node_id=crypto.node_id(OTHER_NODE_KEY))
        self.assertIn('Remove that server', text)
        self.assertIs(True, links.remove(LINK))
        self.assertIsNone(self.prepare(OTHER_LINK, node_id=crypto.node_id(OTHER_NODE_KEY)))

    def test_it_waits_for_nobody_and_keeps_nobody_waiting(self):
        # It only reads: a worker that is storing at this moment does not hold it up, nor the other way round.
        holder = self.database.connect()
        try:
            cursor = holder.cursor()
            cursor.execute("SELECT GET_LOCK(CONCAT(DATABASE(), '.ms_nodes'), 0)")
            self.assertEqual(1, cursor.fetchone()[0])
            started = time.monotonic()
            self.assertIsNone(self.prepare())
            self.assertLess(time.monotonic() - started, 2)
        finally:
            holder.close()

    def test_no_text_of_a_refusal_holds_a_key(self):
        self.store()
        for changes in (dict(link_id=OTHER_LINK), dict(host='10.0.0.5'), dict(tls_pin='x'), dict(label='')):
            try:
                self.prepare(**changes)
            except (links.LinkError, transport.TransportError) as error:
                shown = repr(error) + str(error) + repr(error.args)
                for secret in (PRIVATE.hex(), MASTER.decode(), PIN, NODE_KEY.hex()):
                    self.assertNotIn(secret, shown)
                self.assertIsNone(error.__cause__)


class StateTests(Controller):
    CHANGES = (('pause', 'active', 'paused', 'link_pause'), ('resume', 'paused', 'active', 'link_resume'))

    def test_a_server_becomes_active_by_proof_alone(self):
        # confirm() is the one way from pending to active (ConfirmTests); no function just says so.
        self.assertFalse(hasattr(links, 'activate'))
        self.store()
        for name, _, _, _ in self.CHANGES:
            self.assertIs(False, getattr(links, name)(LINK, 'admin'))
        self.assertEqual('pending', self.row()['status'])
        public = sorted(name for name, value in vars(links).items()
                        if callable(value) and not name.startswith('_') and getattr(value, '__module__', '') ==
                        links.__name__ and not isinstance(value, type))
        self.assertEqual(['check_label', 'confirm', 'hello', 'link_of', 'pairing_slot', 'pause', 'prepare', 'remove',
                          'resume', 'revoke', 'seal', 'store', 'unseal'], public)

    def test_a_link_changes_state_only_from_the_state_that_change_starts_in(self):
        self.store()
        self.forget_audit()
        self.now += 60
        for name, before, after, event in self.CHANGES:
            for status in models.STATUSES:
                with self.subTest(change=name, status=status):
                    self.alter(status=status, updated_at=NOW)
                    moved = getattr(links, name)(LINK, 'admin')
                    self.assertIs(status == before, moved)
                    row = self.row()
                    self.assertEqual((after, NOW + 60) if moved else (status, NOW),
                                     (row['status'], row['updated_at']))
                    self.assertEqual((event,) + (('ok', '') if moved else ('refused', 'link'))
                                     + (LINK, 'admin', '', '', None, None, 0), self.audited()[-1])
        self.assertEqual(len(self.CHANGES) * len(models.STATUSES), len(self.audited()))

    def test_a_change_touches_nothing_but_the_status_and_its_time(self):
        self.store()
        self.alter(status='active')
        before = self.row()
        self.now += 60
        for name, _, after, _ in self.CHANGES:
            self.assertIs(True, getattr(links, name)(LINK))
            self.assertEqual(dict(before, status=after, updated_at=NOW + 60), self.row())

    def test_of_eight_workers_making_the_same_change_one_makes_it(self):
        self.store()
        for name, before, _, _ in self.CHANGES:
            self.alter(status=before)
            self.assertEqual([False] * 7 + [True],
                             sorted(self.workers([lambda: getattr(links, name)(LINK, 'admin')] * 8)))
        self.assertEqual([False] * 7 + [True], sorted(self.workers([lambda: links.remove(LINK, 'admin')] * 8)))

    def test_revoke_retains_key_for_retry_until_the_remote_node_confirms(self):
        self.store()
        self.alter(status='paused')
        self.licensed = False
        with mock.patch.object(transport, 'send', side_effect=[
            (403, 'application/json', b'{}'), (200, 'application/json', b'{"revoked":true}')
        ]):
            self.assertFalse(links.revoke(LINK, 'admin'))
            self.assertEqual((models.REVOKING, links.REFUSED), (self.row()['status'], self.row()['last_error']))
            self.assertFalse(links.resume(LINK, 'admin'))
            self.assertTrue(links.revoke(LINK, 'admin'))
            self.assertFalse(links.revoke(LINK, 'admin'))
            self.assertEqual([], self.rows())

    def test_lapsed_controller_can_pause_and_remove_an_unreadable_row(self):
        self.store()
        self.alter(status='active')
        node = models.Node.objects.get(pk=LINK)
        models.InventoryCache.objects.create(node=node, snapshot='{}')
        models.Capability.objects.create(token_hash='e1' * 32, node=node, admin_id=1, session_hash='e2' * 32,
                                         created_at=NOW, expires_at=NOW + 60)
        self.store(OTHER_LINK, node_key=OTHER_NODE_KEY)
        self.forget_audit()
        self.master, self.licensed = None, False
        self.alter(sealed='x')
        with mock.patch.object(keys, 'master_key', side_effect=AssertionError('the key is not asked')), \
                mock.patch.object(links, 'unseal', side_effect=AssertionError('nothing is opened')):
            self.assertIs(True, links.pause(LINK, 'admin'))
            self.assertEqual('paused', self.row()['status'])
            self.assertIs(False, links.resume(LINK, 'admin'))
            self.assertIs(True, links.remove(LINK, 'admin'))
            self.assertIs(False, links.remove(LINK, 'admin'))
        self.assertEqual(1, self.licence_asked)
        self.assertEqual([OTHER_LINK], [row['link_id'] for row in self.rows()])
        self.assertEqual((0, 0), (models.InventoryCache.objects.count(), models.Capability.objects.count()))
        self.assertEqual([(event, outcome, reason, LINK, 'admin', '', '', None, None, 0) for event, outcome, reason in (
            ('link_pause', 'ok', ''), ('link_resume', 'refused', 'licence'), ('node_remove', 'ok', ''),
            ('node_remove', 'refused', 'link'))], self.audited())

    def test_what_is_not_a_link_id_names_no_row(self):
        self.store()
        self.store(OTHER_LINK, node_key=OTHER_NODE_KEY)
        for status in models.STATUSES:
            self.alter(status=status)
            self.alter(OTHER_LINK, status=status)
            before = self.rows()
            for not_an_id in (None, 0, 1, True, '', '%', '_' * 32, LINK.upper(), LINK[:-1], LINK + ' ', ' ' + LINK,
                              LINK + '\n', LINK.encode(), [LINK], (LINK,), {LINK: 1}, THIRD_LINK):
                for change in (links.pause, links.resume, links.remove):
                    self.assertIs(False, change(not_an_id, 'admin'), repr(not_an_id))
                for ask in (links.hello, links.confirm):
                    self.assertEqual(links.Hello(False, links.NO_SUCH_SERVER, '', ()), ask(not_an_id, 'admin'))
            self.assertEqual(before, self.rows())


class Asking(Controller):
    """A controller and a stand-in node that it has stored; active, unless a test wants it as it was stored."""

    def setUp(self):
        super().setUp()
        self.led = []
        patcher = mock.patch.object(transport, '_node_addresses', side_effect=self.lead_here)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(transport, 'send', wraps=transport.send)
        self.sent = patcher.start()
        self.addCleanup(patcher.stop)

    def lead_here(self, link, deadline):
        """The one thing a test decides for the transport: where the public address of the record leads."""
        self.led.append((link.host, link.allow_loopback_for_tests))
        return [ipaddress.ip_address('127.0.0.1')]

    def paired(self, answer=None, link_id=LINK, label='Frankfurt 1', pinned=None, status='active', **options):
        node = test_transport.Node(answer or test_transport.reply(body=ANSWER), **options)
        self.addCleanup(node.close)
        links.store(label, link_id, HOST, node.port, node.public, PRIVATE, pinned or node.pin)
        self.assertEqual('pending', self.row(link_id)['status'])
        if status != 'pending':
            self.alter(link_id, status=status)
        self.forget_audit()
        return node

    def assert_not_asked(self, *nodes):
        self.sent.assert_not_called()
        self.assertEqual([], self.led)
        time.sleep(0.1)
        for node in nodes:
            self.assertTrue(node.connections.empty())

    def assert_failed(self, text, outcome, reason, status=None, size=None, link_id=LINK, actor='admin', ask=None):
        """hello() says exactly this fixed text, writes it on the row and changes nothing else there."""
        before = self.row(link_id)
        self.forget_audit()
        self.now += 1
        self.assertEqual(links.Hello(False, text, '', ()), (ask or links.hello)(link_id, actor))
        self.assertIn(text, links.STORED_ERRORS)
        self.assertEqual(dict(before, last_error=text, last_error_at=self.now), self.row(link_id))
        self.assertEqual([('request', outcome, reason, link_id, actor, 'GET', PATH, status, size, 0)], self.audited())
        self.assertNotIn(MARK, repr(self.rows()) + repr(self.database.run('SELECT * FROM ms_audit')))


class HelloTests(Asking):
    def test_a_node_that_answers_is_noted_as_seen_with_its_version(self):
        node = self.paired()
        self.alter(last_error='The server could not be reached.', last_error_at=NOW - 60)
        before = self.row()
        self.now += 5
        self.assertEqual(links.Hello(True, '', '3.0.10', ('hello', 'inventory')), links.hello(LINK, 'admin'))
        self.assertEqual(dict(before, panel_version='3.0.10', last_seen_at=NOW + 5, last_error='',
                              last_error_at=None), self.row())
        self.assertEqual([('request', 'ok', '', LINK, 'admin', 'GET', PATH, 200, len(ANSWER), 0)], self.audited())
        seen = node.finished()['seen']
        self.assertEqual(('GET', PATH, b''), (seen.method, seen.target, seen.body))
        self.assertEqual([('Host', '%s:%d' % (HOST, node.port)), ('Connection', 'close'),
                          ('Accept-Encoding', 'identity'), ('X-CPMS-Link', LINK), ('X-CPMS-Node', node.id),
                          ('X-CPMS-Timestamp', str(NOW + 5)), ('X-CPMS-Actor', 'admin'), ('X-CPMS-Mode', 'json')],
                         [header for header in seen.headers if header[0] not in ('X-CPMS-Nonce', 'X-CPMS-Signature')])
        self.assertTrue(crypto.verify(crypto.public_key(PRIVATE), bytes.fromhex(dict(seen.headers)['X-CPMS-Signature']),
                                      node.request_message(seen)))
        # The stored link named a public address and carried no allowance; the test led it here.
        self.assertEqual([(HOST, False)], self.led)

    def test_each_answer_replaces_what_the_last_one_left(self):
        node = self.paired()
        self.assertEqual('3.0.10', links.hello(LINK, 'admin').panel_version)
        node.answer = test_transport.reply(body=said(version='3.1', build=0, capabilities=[]))
        self.now += 30
        self.assertEqual(links.Hello(True, '', '3.1.0', ()), links.hello(LINK, 'admin'))
        self.assertEqual(('3.1.0', NOW + 30), (self.row()['panel_version'], self.row()['last_seen_at']))
        # An answer exactly as large as an answer may be is still read.
        node.answer = test_transport.reply(body=ANSWER + b' ' * (links.MAX_HELLO - len(ANSWER)))
        self.assertEqual(links.Hello(True, '', '3.0.10', ('hello', 'inventory')), links.hello(LINK, 'admin'))

    def test_whatever_else_a_node_says_leaves_a_fixed_text_and_not_a_word_of_its_own(self):
        reply, cases = test_transport.reply, hostile_replies()
        node = self.paired()
        self.assertEqual('3.0.10', links.hello(LINK, 'admin').panel_version)
        with mock.patch.object(transport, 'DEADLINE', 5):
            for name, answer, text, outcome, reason, status, size in cases:
                with self.subTest(name):
                    node.answer = answer
                    self.assert_failed(text, outcome, reason, status, size)
                    self.assertEqual(('3.0.10', NOW), (self.row()['panel_version'], self.row()['last_seen_at']))
            # The next true answer clears the text again.
            node.answer = reply(body=ANSWER)
            self.assertIs(True, links.hello(LINK, 'admin').ok)
            self.assertEqual(('', None), (self.row()['last_error'], self.row()['last_error_at']))
        self.assertEqual(len(cases) + 2, self.sent.call_count)
        self.assertEqual(len(cases) + 2, len(self.led))

    def test_a_node_that_does_not_answer_in_time_is_given_up_on(self):
        node = self.paired(test_transport.reply(body=ANSWER, hold=True))
        with mock.patch.object(transport, 'DEADLINE', 0.6), mock.patch.object(transport, 'CONNECT_TIMEOUT', 0.3):
            started = time.monotonic()
            self.assert_failed('The server did not answer in time.', 'error', 'timeout')
            self.assertLess(time.monotonic() - started, 3)
            node.speaks_tls = False
            self.assert_failed('The server did not answer in time.', 'error', 'timeout')

    def test_a_server_with_another_certificate_is_sent_nothing(self):
        node = self.paired(certificate='impostor', pinned=test_transport.pin('node'))
        self.assert_failed('The server presented a different certificate from the one it was connected with.',
                           'error', 'certificate')
        record = node.finished()
        self.assertEqual((True, b'', None), (record['tls'], record['raw'], record['seen']))

    def test_a_server_that_is_gone_is_noted_as_unreachable(self):
        node = self.paired()
        node.close()
        time.sleep(0.2)
        self.assert_failed('The server could not be reached.', 'error', 'unreachable')

    def test_a_reply_that_arrives_after_the_server_was_paused_or_removed_is_not_written_down(self):
        def pause_first(node, connection, seen):
            self.alter(status='paused')
            test_transport.reply(body=ANSWER)(node, connection, seen)

        def remove_first(node, connection, seen):
            self.database.run('DELETE FROM ms_nodes')
            test_transport.reply(body=said(role=MARK))(node, connection, seen)
        self.paired(pause_first)
        before = self.row()
        self.assertEqual(links.Hello(True, '', '3.0.10', ('hello', 'inventory')), links.hello(LINK, 'admin'))
        self.assertEqual(dict(before, status='paused'), self.row())
        self.alter(status='active')
        self.paired(remove_first, link_id=OTHER_LINK, label='Second')
        self.assertEqual(links.Hello(False, links.NOT_A_NODE, '', ()), links.hello(OTHER_LINK, 'admin'))
        self.assertEqual([], self.rows())

    def test_an_actor_that_cannot_be_signed_for_is_sent_nowhere(self):
        node = self.paired()
        for actor in ('', 'two words', 'admin\r\nX-CPMS-Mode: page', 'a' * 51, None, 7):
            self.sent.reset_mock()
            before = self.row()
            self.forget_audit()
            self.assertEqual(links.Hello(False, 'The request could not be signed.', '', ()), links.hello(LINK, actor))
            self.assertEqual(dict(before, last_error='The request could not be signed.', last_error_at=NOW),
                             self.row())
            # The audit trail leaves the actor out and counts that it did.
            self.assertEqual([('request', 'error', 'format', LINK, '', 'GET', PATH, None, None,
                               0 if actor is None else 1)], self.audited())
        time.sleep(0.1)
        self.assertTrue(node.connections.empty())
        self.assertEqual([], self.led)


class ConfirmTests(Asking):
    """From stored to active: only on the server's own verified answer to the first request of the link."""

    def assert_pending(self, text, outcome, reason, status=None, size=None):
        self.assert_failed(text, outcome, reason, status, size, ask=links.confirm)
        self.assertEqual('pending', self.row()['status'])

    def test_a_pending_server_that_answers_becomes_active_with_its_version(self):
        node = self.paired(status='pending')
        self.alter(last_error='The server answered with a redirect instead of a signed reply.', last_error_at=NOW - 9)
        before = self.row()
        self.now += 5
        self.assertEqual(links.Hello(True, '', '3.0.10', ('hello', 'inventory')), links.confirm(LINK, 'admin'))
        self.assertEqual(dict(before, status='active', updated_at=NOW + 5, panel_version='3.0.10',
                              last_seen_at=NOW + 5, last_error='', last_error_at=None), self.row())
        self.assertEqual([('request', 'ok', '', LINK, 'admin', 'GET', PATH, 200, len(ANSWER), 0),
                          ('link_approve', 'ok', '', LINK, 'admin', '', '', None, None, 0)], self.audited())
        # What was sent is exactly what hello() sends: there is no second kind of request.
        seen = node.finished()['seen']
        self.assertEqual(('GET', PATH, b'', 'json'), (seen.method, seen.target, seen.body,
                                                      dict(seen.headers)['X-CPMS-Mode']))
        self.assertEqual((links._HELLO.status, links._CONFIRM.status), (models.ACTIVE, models.PENDING))
        # From now on it is asked with hello(), and confirm() has nothing more to do.
        self.assertIs(True, links.hello(LINK, 'admin').ok)
        self.assertEqual(links.Hello(False, links.NOT_PENDING, '', ()), links.confirm(LINK, 'admin'))

    def test_a_server_that_has_not_accepted_the_link_stays_pending_with_a_fixed_text(self):
        # What a managed server answers before its administrator approved: its unsigned refusals.
        reply = test_transport.reply
        node = self.paired(reply(status=302, body=b'', extra=[('Location', '/')], signature=False), status='pending')
        self.assert_pending('The server answered with a redirect instead of a signed reply.', 'error', 'format')
        node.answer = reply(body=b'{"error_message": "This request need session."}', signature=False)
        self.assert_pending('The reply was not signed by the server. It may no longer accept this controller.',
                            'error', 'signature')
        # Approved there, it answers, and the same call now makes it active and clears the text.
        node.answer = reply(body=ANSWER)
        self.assertIs(True, links.confirm(LINK, 'admin').ok)
        self.assertEqual(('active', '', None), tuple(self.row()[name] for name in ('status', 'last_error',
                                                                                   'last_error_at')))

    def test_whatever_else_a_server_says_leaves_it_pending_with_a_fixed_text_and_not_a_word_of_its_own(self):
        cases = hostile_replies()
        node = self.paired(status='pending')
        with mock.patch.object(transport, 'DEADLINE', 5):
            for name, answer, text, outcome, reason, status, size in cases:
                with self.subTest(name):
                    node.answer = answer
                    self.assert_pending(text, outcome, reason, status, size)
                    self.assertEqual(('', None), (self.row()['panel_version'], self.row()['last_seen_at']))
        self.assertEqual(len(cases), self.sent.call_count)
        self.assertEqual(0, len([row for row in self.database.run('SELECT event FROM ms_audit')
                                 if row[0] == 'link_approve']))

    def test_a_failure_of_any_kind_leaves_it_pending(self):
        self.paired(status='pending')
        for error in (RuntimeError(MARK), OSError(MARK), MemoryError(MARK), transport.TransportError(MARK)):
            with mock.patch.object(transport, 'send', side_effect=error):
                self.assert_pending(links.FAILED, 'error', 'internal')
        for kind, reason, text in links._FAILURES:
            with mock.patch.object(transport, 'send', side_effect=kind('%s <script>' % MARK)):
                self.assert_pending(text, 'error', reason)
        with mock.patch.object(links, '_answer', side_effect=RuntimeError(MARK)):
            self.assert_pending(links.FAILED, 'error', 'internal')

    def test_only_a_pending_server_is_confirmed_and_no_other_is_even_asked(self):
        node = self.paired(status='pending')
        others = ('active', 'paused', 'revoked', '', 'PENDING', 'pending ', 'pending2')
        for status in others:
            self.alter(status=status)
            before = self.rows()
            self.assertEqual(links.Hello(False, links.NOT_PENDING, '', ()), links.confirm(LINK, 'admin'), status)
            self.assertEqual(before, self.rows())
        self.assertEqual(links.Hello(False, links.NO_SUCH_SERVER, '', ()), links.confirm(OTHER_LINK, 'admin'))
        self.assert_not_asked(node)
        self.assertEqual([('request', 'refused', 'link', LINK, 'admin', 'GET', PATH, None, None, 0)] * len(others)
                         + [('request', 'refused', 'link', OTHER_LINK, 'admin', 'GET', PATH, None, None, 0)],
                         self.audited())
        # And hello() does not stand in for it: a pending server is not asked that way.
        self.alter(status='pending')
        self.assertEqual(links.Hello(False, links.NOT_ACTIVE, '', ()), links.hello(LINK, 'admin'))
        self.assert_not_asked(node)
        self.assertEqual('pending', self.row()['status'])

    def test_without_the_licence_or_the_role_nobody_is_asked_and_nothing_changes(self):
        node = self.paired(status='pending')
        before = self.rows()
        self.licensed = False
        self.assertEqual(links.Hello(False, links.NO_LICENCE, '', ()), links.confirm(LINK, 'admin'))
        self.licensed = True
        for role in (keys.OFF, keys.NODE):
            self.role = role
            self.assertEqual(links.Hello(False, links.NOT_CONTROLLER, '', ()), links.confirm(LINK, 'admin'))
        self.assert_not_asked(node)
        self.assertEqual(before, self.rows())
        self.assertEqual(['licence', 'role', 'role'], [row[2] for row in self.audited()])

    def test_a_row_whose_sealed_text_does_not_open_is_not_asked_and_stays_pending(self):
        node = self.paired(status='pending')
        self.alter(sealed=self.row()['sealed'][:-4])
        self.assert_pending(links.UNREADABLE, 'error', 'internal')
        self.assert_not_asked(node)

    def test_of_eight_workers_confirming_at_once_one_makes_it_active(self):
        self.paired(status='pending')
        outcomes = self.workers([lambda: links.confirm(LINK, 'admin')] * 8)
        self.assertEqual([links.Hello(False, links.NOT_PENDING, '', ())] * 7
                         + [links.Hello(True, '', '3.0.10', ('hello', 'inventory'))], sorted(outcomes))
        self.assertEqual('active', self.row()['status'])
        events = [row[0:3] for row in self.audited()]
        self.assertEqual(1, events.count(('link_approve', 'ok', '')))
        self.assertEqual(1, events.count(('request', 'ok', '')))
        self.assertEqual(7, events.count(('request', 'refused', 'link')))

    def test_an_answer_that_arrives_after_the_server_was_removed_or_changed_makes_nothing_active(self):
        def remove_first(node, connection, seen):
            self.database.run('DELETE FROM ms_nodes')
            test_transport.reply(body=ANSWER)(node, connection, seen)

        def revoke_first(node, connection, seen):
            self.alter(status='revoked')
            test_transport.reply(body=ANSWER)(node, connection, seen)
        self.paired(revoke_first, status='pending')
        before = self.row()
        self.assertEqual(links.Hello(False, links.NOT_PENDING, '', ()), links.confirm(LINK, 'admin'))
        self.assertEqual(dict(before, status='revoked'), self.row())
        self.assertEqual([('request', 'refused', 'link', LINK, 'admin', 'GET', PATH, None, None, 0)], self.audited())
        self.paired(remove_first, link_id=OTHER_LINK, label='Second', status='pending')
        self.assertEqual(links.Hello(False, links.NOT_PENDING, '', ()), links.confirm(OTHER_LINK, 'admin'))
        self.assertEqual([], self.rows())

    def test_an_actor_that_cannot_be_signed_for_confirms_nothing(self):
        node = self.paired(status='pending')
        for actor in ('', 'two words', 'admin\r\nX-CPMS-Mode: page', 'a' * 51, None, 7):
            self.assertEqual(links.Hello(False, 'The request could not be signed.', '', ()),
                             links.confirm(LINK, actor))
            self.assertEqual('pending', self.row()['status'])
        time.sleep(0.1)
        self.assertTrue(node.connections.empty())

    def test_without_its_tables_it_still_answers_and_does_not_raise(self):
        self.paired(status='pending')
        self.database.run('RENAME TABLE ms_nodes TO ms_nodes_away')
        try:
            with transaction.atomic():
                result = links.confirm(LINK, 'admin')
                self.assertEqual(0, models.Link.objects.count())
        finally:
            self.database.run('RENAME TABLE ms_nodes_away TO ms_nodes')
        self.assertEqual(links.Hello(False, links.FAILED, '', ()), result)
        self.assertEqual('pending', self.row()['status'])
        # Without the audit trail the proof still counts: an audit failure never changes an outcome.
        self.database.run('RENAME TABLE ms_audit TO ms_audit_away')
        try:
            self.assertIs(True, links.confirm(LINK, 'admin').ok)
        finally:
            self.database.run('RENAME TABLE ms_audit_away TO ms_audit')
        self.assertEqual('active', self.row()['status'])


class NothingSentTests(Asking):
    def test_without_the_licence_no_server_is_asked_and_no_row_changes(self):
        node = self.paired()
        before = self.rows()
        for answer in (False, None, 0, 1, 'yes'):
            self.licensed = answer
            self.assertEqual(links.Hello(False, links.NO_LICENCE, '', ()), links.hello(LINK, 'admin'))
        self.assert_not_asked(node)
        self.assertEqual(before, self.rows())
        self.assertEqual([('request', 'refused', 'licence', LINK, 'admin', 'GET', PATH, None, None, 0)] * 5,
                         self.audited())
        self.assertEqual(5, self.licence_asked)
        # With the licence back, the same call goes out.
        self.licensed = True
        self.assertIs(True, links.hello(LINK, 'admin').ok)
        self.assertEqual(1, self.sent.call_count)
        self.assertEqual('GET', node.finished()['seen'].method)

    def test_a_server_that_is_not_a_controller_asks_nobody_and_does_not_ask_for_the_licence(self):
        node = self.paired()
        before = self.rows()
        for role in (keys.OFF, keys.NODE):
            self.role = role
            self.assertEqual(links.Hello(False, links.NOT_CONTROLLER, '', ()), links.hello(LINK, 'admin'))
        self.assert_not_asked(node)
        self.assertEqual((before, 0), (self.rows(), self.licence_asked))
        self.assertEqual([('request', 'refused', 'role', LINK, 'admin', 'GET', PATH, None, None, 0)] * 2,
                         self.audited())

    def test_only_an_active_server_is_asked(self):
        node = self.paired()
        others = ('pending', 'paused', 'revoked', '', 'ACTIVE', 'active ', 'active2')
        for status in others:
            self.alter(status=status)
            before = self.rows()
            self.assertEqual(links.Hello(False, links.NOT_ACTIVE, '', ()), links.hello(LINK, 'admin'), status)
            self.assertEqual(before, self.rows())
        self.assertEqual(links.Hello(False, links.NO_SUCH_SERVER, '', ()), links.hello(OTHER_LINK, 'admin'))
        self.assert_not_asked(node)
        self.assertEqual([('request', 'refused', 'link', LINK, 'admin', 'GET', PATH, None, None, 0)] * len(others)
                         + [('request', 'refused', 'link', OTHER_LINK, 'admin', 'GET', PATH, None, None, 0)],
                         self.audited())
        # Paused by its own function and resumed, it is asked again.
        self.alter(status='active')
        self.assertIs(True, links.pause(LINK))
        self.assertEqual(links.NOT_ACTIVE, links.hello(LINK, 'admin').error)
        self.assert_not_asked(node)
        self.assertIs(True, links.resume(LINK))
        self.assertIs(True, links.hello(LINK, 'admin').ok)

    def test_a_row_whose_sealed_text_does_not_open_is_not_asked(self):
        node = self.paired()
        good = self.row()['sealed']
        record = links.unseal(LINK, good, MASTER)
        damaged = dict(
            moved_from_another_row=links.seal(OTHER_LINK, record, MASTER),
            sealed_with_another_key=links.seal(LINK, record, OTHER_MASTER),
            cut_short=good[:-4], one_character_changed=good[:50] + ('A' if good[50] != 'A' else 'B') + good[51:],
            not_sealed_at_all='not-a-sealed-text', empty='',
            a_private_address=test_links.sealed_as_is(test_links.plain(
                host='10.0.0.5', port=str(node.port), node_id=node.id, node_key=node.public.hex(), tls_pin=node.pin)),
            this_machine=test_links.sealed_as_is(test_links.plain(
                host='127.0.0.1', port=str(node.port), node_id=node.id, node_key=node.public.hex(), tls_pin=node.pin)),
            one_line_more=test_links.sealed_as_is(test_links.plain(
                'true', port=str(node.port), node_id=node.id, node_key=node.public.hex(), tls_pin=node.pin)),
        )
        for name, sealed in sorted(damaged.items()):
            with self.subTest(name):
                self.alter(sealed=sealed)
                self.assert_failed(links.UNREADABLE, 'error', 'internal')
        for master in (None, OTHER_MASTER):
            self.alter(sealed=good)
            self.master = master
            self.assert_failed(links.UNREADABLE, 'error', 'internal')
        self.assert_not_asked(node)
        self.master = MASTER
        self.assertIs(True, links.hello(LINK, 'admin').ok)

    def test_two_rows_that_swap_their_sealed_texts_reach_neither_server(self):
        """Whoever can write to the database cannot make one server's link lead to another server."""
        first = self.paired()
        second = self.paired(link_id=OTHER_LINK, label='Second')
        texts = self.row(LINK)['sealed'], self.row(OTHER_LINK)['sealed']
        self.alter(LINK, sealed=texts[1])
        self.alter(OTHER_LINK, sealed=texts[0])
        self.assert_failed(links.UNREADABLE, 'error', 'internal')
        self.assert_failed(links.UNREADABLE, 'error', 'internal', link_id=OTHER_LINK)
        self.assert_not_asked(first, second)
        self.alter(LINK, sealed=texts[0])
        self.assertIs(True, links.hello(LINK, 'admin').ok)
        self.assertEqual(LINK, first.named(first.finished()['seen'])['link'])
        self.assertTrue(first.connections.empty() and second.connections.empty())


class NoWayHereTests(Controller):
    """Without the test's own lead, as on a real controller: nothing stored reaches this machine."""

    def test_a_name_that_leads_to_this_machine_or_inside_is_never_connected_to(self):
        node = test_transport.Node(test_transport.reply(body=ANSWER))
        self.addCleanup(node.close)
        links.store('Frankfurt 1', LINK, 'node-1.example.com', node.port, node.public, PRIVATE, node.pin)
        self.alter(status='active')
        self.assertIs(False, links.link_of(models.Node.objects.get(pk=LINK)).allow_loopback_for_tests)
        text = 'The name of the server now leads to an address that a link may not connect to.'
        for address in ('127.0.0.1', '10.0.0.5', '169.254.169.254', '::1'):
            answers = [(socket.AF_INET6 if ':' in address else socket.AF_INET, socket.SOCK_STREAM, 6, '',
                        (address, node.port))]
            self.forget_audit()
            with mock.patch.object(socket, 'getaddrinfo', return_value=answers) as lookup, \
                    mock.patch.object(socket, 'socket') as made:
                self.assertEqual(links.Hello(False, text, '', ()), links.hello(LINK, 'admin'))
                self.assertEqual(1, lookup.call_count)
                made.assert_not_called()
            self.assertEqual((text, NOW), (self.row()['last_error'], self.row()['last_error_at']))
            self.assertEqual([('request', 'error', 'not_allowed', LINK, 'admin', 'GET', PATH, None, None, 0)],
                             self.audited())
        time.sleep(0.1)
        self.assertTrue(node.connections.empty())


class NeverRaisesTests(Asking):
    def test_an_error_nobody_expected_becomes_the_general_text_and_none_of_its_own(self):
        self.paired()
        for error in (RuntimeError(MARK), ValueError(MARK), OSError(MARK), KeyError(MARK), MemoryError(MARK),
                      transport.TransportError(MARK)):
            with mock.patch.object(transport, 'send', side_effect=error):
                self.assert_failed(links.FAILED, 'error', 'internal')

    def test_every_refusal_of_the_transport_becomes_its_fixed_text_whatever_the_error_says(self):
        self.paired()
        for kind, reason, text in links._FAILURES:
            with mock.patch.object(transport, 'send', side_effect=kind('%s <script>' % MARK)):
                self.assert_failed(text, 'error', reason)

    def test_without_its_tables_it_still_answers_and_does_not_raise(self):
        node = self.paired()
        for table in ('ms_nodes', 'ms_audit'):
            self.database.run('RENAME TABLE %s TO %s_away' % (table, table))
            try:
                with transaction.atomic():
                    result = links.hello(LINK, 'admin')
                    # The caller's own transaction is still usable afterwards.
                    self.assertEqual(0, models.Link.objects.count())
            finally:
                self.database.run('RENAME TABLE %s_away TO %s' % (table, table))
            if table == 'ms_nodes':
                self.assertEqual(links.Hello(False, links.FAILED, '', ()), result)
            else:
                self.assertEqual(links.Hello(True, '', '3.0.10', ('hello', 'inventory')), result)
        self.assertEqual('3.0.10', self.row()['panel_version'])
        # Only the second call got as far as the node.
        self.assertEqual('GET', node.finished()['seen'].method)
        self.assertTrue(node.connections.empty())


if __name__ == '__main__':
    unittest.main()
