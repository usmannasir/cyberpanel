import copy
import unittest
from unittest.mock import patch

from multiServer import inventory, test_links_database as db

SAMPLE = {'version': 1, 'websites': {'rows': [['shop.example', 1]], 'partial': False},
          'databases': {'rows': [['shop_db', 'shop.example']], 'partial': False},
          'mail': {'rows': [['sales+web@shop.example', 'shop.example']], 'partial': False}}


class ContractTests(unittest.TestCase):
    def test_exact_roundtrip(self):
        self.assertEqual(SAMPLE, inventory.decode(inventory.encode(SAMPLE)))

    def test_wrong_types_extra_fields_duplicate_names_and_size(self):
        for key, value in [('version', True), ('version', 2), ('other', []),
                           ('mail', {'rows': [], 'partial': 1}),
                           ('databases', {'rows': [], 'partial': False, 'extra': ''})]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                inventory.decode(inventory.encode(dict(SAMPLE, **{key: value})))
        for raw in [inventory.encode(SAMPLE).replace(b'"version":1', b'"version":1,"version":1'),
                    b' ' * (inventory.BYTE_LIMIT + 1)]:
            with self.assertRaises(ValueError):
                inventory.decode(raw)
        for category, rows in [('websites', [['<site>', 1]]), ('websites', [['site', True]]),
                               ('websites', [['a' * 64 + '.example', 0]]),
                               ('databases', [['a', 'site'], ['A', 'site']]),
                               ('databases', [['db', 'site', 'extra']]),
                               ('mail', [['test@site.example', 'other.example']]),
                               ('mail', [['x@K.test', 'k.test']]),
                               ('websites', [['site', 1]] * (inventory.ROW_LIMIT + 1))]:
            with self.subTest(category=category), self.assertRaises(ValueError):
                data = copy.deepcopy(SAMPLE)
                data[category]['rows'] = rows
                inventory.decode(inventory.encode(data))


