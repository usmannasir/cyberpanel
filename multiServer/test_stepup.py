"""The password and one-time code asked again before a link is made, ended or the role is changed.

The cases that need the administrator's row run on a real MariaDB, on a
server marked as a disposable test server (multiServer/testing.py).
"""
import ast
import json
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch

from multiServer import stepup, test_gateway, testing

SKIP = testing.unavailable()
if SKIP is None:
    from django.db import connection
    from loginSystem.models import Administrator
    Base = test_gateway.Panel
else:
    Base = unittest.TestCase

SECRET = 'JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP'
PASSWORD = 'correct horse; battery $taple'
NOW = 1794999990  # the start of a half minute


def code(step):
    import pyotp
    return pyotp.TOTP(SECRET).generate_otp(step)


class Clock(object):
    def __init__(self):
        self.now = NOW

    def time(self):
        return self.now + 0.4


class CodeTests(unittest.TestCase):
    STEP = NOW // 30

    def test_a_code_stands_for_its_half_minute_and_the_one_before_and_after(self):
        self.assertEqual(0, NOW % 30)
        for offset in (-1, 0, 1):
            self.assertEqual(self.STEP + offset, stepup._step(SECRET, code(self.STEP + offset), NOW, 0))
            self.assertEqual(self.STEP + offset, stepup._step(SECRET, code(self.STEP + offset), NOW + 29, 0))
        for offset in (-2, 2, 100):
            self.assertIsNone(stepup._step(SECRET, code(self.STEP + offset), NOW, 0))

    def test_a_code_is_not_accepted_at_or_before_the_half_minute_of_the_last_one(self):
        self.assertIsNone(stepup._step(SECRET, code(self.STEP), NOW, self.STEP))
        self.assertIsNone(stepup._step(SECRET, code(self.STEP - 1), NOW, self.STEP))
        self.assertEqual(self.STEP + 1, stepup._step(SECRET, code(self.STEP + 1), NOW, self.STEP))
        self.assertIsNone(stepup._step(SECRET, code(self.STEP + 1), NOW, self.STEP + 1))

    def test_only_six_digits_are_a_code(self):
        right = code(self.STEP)
        for wrong in ('', right[:5], right + '0', ' ' + right, right + '\n', right.encode(), int(right), None,
                      '١' * 6, [right]):
            self.assertIsNone(stepup._step(SECRET, wrong, NOW, 0), repr(wrong))

    def test_what_is_kept_is_three_small_numbers_or_nothing(self):
        self.assertEqual((2, NOW, 7), stepup._kept([2, NOW, 7]))
        for other in (None, {}, [], [1, 2], [1, 2, 3, 4], ['1', 2, 3], [1.0, 2, 3], [True, 2, 3], [-1, 2, 3],
                      [1, 10 ** 11, 3], 'abc', 5):
            self.assertEqual((0, 0, 0), stepup._kept(other), repr(other))

    def test_the_words_for_a_refusal_are_fixed_and_say_nothing_of_what_was_typed(self):
        self.assertEqual(stepup.LOCKED, stepup.message('not_allowed'))
        for reason in ('password', 'two_factor', 'admin', 'internal'):
            self.assertEqual(stepup.WRONG, stepup.message(reason))
        self.assertIn('15 minutes', stepup.LOCKED)

    @unittest.skipUnless(sys.version_info >= (3, 8), 'ast cannot check an older grammar before Python 3.8')
    def test_sources_parse_as_python_3_6(self):
        directory = Path(__file__).resolve().parent
        for name in ('stepup.py', 'test_stepup.py'):
            ast.parse((directory / name).read_text(), feature_version=(3, 6))


