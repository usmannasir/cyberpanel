"""A DKIM key pair is stored once per registrable domain: only the owner of every site under it may use it."""
import json
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from plogical.test_child_domain_conversion import load_method

PUBLIC = 'default._domainkey IN TXT ( "v=DKIM1; k=rsa; " "p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA" ) ;'


class Table:
    """The two ORM calls the ownership rule makes."""

    def __init__(self, *domains):
        self.domains = domains
        self.objects = self

    def filter(self, domain=None, domain__endswith=None):
        if domain is not None:
            found = [name for name in self.domains if name == domain]
        else:
            found = [name for name in self.domains if name.endswith(domain__endswith)]
        return SimpleNamespace(values_list=lambda field, flat: found)


def ownership_rule(websites, children, owned):
    acl = SimpleNamespace(checkOwnership=lambda name, admin, current: 1 if name in owned else 0)
    rule = load_method('plogical/acl.py', 'ACLManager', 'ownsEverySiteUnder',
                       dict(Websites=Table(*websites), ChildDomains=Table(*children), ACLManager=acl))
    return lambda domain, current=None: rule(domain, 'caller', current or {'admin': 0})


class OwnershipRuleTests(unittest.TestCase):
    def test_owner_of_every_site_under_the_domain_qualifies(self):
        rule = ownership_rule(['example.com', 'unrelated.org'], ['mail.example.com'],
                              owned={'example.com', 'mail.example.com'})
        self.assertEqual(1, rule('example.com'))

    def test_one_site_of_another_customer_under_the_domain_disqualifies(self):
        # The caller added a child domain under someone else's website.
        rule = ownership_rule(['victim.com', 'attacker.net'], ['x.victim.com'],
                              owned={'attacker.net', 'x.victim.com'})
        self.assertEqual(0, rule('victim.com'))
        # Two customers each host a subdomain of the same registrable domain.
        rule = ownership_rule(['a.shared.example', 'b.shared.example'], [], owned={'a.shared.example'})
        self.assertEqual(0, rule('shared.example'))

    def test_only_names_at_or_under_the_domain_are_considered(self):
        rule = ownership_rule(['example.com', 'notexample.com', 'example.com.attacker.net'], [],
                              owned={'example.com'})
        self.assertEqual(1, rule('example.com'))

    def test_domain_with_no_hosted_site_belongs_to_no_customer(self):
        self.assertEqual(0, ownership_rule(['other.org'], [], owned={'other.org'})('example.com'))

    def test_administrator_always_qualifies(self):
        rule = ownership_rule(['victim.com'], [], owned=set())
        self.assertEqual(1, rule('victim.com', {'admin': 1}))
        self.assertEqual(0, rule('victim.com', {'admin': 0}))
        self.assertEqual(0, rule('victim.com', {}))


class DKIMHandlerTests(unittest.TestCase):
    def setUp(self):
        self.namespace = {'json': json, 'parse_dkim_public_key': lambda output: 'public-key',
                          'HttpResponse': lambda content: SimpleNamespace(content=content.encode())}
        for name in ('ACLManager', 'Administrator', 'ProcessUtilities', 'DNS', 'dnsDomains',
                     'virtualHostUtilities'):
            self.namespace[name] = MagicMock()
        acl = self.namespace['ACLManager']
        acl.currentContextPermission.return_value = 1
        acl.checkOwnership.return_value = 1
        acl.loadErrorJson.side_effect = lambda *arguments: SimpleNamespace(
            content=json.dumps({'status': 0, 'refused': list(arguments)}).encode())
        self.namespace['DNS'].createDKIMRecords.return_value = 1
        self.namespace['virtualHostUtilities'].cyberPanel = '/usr/local/CyberCP'
        self.root = self.namespace['ProcessUtilities']
        extractor = SimpleNamespace(TLDExtract=lambda cache_dir=None: lambda name: SimpleNamespace(
            domain=name.split('.')[-2], suffix=name.split('.')[-1]))
        modules = patch.dict('sys.modules', {'tldextract': extractor})
        modules.start()
        self.addCleanup(modules.stop)

    def call(self, method, owns):
        self.namespace['ACLManager'].ownsEverySiteUnder.return_value = owns
        handler = load_method('mailServer/mailserverManager.py', 'MailServerManager', method, self.namespace)
        request = SimpleNamespace(session={'userID': 7}, body=json.dumps({'domainName': 'x.victim.com'}).encode())
        return json.loads(handler(SimpleNamespace(request=request)).content)

    def commands(self):
        return [call[0][0] for call in self.root.outputExecutioner.call_args_list]

    def test_key_of_a_domain_shared_with_another_customer_is_not_read(self):
        result = self.call('fetchDKIMKeys', owns=0)
        self.assertEqual(0, result['status'])
        self.assertNotIn('privateKey', result)
        self.assertEqual([], self.commands())
        self.namespace['DNS'].createDKIMRecords.assert_not_called()
        asked = self.namespace['ACLManager'].ownsEverySiteUnder.call_args[0]
        self.assertEqual('victim.com', asked[0])

    def test_owner_of_every_site_still_receives_the_keys(self):
        self.root.outputExecutioner.side_effect = [PUBLIC, 'private-key']
        result = self.call('fetchDKIMKeys', owns=1)
        self.assertEqual((1, 'public-key', 'private-key'),
                         (result['keysAvailable'], result['publicKey'], result['privateKey']))
        self.assertEqual(['sudo cat /etc/opendkim/keys/victim.com/default.txt',
                          'sudo cat /etc/opendkim/keys/victim.com/default.private'], self.commands())

    def test_key_is_not_generated_for_a_domain_shared_with_another_customer(self):
        result = self.call('generateDKIMKeys', owns=0)
        self.assertEqual(0, result['status'])
        self.assertEqual([], self.commands())
        self.namespace['DNS'].dnsTemplate.assert_not_called()

    def test_owner_of_every_site_still_generates_keys(self):
        self.root.outputExecutioner.side_effect = ['1,None', PUBLIC]
        result = self.call('generateDKIMKeys', owns=1)
        self.assertEqual(1, result['generateStatus'])
        self.assertIn('generateKeys --domain x.victim.com', self.commands()[0])


if __name__ == '__main__':
    unittest.main()
