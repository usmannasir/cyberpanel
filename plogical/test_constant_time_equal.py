"""Two secrets are compared without telling where they differ, whatever characters they hold."""
import unittest

from plogical.securityUtils import constant_time_equal


class ConstantTimeEqualTests(unittest.TestCase):

    def test_equal_values_are_equal_and_others_are_not(self):
        self.assertTrue(constant_time_equal('cp_key_0123456789', 'cp_key_0123456789'))
        self.assertTrue(constant_time_equal('', ''))
        self.assertTrue(constant_time_equal(1234, '1234'))
        self.assertFalse(constant_time_equal('cp_key_0123456789', 'cp_key_0123456780'))
        self.assertFalse(constant_time_equal('cp_key', 'cp_key_'))
        self.assertFalse(constant_time_equal('cp_key', ''))

    def test_a_missing_value_is_never_equal(self):
        self.assertFalse(constant_time_equal(None, None))
        self.assertFalse(constant_time_equal(None, 'cp_key'))
        self.assertFalse(constant_time_equal('cp_key', None))
        self.assertFalse(constant_time_equal('None', None))

    def test_text_outside_ascii_is_compared_and_not_an_error(self):
        self.assertFalse(constant_time_equal('cl\xe9', 'cp_key'))
        self.assertFalse(constant_time_equal('cp_key', 'cl\xe9'))
        self.assertFalse(constant_time_equal('\xff\xfe', 'cp_key'))
        self.assertTrue(constant_time_equal('cl\xe9 م\U0001f600', 'cl\xe9 م\U0001f600'))
        self.assertFalse(constant_time_equal('cl\xe9', 'cl\xe8'))
        # Half a character is a value too, and never equal to the text that spells it.
        self.assertFalse(constant_time_equal('\udcff', 'cp_key'))
        self.assertTrue(constant_time_equal('\udcff', '\udcff'))
        self.assertFalse(constant_time_equal('\udcff', '\\udcff'))
        self.assertFalse(constant_time_equal('\udcff', '\xed\xb3\xbf'))


if __name__ == '__main__':
    unittest.main()
