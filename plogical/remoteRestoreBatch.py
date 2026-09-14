"""Track an ordinary remote restore batch without deleting its evidence."""
import os
import fcntl
import secrets
import subprocess
import time


RESTORE_TIMEOUT_SECONDS = 6 * 60 * 60
ATTEMPT_PREFIX = 'REMOTE_RESTORE_ATTEMPT='


def archive_stem(name):
    return name[:-7] if name.endswith('.tar.gz') else name


def batch_status(status):
    current = status.rsplit('\n' + ATTEMPT_PREFIX, 1)[-1]
    # Older workers could append success after an individual restore failed.
    if any(marker in current for marker in ('[5010]', '[5009]', 'Error[Failed]', 'completed[failed]')):
        return {'remoteTransferStatus': 0, 'error_message': status,
                'status': status, 'complete': 0}
    return {'remoteTransferStatus': 1, 'error_message': 'None', 'status': status,
            'complete': int('completed[success]' in current)}


def _read_status(path):
    try:
        with open(path) as source:
            info = os.fstat(source.fileno())
            return (info.st_ino, info.st_mtime_ns, info.st_size), source.read()
    except FileNotFoundError:
        return None, ''


def _status_path(backup_dir, archive):
    path = os.path.join(backup_dir, archive_stem(archive), 'status')
    root = os.path.realpath(backup_dir)
    if os.path.commonpath((root, os.path.realpath(path))) != root:
        raise ValueError('Invalid backup archive path')
    return path


def run_restore_batch(backup_dir, log_path, transfer_id, panel_path,
                      timeout=RESTORE_TIMEOUT_SECONDS, poll_interval=2):
    lock_path = os.path.join(backup_dir, '.restore.lock')
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            # A repeated asynchronous start refers to the existing batch. Do not
            # overwrite its log, PID or archive status, or launch another worker.
            return False
        return _run_locked_batch(backup_dir, log_path, transfer_id, panel_path,
                                 timeout, poll_interval)


def _run_locked_batch(backup_dir, log_path, transfer_id, panel_path, timeout, poll_interval):
    """Success requires every archive's fresh Done status and a finished worker.

    submitRestore's Python process joins its non-daemon restore child at exit.
    A timeout reports failure immediately, then waits while retaining the lock
    until the existing worker exits. It never permits an overlapping retry. Keep
    archives, extracted files and logs available for inspection in every case.
    """
    completed = 0
    with open(log_path, 'a', buffering=1) as log:
        log.write('\n' + ATTEMPT_PREFIX + secrets.token_hex(16) + '\n')
        with open(os.path.join(backup_dir, 'pid'), 'w') as pid:
            pid.write(str(os.getpid()))
        worker = None
        def fail(message):
            log.write('Backup restore incomplete after %s archive(s): %s [5010]\n'
                      % (completed, message))
            return False

        try:
            archives = sorted(name for name in os.listdir(backup_dir)
                              if name.endswith('.tar.gz') and
                              not os.path.islink(os.path.join(backup_dir, name)) and
                              os.path.isfile(os.path.join(backup_dir, name)))
            if not archives:
                return fail('No backup archives were found.')
            for archive in archives:
                log.write('Starting restore for: %s\n' % archive)
                status_path = _status_path(backup_dir, archive)
                old_signature, _ = _read_status(status_path)
                command = ['sudo', 'nice', '-n', '10',
                           '/usr/local/CyberCP/bin/python',
                           os.path.join(panel_path, 'plogical', 'backupUtilities.py'),
                           'submitRestore', '--backupFile', archive, '--dir', str(transfer_id)]
                worker = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
                started = time.monotonic()
                while True:
                    return_code = worker.poll()
                    signature, status = _read_status(_status_path(backup_dir, archive))
                    fresh_status = status if signature != old_signature else ''
                    if return_code is not None:
                        if '[5009]' in fresh_status or 'Error[Failed]' in fresh_status:
                            return fail('%s: %s' % (archive, fresh_status))
                        if return_code != 0:
                            return fail('%s: worker exited with status %s. %s' %
                                        (archive, return_code, fresh_status))
                        if fresh_status.strip() != 'Done':
                            return fail('%s: worker exited without a fresh completion status. %s' %
                                        (archive, fresh_status))
                        completed += 1
                        log.write('Restore completed for: %s\n' % archive)
                        break
                    if time.monotonic() - started >= timeout:
                        fail('%s: monitoring timed out; worker PID %s may still be running. '
                             'Inspect it and the retained logs before retrying.' %
                             (archive, worker.pid))
                        worker.wait()
                        return False
                    time.sleep(poll_interval)
            log.write('Backup restore complete: %s archive(s).\ncompleted[success]\n' % completed)
            return True
        except Exception as error:
            fail(str(error))
            if worker is not None:
                worker.wait()
            return False
