import re


_SNAPSHOT_SAVED = re.compile(
    r'^snapshot\s+([0-9a-f]{8,64})\s+saved\s*$',
    re.IGNORECASE | re.MULTILINE,
)


def extract_snapshot_id(output):
    matches = _SNAPSHOT_SAVED.findall(output or '')
    if not matches:
        raise ValueError('Restic did not report a saved snapshot.')
    return matches[-1]
