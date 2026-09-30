"""Reserve numeric status paths accepted by the panel's polling endpoint."""
import os
import secrets


def create_status_file(directory='/home/cyberpanel'):
    # Four-digit random names can reuse an old root-owned success file, or
    # collide with another active worker. Reserve each path before launch.
    while True:
        path = os.path.join(directory, str(secrets.randbits(128)))
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            continue
        with os.fdopen(fd, 'w') as status:
            status.write('Starting..,0')
        return path
