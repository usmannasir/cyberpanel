import smtplib
import ssl


class SMTPClient:
    """Wrapper around smtplib.SMTP for sending mail via Postfix.

    Supports two modes:
    1. Authenticated (port 587 + STARTTLS) — for standalone login sessions
    2. Local relay (port 25, no auth) — for SSO sessions using master user
       Postfix accepts relay from localhost (permit_mynetworks in main.cf)
    """

    def __init__(self, email_address, password, host='localhost', port=587,
                 use_local_relay=False):
        self.email_address = email_address
        self.password = password
        self.host = host
        self.port = port
        self.use_local_relay = use_local_relay

    def send_message(self, mime_message):
        """Send a composed email via SMTP.

        Returns:
            dict: {success: bool, message_id: str or None, error: str or None}
        """
        try:
            if self.use_local_relay:
                # SSO mode: send via port 25 without auth
                # Postfix permits relay from localhost (permit_mynetworks)
                smtp = smtplib.SMTP(self.host, 25)
                smtp.ehlo()
                smtp.send_message(mime_message)
                smtp.quit()
            else:
                # Standalone mode: authenticated via port 587 + STARTTLS
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

                smtp = smtplib.SMTP(self.host, self.port)
                smtp.ehlo()
                smtp.starttls(context=ctx)
                smtp.ehlo()
                smtp.login(self.email_address, self.password)
                smtp.send_message(mime_message)
                smtp.quit()

            message_id = mime_message.get('Message-ID', '')
            return {'success': True, 'message_id': message_id}
        except smtplib.SMTPAuthenticationError as e:
            return {'success': False, 'message_id': None, 'error': 'Authentication failed: %s' % str(e)}
        except smtplib.SMTPRecipientsRefused as e:
            return {'success': False, 'message_id': None, 'error': 'Recipients refused: %s' % str(e)}
        except Exception as e:
            return {'success': False, 'message_id': None, 'error': str(e)}

    def save_to_sent(self, imap_client, raw_message):
        """Append sent message to the Sent folder via IMAP.

        CyberPanel's Dovecot uses INBOX.Sent as the Sent folder.
        """
        # Try CyberPanel's actual folder name first, then fallbacks
        sent_folders = ['INBOX.Sent', 'Sent', 'Sent Messages', 'Sent Items']
        for folder in sent_folders:
            try:
                if imap_client.append_message(folder, raw_message, '\\Seen'):
                    return True
            except Exception:
                continue
        try:
            imap_client.create_folder('INBOX.Sent')
            return imap_client.append_message('INBOX.Sent', raw_message, '\\Seen')
        except Exception:
            return False
