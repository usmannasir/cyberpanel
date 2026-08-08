import pathlib
import re
import unittest


class DomainAliasTemplateTests(unittest.TestCase):

    def test_create_and_delete_use_alias_actions(self):
        template = (
            pathlib.Path(__file__).with_name('templates')
            / 'websiteFunctions'
            / 'domainAlias.html'
        ).read_text(encoding='utf-8')

        self.assertIn('ng-click="addAliasFunc()"', template)
        self.assertIn('ng-model="aliasDomain"', template)
        self.assertIn('confirmRemoveAlias', template)
        self.assertIn('{% for alias in aliases %}', template)
        self.assertIsNone(re.search(r'ng-click="createDomain\(\)"', template))
        self.assertIsNone(re.search(r'ng-model="domainNameCreate"', template))

    def test_both_static_copies_initialize_the_master_domain(self):
        repository = pathlib.Path(__file__).parents[1]
        copies = (
            repository / 'static' / 'websiteFunctions' / 'websiteFunctions.js',
            pathlib.Path(__file__).with_name('static') / 'websiteFunctions' / 'websiteFunctions.js',
        )
        for javascript_path in copies:
            javascript = javascript_path.read_text(encoding='utf-8')
            controller = javascript[javascript.index("app.controller('manageAliasController'"):]
            self.assertIn('var masterDomain = ($("#domainNamePage").text() || "").trim();', controller)
            self.assertIn('$scope.confirmRemoveAlias', controller)


if __name__ == '__main__':
    unittest.main()
