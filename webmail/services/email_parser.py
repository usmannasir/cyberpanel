import email
import re
from email.header import decode_header
from email.utils import parsedate_to_datetime


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
        'href', 'src', 'alt', 'title', 'width', 'height', 'style',
        'class', 'id', 'colspan', 'rowspan', 'cellpadding', 'cellspacing',
        'border', 'align', 'valign', 'bgcolor', 'color', 'size', 'face',
        'dir', 'lang', 'start', 'type', 'target', 'rel',
    }

    DANGEROUS_CSS_PATTERNS = [
        re.compile(r'expression\s*\(', re.IGNORECASE),
        re.compile(r'javascript\s*:', re.IGNORECASE),
        re.compile(r'vbscript\s*:', re.IGNORECASE),
        re.compile(r'url\s*\(\s*["\']?\s*javascript:', re.IGNORECASE),
        re.compile(r'-moz-binding', re.IGNORECASE),
        re.compile(r'behavior\s*:', re.IGNORECASE),
    ]

    @staticmethod
    def _decode_header_value(value):
        if value is None:
            return ''
        decoded_parts = decode_header(value)
        result = []
        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                result.append(part.decode(charset or 'utf-8', errors='replace'))
            else:
                result.append(part)
        return ''.join(result)

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
                    charset = part.get_content_charset() or 'utf-8'
                    body_html = payload.decode(charset, errors='replace') if payload else ''
                elif content_type == 'text/plain':
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or 'utf-8'
                    body_text = payload.decode(charset, errors='replace') if payload else ''
        else:
            content_type = msg.get_content_type()
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or 'utf-8'
            if payload:
                decoded = payload.decode(charset, errors='replace')
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
        """Whitelist-based HTML sanitization. Strips dangerous content."""
        if not html:
            return ''

        # Remove script, style, iframe, object, embed, form tags and their content
        for tag in ['script', 'style', 'iframe', 'object', 'embed', 'form', 'applet', 'base', 'link', 'meta']:
            html = re.sub(r'<%s\b[^>]*>.*?</%s>' % (tag, tag), '', html, flags=re.IGNORECASE | re.DOTALL)
            html = re.sub(r'<%s\b[^>]*/?\s*>' % tag, '', html, flags=re.IGNORECASE)

        # Remove event handler attributes (on*)
        html = re.sub(r'\s+on\w+\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s>]+)', '', html, flags=re.IGNORECASE)

        # Remove javascript: and data: URIs in href/src
        html = re.sub(r'(href|src)\s*=\s*["\']?\s*javascript:[^"\'>\s]*["\']?', r'\1=""', html, flags=re.IGNORECASE)
        html = re.sub(r'(href|src)\s*=\s*["\']?\s*data:[^"\'>\s]*["\']?', r'\1=""', html, flags=re.IGNORECASE)
        html = re.sub(r'(href|src)\s*=\s*["\']?\s*vbscript:[^"\'>\s]*["\']?', r'\1=""', html, flags=re.IGNORECASE)

        # Sanitize style attributes - remove dangerous CSS
        def clean_style(match):
            style = match.group(1)
            for pattern in cls.DANGEROUS_CSS_PATTERNS:
                if pattern.search(style):
                    return 'style=""'
            return match.group(0)

        html = re.sub(r'style\s*=\s*"([^"]*)"', clean_style, html, flags=re.IGNORECASE)
        html = re.sub(r"style\s*=\s*'([^']*)'", clean_style, html, flags=re.IGNORECASE)

        # Rewrite external image src to proxy endpoint
        def proxy_image(match):
            src = match.group(1)
            if src.startswith(('http://', 'https://')):
                from django.utils.http import urlencode
                import base64
                encoded_url = base64.urlsafe_b64encode(src.encode()).decode()
                return 'src="/webmail/api/proxyImage?url=%s"' % encoded_url
            return match.group(0)

        html = re.sub(r'src\s*=\s*"(https?://[^"]*)"', proxy_image, html, flags=re.IGNORECASE)

        return html

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