@unittest.skipIf(SKIP, SKIP)
class ConfirmTests(Base):
    """An administrator with a password and a second factor, in the panel's own table."""

    def setUp(self):
        super().setUp()
        from plogical import hashPassword
        Administrator.objects.filter(pk=self.administrator.pk).update(
            password=hashPassword.hash_password(PASSWORD), twoFA=1, secretKey=SECRET,
            config=json.dumps({'onboarding': 1}))
        self.time = self.start(patch.object(stepup, 'time', Clock()))
        self.step = NOW // 30

    def confirm(self, password=PASSWORD, offset=0, **given):
        return stepup.confirm(given.get('admin_id', self.administrator.pk), password,
                              given.get('code', code(self.step + offset)))

    def kept(self):
        return json.loads(Administrator.objects.get(pk=self.administrator.pk).config)

    def at_once(self, calls):
        """Every call at the same moment, each in a thread with a database connection of its own."""
        outcomes, together = [None] * len(calls), threading.Barrier(len(calls))

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

    def test_the_right_password_and_a_new_code_pass_and_the_same_code_does_not_pass_again(self):
        self.assertIsNone(self.confirm())
        self.assertEqual({'onboarding': 1, stepup.KEPT_AS: [0, 0, self.step]}, self.kept())
        self.assertEqual('two_factor', self.confirm())
        # Nor an older one that would still have been in time.
        self.assertEqual('two_factor', self.confirm(offset=-1))
        self.assertIsNone(self.confirm(offset=1))
        self.assertEqual('two_factor', self.confirm(offset=1))
        self.time.now += 60
        self.assertIsNone(self.confirm(offset=2))

    def test_a_wrong_password_or_code_is_counted_and_the_fifth_shuts_the_account_out_for_the_window(self):
        self.assertEqual('password', self.confirm('not the password'))
        self.assertEqual('password', self.confirm(''))
        self.assertEqual('two_factor', self.confirm(code='000000'))
        self.assertEqual('two_factor', self.confirm(code='12345'))
        self.assertEqual([4, NOW, 0], self.kept()[stepup.KEPT_AS])
        self.time.now += 100
        self.assertEqual('password', self.confirm(None))
        self.assertEqual([5, NOW, 0], self.kept()[stepup.KEPT_AS])
        # Now not even the right password with a good code is looked at.
        with patch('plogical.hashPassword.check_password') as checked:
            for unused in range(3):
                self.assertEqual('not_allowed', self.confirm())
            checked.assert_not_called()
        self.assertEqual([5, NOW, 0], self.kept()[stepup.KEPT_AS])
        self.time.now = NOW + stepup.WINDOW - 1
        self.assertEqual('not_allowed', self.confirm(offset=29))
        self.time.now = NOW + stepup.WINDOW
        self.step = self.time.now // 30
        self.assertIsNone(self.confirm())
        self.assertEqual([0, 0, self.step], self.kept()[stepup.KEPT_AS])

    def test_a_pass_clears_the_count(self):
        for unused in range(4):
            self.assertEqual('password', self.confirm('wrong'))
        self.assertIsNone(self.confirm())
        for unused in range(4):
            self.assertEqual('two_factor', self.confirm())
        self.assertIsNone(self.confirm(offset=1))

    def test_the_cap_holds_when_every_worker_is_asked_at_the_same_moment(self):
        outcomes = self.at_once([lambda: self.confirm('wrong')] * 12)
        self.assertEqual(['not_allowed'] * 7 + ['password'] * 5, sorted(outcomes))
        self.assertEqual([5, NOW, 0], self.kept()[stepup.KEPT_AS])

    def test_one_code_passes_once_when_every_worker_is_given_it_at_the_same_moment(self):
        outcomes = self.at_once([self.confirm] * 8)
        # The first to be looked at passes. The same code again is refused, but it is the right code
        # (a form sent twice), so it is not counted as an attempt to guess one.
        self.assertEqual((1, 7, 0), tuple(outcomes.count(outcome) for outcome in (None, 'two_factor', 'not_allowed')))
        self.assertEqual([0, 0, self.step], self.kept()[stepup.KEPT_AS])

    def test_a_code_used_before_is_refused_without_counting_and_a_wrong_code_still_counts(self):
        self.assertIsNone(self.confirm())
        for unused in range(8):
            self.assertEqual('two_factor', self.confirm())
        self.assertEqual([0, 0, self.step], self.kept()[stepup.KEPT_AS])
        for unused in range(5):
            self.assertEqual('two_factor', self.confirm(code='000000' if code(self.step) != '000000' else '111111'))
        self.assertEqual('not_allowed', self.confirm(offset=1))

    def test_only_an_active_full_administrator_with_a_second_factor_is_checked_at_all(self):
        with patch('plogical.hashPassword.check_password') as checked:
            for admin_id in (None, '1', True, self.administrator.pk + 100):
                self.assertEqual('admin', self.confirm(admin_id=admin_id))
            for change in (dict(acl=self.reseller), dict(state='SUSPENDED'), dict(twoFA=0), dict(secretKey='None'),
                           dict(secretKey='')):
                before = Administrator.objects.filter(pk=self.administrator.pk).values(*change)[0]
                Administrator.objects.filter(pk=self.administrator.pk).update(**change)
                self.assertEqual('admin', self.confirm(), change)
                Administrator.objects.filter(pk=self.administrator.pk).update(**before)
            checked.assert_not_called()
        self.assertEqual({'onboarding': 1}, self.kept())
        self.assertIsNone(self.confirm())

    def test_nothing_typed_is_kept_and_the_other_settings_of_the_account_stay(self):
        self.assertEqual('password', self.confirm('planted-password-1'))
        self.assertEqual('two_factor', self.confirm(code='918273'))
        self.assertIsNone(self.confirm())
        row = repr(Administrator.objects.filter(pk=self.administrator.pk).values()[0])
        for typed in ('planted-password-1', '918273', code(self.step)):
            self.assertNotIn(typed, row.replace(repr(SECRET), ''))
        self.assertEqual(1, self.kept()['onboarding'])
        self.assertEqual([], self.log)

    def test_settings_that_are_not_an_object_refuse_and_are_left_alone(self):
        for text in ('not json', '[]', '"text"'):
            Administrator.objects.filter(pk=self.administrator.pk).update(config=text)
            self.assertEqual('internal', self.confirm())
            self.assertEqual(text, Administrator.objects.get(pk=self.administrator.pk).config)
        Administrator.objects.filter(pk=self.administrator.pk).update(config='')
        self.assertIsNone(self.confirm())



