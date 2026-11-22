"""What a panel user may be called.

Until now the name of a new user was stored as typed. A new name is held to
one written rule. Users created before the rule existed keep signing in and
working under the name they have: wherever the name is handed on it is
quoted, a file kept for a user is named through `file_for_user`, and an
owner recreated from a backup is held to `stored_name_is_usable`.
"""
import os
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


# A name that is a plain part of a file name, whatever follows or precedes it.
_FILE_NAME_PART = re.compile(r'[A-Za-z0-9._@-]+')


def file_for_user(prefix, user):
    """Path of the file a feature keeps for a panel user: `prefix` followed by what stands for the user.

    A name made of letters, digits and . _ @ - stands for itself, so the file
    such a user always had is kept. Any other name gets a file named after the
    user's number; the comma keeps it apart from every file of the first kind.
    """
    name = user.userName
    if isinstance(name, str) and _FILE_NAME_PART.fullmatch(name) is not None:
        return prefix + name
    return '%s,%d' % (prefix, int(user.pk))


def existing_file_for_user(prefix, user):
    """The file to read for this user, or None when the user has none.

    A user whose name is not a plain part of a file name may still have the
    file an earlier release wrote under the name itself. It is read only when
    the name cannot lead out of the directory.
    """
    path = file_for_user(prefix, user)
    if os.path.isfile(path):
        return path
    name = user.userName
    if isinstance(name, str) and name and '/' not in name and '\x00' not in name:
        earlier = prefix + name
        if earlier != path and os.path.isfile(earlier) and not os.path.islink(earlier):
            return earlier
    return None