@unittest.skipIf(db.SKIP, db.SKIP)
class CacheTests(db.Controller):
    def setUp(self):
        super().setUp()
        from multiServer import inventory_cache, models
        self.cache = inventory_cache
        self.store()
        self.alter(status='active')
        self.active = models.Node.objects.filter(status=models.ACTIVE)
        self.send = patch.object(db.transport, 'send', return_value=(200, 'application/json', inventory.encode(SAMPLE)))
        self.wire = self.send.start()
        self.addCleanup(self.send.stop)

    def refresh(self):
        self.cache.refresh(self.active, 'admin', self.now)

    def contents(self):
        node, saved, fetched, error = next(self.cache.sources(self.active))
        return self.cache.contents(node, saved, fetched, error, self.now)

    def test_fresh_circuit_stale_expiry_and_recovery(self):
        self.refresh()
        self.refresh()
        self.assertEqual(1, self.wire.call_count)
        self.assertEqual((SAMPLE, 'Current'), self.contents())
        self.now += self.cache.FRESH
        self.wire.side_effect = db.transport.TimedOut()
        self.refresh()
        self.refresh()
        self.assertEqual(2, self.wire.call_count)
        self.assertEqual((SAMPLE, 'Stale · node offline'), self.contents())
        self.now += self.cache.MAX_STALE
        self.assertEqual((None, 'Unavailable · node offline'), self.contents())
        self.wire.side_effect = None
        self.refresh()
        self.assertEqual((SAMPLE, 'Current'), self.contents())

    def test_failed_verification_drops_cached_data(self):
        self.refresh()
        self.now += self.cache.FRESH
        self.wire.return_value = (403, 'application/json', b'{}')
        self.refresh()
        self.assertEqual((None, 'Unavailable'), self.contents())

    def test_late_writer_cannot_restore_a_paused_then_resumed_snapshot(self):
        node, lease = self.cache._claim(db.LINK, self.now)
        self.assertIsNone(self.cache._claim(db.LINK, self.now))
        result = self.cache._fetch(node, 'admin')
        db.links.pause(db.LINK, 'admin')
        self.assertEqual([], list(self.cache.sources(self.active)))
        db.links.resume(db.LINK, 'admin')
        self.cache._finish(node, lease, result, self.now)
        self.assertEqual((None, 'Awaiting refresh'), self.contents())

    def test_snapshot_bound_to_identity_and_late_lease_excluded(self):
        node, old = self.cache._claim(db.LINK, self.now)
        result = self.cache._fetch(node, 'admin')
        self.now += self.cache.RETRY
        _, new = self.cache._claim(db.LINK, self.now)
        self.cache._finish(node, old, result, self.now)
        self.assertEqual((None, 'Refresh pending'), self.contents())
        self.cache._finish(node, new, result, self.now)
        self.alter(sealed='changed')
        self.assertIsNone(self.contents()[0])

    def test_parallel_claims_only_one_request_per_link(self):
        results = self.workers([lambda: self.cache._claim(db.LINK, self.now) for _ in range(4)])
        self.assertEqual(3, results.count(None))
        self.assertEqual(1, sum(isinstance(result, tuple) for result in results))

    def test_real_template_escapes_text_and_keeps_duplicate_sources(self):
        from django.template.loader import render_to_string
        row = ('example.test', 'Active', '<Node>', '/websites/example.test/workspace', 'Current')
        with patch('django.template.loader_tags.ExtendsNode.render', autospec=True) as extends:
            # Render only the content block, independent of the panel shell.
            extends.side_effect = lambda tag, context: tag.nodelist.render(context)
            html = render_to_string('multiServer/inventory.html', {
                'licensed': True, 'rows': [row, row], 'category': 'websites', 'query': '"<test>'})
        self.assertEqual(2, html.count('&lt;Node&gt;'))
        self.assertIn('ng-non-bindable', html)
        self.assertIn('&quot;&lt;test&gt;', html)


    def test_refresh_budget_moves_on_to_unvisited_nodes(self):
        from multiServer import models
        for i in range(self.cache.FANOUT + 1):
            models.Node.objects.create(link_id='%032x' % i, status=models.ACTIVE, sealed='invalid',
                                       created_at=self.now, updated_at=self.now)
        with patch.object(self.cache, '_fetch', return_value=(self.cache.OFFLINE, '')) as fetch:
            self.refresh()
            self.assertEqual(self.cache.FANOUT, fetch.call_count)
            self.refresh()
            self.assertEqual(self.cache.FANOUT + 2, fetch.call_count)
            self.refresh()
            self.assertEqual(self.cache.FANOUT + 2, fetch.call_count)

    def test_reader_rechecks_the_mapped_admin_and_bounds_the_projection(self):
        from websiteFunctions.models import Websites
        with patch('multiServer.views.active_full_administrator', return_value=None) as auth, \
                patch.object(Websites.objects, 'order_by') as order:
            with self.assertRaises(PermissionError):
                inventory.read(17, ('websites',))
            auth.assert_called_once_with(17)
            order.assert_not_called()
        with patch('multiServer.views.active_full_administrator', return_value=object()), \
                patch.object(Websites.objects, 'order_by') as order:
            query = order.return_value.values_list.return_value
            query.__getitem__.return_value = [('site%d.example' % i, 1) for i in range(inventory.ROW_LIMIT + 1)]
            batch = inventory.read(17, ('websites',))['websites']
            order.return_value.values_list.assert_called_once_with('domain', 'state')
            query.__getitem__.assert_called_once_with(slice(None, inventory.ROW_LIMIT + 1))
            self.assertTrue(batch['partial'])
            self.assertEqual(inventory.ROW_LIMIT, len(batch['rows']))

    def test_gateway_passes_only_the_verified_mapping_to_inventory(self):
        from multiServer import nodeGateway as gateway
        request = gateway.Verified(db.LINK, 23, 'other-actor', 'inventory', 'GET',
                                   'node.example:8090', inventory.PATH, '', '-', b'', '192.0.2.1')
        with patch.object(inventory, 'read', return_value=SAMPLE) as read:
            self.assertEqual((200, gateway.JSON, inventory.encode(SAMPLE)), gateway._dispatch(request, None, None))
            read.assert_called_once_with(23)
            for changed in (dict(mode='json'), dict(method='POST'), dict(query='page=2'),
                            dict(content_type='application/json'), dict(path=inventory.PATH + '/')):
                with self.subTest(changed=changed), self.assertRaises(gateway._Refused):
                    gateway._dispatch(request._replace(**changed), None, None)
            self.assertEqual(1, read.call_count)

