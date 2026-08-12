import json

from plogical.securityUtils import is_safe_numeric_id


def parse_remote_transfer_response(response):
    """Return a validated remote-transfer result without leaking response details."""
    try:
        payload = json.loads(response.text)
    except (AttributeError, TypeError, ValueError):
        status_code = getattr(response, 'status_code', None)
        status_suffix = ' (HTTP %s)' % status_code if status_code else ''
        return 0, '', 'Remote server returned an invalid response%s.' % status_suffix

    if not isinstance(payload, dict):
        return 0, '', 'Remote server returned an invalid response.'

    if payload.get('transferStatus') == 1:
        transfer_dir = str(payload.get('dir', '')).strip()
        if is_safe_numeric_id(transfer_dir):
            return 1, transfer_dir, 'None'
        return 0, '', 'Remote server returned an invalid transfer identifier.'

    error_message = payload.get('error_message')
    if isinstance(error_message, str) and error_message.strip():
        return 0, '', error_message.strip()

    return 0, '', 'Remote server returned an unexpected transfer response.'
