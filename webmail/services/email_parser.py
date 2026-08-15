import email
import base64
import re
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

from bs4 import BeautifulSoup, Comment, Doctype

from .mime_utils import decode_mime_bytes, decode_mime_header


class EmailParser:
    """Parse MIME messages and sanitize HTML content."""

    SAFE_TAGS = {
        'a', 'abbr', 'b', 'blockquote', 'br', 'caption', 'cite', 'code',
        'col', 'colgroup', 'dd', 'del', 'details', 'div', 'dl', 'dt', 'em',
        'figcaption', 'figure', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr',
        'i', 'img', 'ins', 'li', 'mark', 'ol', 'p', 'pre', 'q', 's',
        'small', 'span', 'strong', 'sub', 'summary', 'sup', 'table',
        'tbody', 'td', 'tfoot', 'th', 'thead', 'tr', 'u', 'ul', 'wbr',
        'font', 'center', 'big',
    }

    SAFE_ATTRS = {
        'href', 'src', 'alt', 'title', 'width', 'height',
        'colspan', 'rowspan', 'cellpadding', 'cellspacing',
        'border', 'align', 'valign', 'bgcolor', 'color', 'size', 'face',
        'dir', 'lang', 'start', 'type', 'target', 'rel',
    }

    SAFE_HREF_SCHEMES = {'', 'http', 'https', 'mailto'}
    SAFE_SRC_SCHEMES = {'cid'}

    @staticmethod
    def _decode_header_value(value):
        return decode_mime_header(value)

    @classmethod
    def parse_message(cls, raw_bytes):
        """Parse raw email bytes into a structured dict."""
        if isinstance(raw_bytes, str):
            raw_bytes = raw_bytes.encode('utf-8')
        msg = email.message_from_bytes(raw_bytes)

        subject = cls._decode_header_value(msg.get('Subject', ''))
        from_addr = cls._decode_header_value(msg.get('From', ''))
        to_addr = cls._decode_header_value(msg.get('To', ''))
        cc_addr = cls._decode_header_value(msg.get('Cc', ''))
        date_str = msg.get('Date', '')
        message_id = msg.get('Message-ID', '')
        in_reply_to = msg.get('In-Reply-To', '')
        references = msg.get('References', '')

        date_iso = ''
        try:
            dt = parsedate_to_datetime(date_str)
            date_iso = dt.isoformat()
        except Exception:
            date_iso = date_str

        body_html = ''
        body_text = ''
        attachments = []
        part_idx = 0

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = str(part.get('Content-Disposition', ''))

                if content_type == 'multipart':
                    continue

                if 'attachment' in disposition or (content_type not in ('text/html', 'text/plain') and disposition):
                    filename = part.get_filename()
                    if filename:
                        filename = cls._decode_header_value(filename)
                    else:
                        filename = 'attachment_%d' % part_idx
                    attachments.append({
                        'part_id': part_idx,
                        'filename': filename,
                        'content_type': content_type,
                        'size': len(part.get_payload(decode=True) or b''),
                    })
                    part_idx += 1
                elif content_type == 'text/html':
                    payload = part.get_payload(decode=True)
                    body_html = decode_mime_bytes(
                        payload, part.get_content_charset())
                elif content_type == 'text/plain':
                    payload = part.get_payload(decode=True)
                    body_text = decode_mime_bytes(
                        payload, part.get_content_charset())
        else:
            content_type = msg.get_content_type()
            payload = msg.get_payload(decode=True)
            if payload:
                decoded = decode_mime_bytes(payload, msg.get_content_charset())
                if content_type == 'text/html':
                    body_html = decoded
                else:
                    body_text = decoded

        if body_html:
            body_html = cls.sanitize_html(body_html)

        preview = cls.extract_preview(body_text or body_html, 200)

        return {
            'subject': subject,
            'from': from_addr,
            'to': to_addr,
            'cc': cc_addr,
            'date': date_str,
            'date_iso': date_iso,
            'message_id': message_id,
            'in_reply_to': in_reply_to,
            'references': references,
            'body_html': body_html,
            'body_text': body_text,
            'attachments': attachments,
            'preview': preview,
            'has_attachments': len(attachments) > 0,
        }

    @classmethod
    def sanitize_html(cls, html):
        """Parse and sanitize an HTML email with a conservative allowlist."""
        if not html:
            return ''

        soup = BeautifulSoup(str(html), 'html.parser')
        for node in soup.find_all(string=lambda value: isinstance(value, (Comment, Doctype))):
            node.extract()

        for tag in list(soup.find_all(True)):
            name = str(tag.name or '').lower()
            if name in ('html', 'body'):
                tag.unwrap()
                continue
            if name not in cls.SAFE_TAGS:
                tag.decompose()
                continue

            sanitized_attributes = {}
            for raw_name, raw_value in list(tag.attrs.items()):
                attribute = str(raw_name).lower()
                if attribute not in cls.SAFE_ATTRS:
                    continue
                if isinstance(raw_value, (list, tuple)):
                    value = ' '.join(str(item) for item in raw_value)
                else:
                    value = str(raw_value)

                if attribute == 'href':
                    value = cls._sanitize_url(value, cls.SAFE_HREF_SCHEMES)
                elif attribute == 'src':
                    value = cls._sanitize_image_source(value)
                elif attribute == 'target':
                    value = '_blank' if value.lower() == '_blank' else '_self'
                sanitized_attributes[attribute] = value

            if name == 'a' and sanitized_attributes.get('target') == '_blank':
                sanitized_attributes['rel'] = 'noopener noreferrer'
            tag.attrs = sanitized_attributes

        return str(soup)

    @staticmethod
    def _sanitize_url(value, allowed_schemes):
        value = ''.join(character for character in value.strip() if ord(character) >= 0x20)
        try:
            scheme = urlsplit(value).scheme.lower()
        except ValueError:
            return ''
        return value if scheme in allowed_schemes else ''

    @classmethod
    def _sanitize_image_source(cls, value):
        value = ''.join(character for character in value.strip() if ord(character) >= 0x20)
        if value.startswith('//'):
            value = 'https:' + value
        try:
            scheme = urlsplit(value).scheme.lower()
        except ValueError:
            return ''
        if scheme in ('http', 'https'):
            encoded_url = base64.urlsafe_b64encode(value.encode('utf-8')).decode('ascii')
            return '/webmail/api/proxyImage?url=%s' % encoded_url
        return value if scheme in cls.SAFE_SRC_SCHEMES else ''

    @staticmethod
    def extract_preview(text, max_length=200):
        """Extract a short text preview from email body."""
        if not text:
            return ''
        # Strip HTML tags if present
        clean = re.sub(r'<[^>]+>', ' ', text)
        # Collapse whitespace
        clean = re.sub(r'\s+', ' ', clean).strip()
        if len(clean) > max_length:
            return clean[:max_length] + '...'
        return clean
