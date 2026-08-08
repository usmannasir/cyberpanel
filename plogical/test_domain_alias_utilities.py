import unittest

from plogical.domainAliasUtilities import merge_alias_names, remove_alias_from_map_line


class DomainAliasUtilitiesTests(unittest.TestCase):

    def test_current_and_legacy_aliases_are_merged_without_duplicates(self):
        aliases = merge_alias_names(
            ['current.example', 'shared.example'],
            ['legacy.example', 'shared.example'],
        )
        self.assertEqual(
            ['current.example', 'shared.example', 'legacy.example'],
            aliases,
        )

    def test_alias_is_removed_without_dropping_other_mapped_domains(self):
        line = '  map                     main.example main.example, first.example, remove.example, last.example\n'
        updated = remove_alias_from_map_line(line, 'main.example', 'remove.example')
        self.assertEqual(
            '  map                     main.example main.example, first.example, last.example\n',
            updated,
        )

    def test_other_maps_are_unchanged(self):
        line = '  map                     other.example other.example, remove.example\n'
        self.assertEqual(
            line,
            remove_alias_from_map_line(line, 'main.example', 'remove.example'),
        )


if __name__ == '__main__':
    unittest.main()
