"""Explicit outcomes for privileged certificate issuance requests."""
import json

RESULT_PREFIX = 'SSL_RESULT='


def result_payload(result):
    code, message = result[:2]
    metadata = result[2] if len(result) > 2 else {}
    success = code == 1
    return {
        'status': int(success), 'SSL': int(success),
        'error_message': 'None' if success else str(message),
        'message': str(message),
        'outcome': metadata.get('outcome', 'issued' if success else 'failed'),
        'certificate_validity': metadata.get('certificate_validity', 'unknown'),
        'retained_existing': bool(metadata.get('retained_existing', False)),
        'warning': str(message) if code == 2 else '',
    }


def parse_output(output):
    lines = str(output or '').splitlines()
    for line in reversed(lines):
        if line.startswith(RESULT_PREFIX):
            try:
                result = json.loads(line[len(RESULT_PREFIX):])
                if (type(result.get('status')) is not int or result['status'] not in (0, 1)
                        or result.get('SSL') != result['status']
                        or not isinstance(result.get('error_message'), str)):
                    raise ValueError('Invalid SSL result')
                return result
            except (ValueError, TypeError, AttributeError):
                break
    # Retain compatibility with an older installed helper during an upgrade.
    if lines and lines[-1].strip() == '1,None':
        return result_payload([1, 'None'])
    return result_payload([0, str(output or 'SSL helper returned no result.')])
