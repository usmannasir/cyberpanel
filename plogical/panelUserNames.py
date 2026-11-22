"""What a panel user may be called.

Until now the name of a new user was stored as typed. A new name is held to
one written rule. Users created before the rule existed keep signing in and
working under the name they have; features that hand the name on check
`stored_name_is_usable` and refuse a name they cannot carry instead of
passing it along.
"""
import re

from plogical import databaseAccounts

NAME_RULE = ('A user name starts with a letter or a number, may contain letters, numbers, '
             'dots, dashes, underscores and @, and is 50 characters long at most.')

_NEW_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9._@-]{0,49}')

# Names earlier releases accepted and people chose in good faith: letters of
# any alphabet, numbers, and . _ @ + - or spaces inside the name.
_STORED_NAME = re.compile(r'\w(?:[\w.@+ -]{0,48}[\w.@+-])?')


def new_name_refusal(name):
    """Why a new panel user may not have this name; None when it may."""
    if not isinstance(name, str) or _NEW_NAME.fullmatch(name) is None:
        return NAME_RULE
    if databaseAccounts.is_system_account(name):
        return 'This user name is reserved for the server. Choose another name.'
    return None


def stored_name_is_usable(name):
    """True when the name of an existing user can be handed to other parts of the panel."""
    return isinstance(name, str) and _STORED_NAME.fullmatch(name) is not None