@unittest.skipIf(SKIP, SKIP)
class PasswordOnlyTests(Base):
    """An administrator without a second factor, as on a managed server."""

    def setUp(self):
        super().setUp()
        from plogical import hashPassword
        Administrator.objects.filter(pk=self.administrator.pk).update(
            password=hashPassword.hash_password(PASSWORD), twoFA=0, secretKey='None', config='{}')
        self.time = self.start(patch.object(stepup, 'time', Clock()))

    def kept(self):
        return json.loads(Administrator.objects.get(pk=self.administrator.pk).config).get(stepup.KEPT_AS)

    def test_the_password_alone_passes_only_where_a_second_factor_is_not_required(self):
        self.assertEqual('admin', stepup.confirm(self.administrator.pk, PASSWORD, ''))
        self.assertIsNone(stepup.confirm(self.administrator.pk, PASSWORD, '', two_factor=False))
        self.assertEqual([0, 0, 0], self.kept())
        # Passes again: there is no code to be used up.
        self.assertIsNone(stepup.confirm(self.administrator.pk, PASSWORD, '', two_factor=False))

    def test_a_wrong_password_is_counted_and_the_fifth_shuts_the_account_out(self):
        for unused in range(5):
            self.assertEqual('password', stepup.confirm(self.administrator.pk, 'wrong', '', two_factor=False))
        self.assertEqual('not_allowed', stepup.confirm(self.administrator.pk, PASSWORD, '', two_factor=False))
        self.time.now = NOW + stepup.WINDOW
        self.assertIsNone(stepup.confirm(self.administrator.pk, PASSWORD, '', two_factor=False))

    def test_an_account_with_a_second_factor_still_needs_a_code_where_it_is_not_required(self):
        Administrator.objects.filter(pk=self.administrator.pk).update(twoFA=1, secretKey=SECRET)
        self.assertEqual('two_factor', stepup.confirm(self.administrator.pk, PASSWORD, '', two_factor=False))
        self.assertIsNone(stepup.confirm(self.administrator.pk, PASSWORD, code(NOW // 30), two_factor=False))

    def test_the_message_asks_for_a_code_only_from_an_account_that_has_one(self):
        admin = Administrator.objects.get(pk=self.administrator.pk)
        self.assertEqual(stepup.WRONG_PASSWORD, stepup.message('password', admin))
        self.assertEqual(stepup.LOCKED, stepup.message('not_allowed', admin))
        Administrator.objects.filter(pk=self.administrator.pk).update(twoFA=1, secretKey=SECRET)
        self.assertEqual(stepup.WRONG, stepup.message('password', Administrator.objects.get(pk=self.administrator.pk)))


class Request(object):
    """What check() reads of a request: the session, the form, and whether it came over HTTPS."""

    def __init__(self, **post):
        self.session, self.POST = {}, post

    def is_secure(self):
        return False


@unittest.skipIf(SKIP, SKIP)
class RecentTests(Base):
    """A confirmation counts for RECENT seconds in its own session, for its own account, as it was made."""

    def setUp(self):
        super().setUp()
        from plogical import hashPassword
        Administrator.objects.filter(pk=self.administrator.pk).update(
            password=hashPassword.hash_password(PASSWORD), twoFA=1, secretKey=SECRET, config='{}')
        self.time = self.start(patch.object(stepup, 'time', Clock()))
        self.request = Request(password=PASSWORD, code=code(NOW // 30))

    def admin(self):
        return Administrator.objects.get(pk=self.administrator.pk)

    def test_after_a_check_nothing_is_asked_for_the_window_and_then_it_is_asked_again(self):
        self.assertFalse(stepup.recent(self.request, self.admin()))
        self.assertIsNone(stepup.check(self.request, self.admin()))
        self.assertTrue(stepup.recent(self.request, self.admin()))
        self.request.POST = {}
        self.time.now = NOW + stepup.RECENT - 1
        self.assertIsNone(stepup.check(self.request, self.admin()))
        self.time.now = NOW + stepup.RECENT
        self.assertFalse(stepup.recent(self.request, self.admin()))
        self.assertEqual('password', stepup.check(self.request, self.admin()))

    def test_it_counts_for_that_account_only_and_ends_with_a_new_password_or_second_factor(self):
        self.assertIsNone(stepup.check(self.request, self.admin()))
        other = self.admin()
        other.pk += 100
        self.assertFalse(stepup.recent(self.request, other))
        from plogical import hashPassword
        Administrator.objects.filter(pk=self.administrator.pk).update(password=hashPassword.hash_password('new one'))
        self.assertFalse(stepup.recent(self.request, self.admin()))
        Administrator.objects.filter(pk=self.administrator.pk).update(password=hashPassword.hash_password(PASSWORD))
        self.request.POST = {'password': PASSWORD, 'code': code(NOW // 30 + 1)}
        self.assertIsNone(stepup.check(self.request, self.admin()))
        Administrator.objects.filter(pk=self.administrator.pk).update(secretKey='KRSXG5CTMVRXEZLUKRSXG5CTMVRXEZLU')
        self.assertFalse(stepup.recent(self.request, self.admin()))

    def test_a_check_with_the_password_alone_never_stands_in_for_one_that_needs_a_code(self):
        Administrator.objects.filter(pk=self.administrator.pk).update(twoFA=0, secretKey='None')
        self.request.POST = {'password': PASSWORD}
        self.assertIsNone(stepup.check(self.request, self.admin(), two_factor=False))
        self.assertTrue(stepup.recent(self.request, self.admin(), two_factor=False))
        self.assertFalse(stepup.recent(self.request, self.admin()))
        # Turning two-factor on in the same session does not make that check one made with a code.
        Administrator.objects.filter(pk=self.administrator.pk).update(twoFA=1, secretKey=SECRET)
        self.assertFalse(stepup.recent(self.request, self.admin()))
        self.assertFalse(stepup.recent(self.request, self.admin(), two_factor=False))

    def test_an_account_with_a_second_factor_is_never_let_through_by_a_check_without_a_code(self):
        # As a sign-in that skipped the code would leave it: the same account, a check without a code.
        stepup.remember(self.request, self.admin(), False)
        self.assertFalse(stepup.recent(self.request, self.admin(), two_factor=False))
        self.request.POST = {}
        self.assertEqual('password', stepup.check(self.request, self.admin(), two_factor=False))

    def test_what_is_kept_is_checked_and_holds_nothing_typed(self):
        self.assertIsNone(stepup.check(self.request, self.admin()))
        kept = self.request.session[stepup.SESSION_KEY]
        self.assertEqual([self.administrator.pk, NOW, True], kept[:3])
        for typed in (PASSWORD, code(NOW // 30)):
            self.assertNotIn(typed, repr(kept))
        for broken in (None, [], kept[:3], [str(kept[0])] + kept[1:], [kept[0], NOW + 1.5] + kept[2:],
                       kept[:2] + [1] + kept[3:], kept[:3] + ['x' * 64], kept[:1] + [NOW + 60] + kept[2:]):
            self.request.session[stepup.SESSION_KEY] = broken
            self.assertFalse(stepup.recent(self.request, self.admin()), repr(broken))
        stepup.forget(self.request)
        self.assertNotIn(stepup.SESSION_KEY, self.request.session)

    def test_a_refused_check_remembers_nothing(self):
        self.request.POST = {'password': 'wrong', 'code': code(NOW // 30)}
        self.assertEqual('password', stepup.check(self.request, self.admin()))
        self.assertNotIn(stepup.SESSION_KEY, self.request.session)

if __name__ == '__main__':
    unittest.main()
