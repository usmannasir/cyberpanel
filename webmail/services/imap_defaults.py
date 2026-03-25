class IMAPDefaults:
    """
    Minimal defaults shared with the folder settings store.

    Keep this separate from IMAPClient to avoid importing imaplib during settings reads.
    """

    SPECIAL_FOLDERS = {
        'sent': 'INBOX.Sent',
        'drafts': 'INBOX.Drafts',
        'trash': 'INBOX.Deleted Items',
        'junk': 'INBOX.Junk E-mail',
        'archive': 'INBOX.Archive',
    }

