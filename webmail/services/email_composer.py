import email
from email.message import EmailMessage
from email.utils import formatdate, make_msgid, formataddr
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import mimetypes
import re


class EmailComposer:
    """Construct MIME messages for sending."""

    @staticmethod
    def compose(from_addr, to_addrs, subject, body_html='', body_text='',
                cc_addrs='', bcc_addrs='', attachments=None,
                in_reply_to='', references=''):
        """Build a MIME message.

        Args:
            from_addr: sender email
            to_addrs: comma-separated recipients
            subject: email subject
            body_html: HTML body content
            body_text: plain text body content
            cc_addrs: comma-separated CC recipients
            bcc_addrs: comma-separated BCC recipients
            attachments: list of (filename, content_type, bytes) tuples
            in_reply_to: Message-ID being replied to
            references: space-separated Message-IDs

        Returns:
            MIMEMultipart message ready for sending
        """
        if attachments:
            msg = MIMEMultipart('mixed')
            body_part = MIMEMultipart('alternative')
            if body_text:
                body_part.attach(MIMEText(body_text, 'plain', 'utf-8'))
            if body_html:
                body_part.attach(MIMEText(body_html, 'html', 'utf-8'))
            elif not body_text:
                body_part.attach(MIMEText('', 'plain', 'utf-8'))
            msg.attach(body_part)

            for filename, content_type, data in attachments:
                if not content_type:
                    content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
                maintype, subtype = content_type.split('/', 1)
                attachment = MIMEBase(maintype, subtype)
                attachment.set_payload(data)
                encoders.encode_base64(attachment)
                attachment.add_header('Content-Disposition', 'attachment', filename=filename)
                msg.attach(attachment)
        else:
            msg = MIMEMultipart('alternative')
            if body_text:
                msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
            if body_html:
                msg.attach(MIMEText(body_html, 'html', 'utf-8'))
            elif not body_text:
                msg.attach(MIMEText('', 'plain', 'utf-8'))

        msg['From'] = from_addr
        msg['To'] = to_addrs
        if cc_addrs:
            msg['Cc'] = cc_addrs
        msg['Subject'] = subject
        msg['Date'] = formatdate(localtime=True)
        msg['Message-ID'] = make_msgid(domain=from_addr.split('@')[-1] if '@' in from_addr else 'localhost')

        if in_reply_to:
            msg['In-Reply-To'] = in_reply_to
        if references:
            msg['References'] = references

        msg['MIME-Version'] = '1.0'
        msg['X-Mailer'] = 'CyberPanel Webmail'

        return msg

    @classmethod
    def compose_reply(cls, original, body_html, from_addr, reply_all=False):
        """Build a reply message from the original parsed message.

        Args:
            original: parsed message dict from EmailParser
            body_html: reply HTML body
            from_addr: sender email
            reply_all: whether to reply all

        Returns:
            MIMEMultipart message
        """
        to = original.get('from', '')
        cc = ''
        if reply_all:
            orig_to = original.get('to', '')
            orig_cc = original.get('cc', '')
            all_addrs = []
            if orig_to:
                all_addrs.append(orig_to)
            if orig_cc:
                all_addrs.append(orig_cc)
            cc = ', '.join(all_addrs)
            # Remove self from CC
            cc_parts = [a.strip() for a in cc.split(',') if from_addr not in a]
            cc = ', '.join(cc_parts)

        subject = original.get('subject', '')
        if not subject.lower().startswith('re:'):
            subject = 'Re: %s' % subject

        in_reply_to = original.get('message_id', '')
        references = original.get('references', '')
        if in_reply_to:
            references = ('%s %s' % (references, in_reply_to)).strip()

        # Quote original
        from html import escape as html_escape
        orig_date = html_escape(original.get('date', ''))
        orig_from = html_escape(original.get('from', ''))
        quoted = '<br><br><div class="wm-quoted">On %s, %s wrote:<br><blockquote>%s</blockquote></div>' % (
            orig_date, orig_from, original.get('body_html', '') or html_escape(original.get('body_text', ''))
        )
        full_html = body_html + quoted

        return cls.compose(
            from_addr=from_addr,
            to_addrs=to,
            subject=subject,
            body_html=full_html,
            cc_addrs=cc,
            in_reply_to=in_reply_to,
            references=references,
        )

    @classmethod
    def compose_forward(cls, original, body_html, from_addr, to_addrs):
        """Build a forward message including original attachments.

        Args:
            original: parsed message dict
            body_html: forward body HTML
            from_addr: sender email
            to_addrs: comma-separated recipients

        Returns:
            MIMEMultipart message (without attachments - caller must add them)
        """
        subject = original.get('subject', '')
        if not subject.lower().startswith('fwd:'):
            subject = 'Fwd: %s' % subject

        from html import escape as html_escape
        orig_from = html_escape(original.get('from', ''))
        orig_to = html_escape(original.get('to', ''))
        orig_date = html_escape(original.get('date', ''))
        orig_subject = html_escape(original.get('subject', ''))

        forwarded = (
            '<br><br><div class="wm-forwarded">'
            '---------- Forwarded message ----------<br>'
            'From: %s<br>'
            'Date: %s<br>'
            'Subject: %s<br>'
            'To: %s<br><br>'
            '%s</div>'
        ) % (orig_from, orig_date, orig_subject, orig_to,
             original.get('body_html', '') or html_escape(original.get('body_text', '')))

        full_html = body_html + forwarded

        return cls.compose(
            from_addr=from_addr,
            to_addrs=to_addrs,
            subject=subject,
            body_html=full_html,
        )
