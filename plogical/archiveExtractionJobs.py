#!/usr/local/CyberCP/bin/python
import argparse
import fcntl
import json
import os
import pwd
import shlex
import stat
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from plogical.securityUtils import (
    PRIVATE_TOKEN_RE,
    create_private_token_file,
    is_private_token_path,
    is_safe_system_user,
    read_private_token_file,
    remove_stale_private_token_files,
)


FILE_EXTRACTION_DIRECTORY = '/home/cyberpanel/.file-extractions'
FILE_EXTRACTION_MAX_AGE = 24 * 60 * 60


def create_archive_extraction_job(
        panel_user_id,
        domain,
        directory=FILE_EXTRACTION_DIRECTORY,
        owner_user='cyberpanel'):
    remove_stale_private_token_files(directory, FILE_EXTRACTION_MAX_AGE)
    now = int(time.time())
    payload = {
        'panel_user_id': str(panel_user_id),
        'domain': str(domain),
        'state': 'queued',
        'message': 'Archive extraction is queued.',
        'created': now,
        'updated': now,
    }
    return create_private_token_file(
        directory,
        json.dumps(payload),
        owner_user=owner_user,
    )


def get_archive_extraction_status(
        token,
        panel_user_id,
        domain,
        directory=FILE_EXTRACTION_DIRECTORY):
    payload = json.loads(read_private_token_file(
        token,
        directory,
        max_age=FILE_EXTRACTION_MAX_AGE,
        max_bytes=16384,
    ))
    if payload.get('panel_user_id') != str(panel_user_id):
        raise PermissionError('Archive extraction job does not belong to this user.')
    if payload.get('domain') != str(domain):
        raise PermissionError('Archive extraction job does not belong to this website.')
    return {
        'state': payload.get('state', 'failed'),
        'message': payload.get('message', 'Archive extraction status is unavailable.'),
        'created': payload.get('created'),
        'updated': payload.get('updated'),
    }


def _update_archive_extraction_status(status_path, state, message):
    token = os.path.basename(status_path)
    directory = os.path.dirname(os.path.abspath(status_path))
    if PRIVATE_TOKEN_RE.fullmatch(token) is None:
        raise ValueError('Invalid archive extraction job token.')
    if not is_private_token_path(status_path, directory):
        raise ValueError('Invalid archive extraction status path.')

    descriptor = os.open(
        status_path,
        os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW,
    )
    try:
        file_status = os.fstat(descriptor)
        if not stat.S_ISREG(file_status.st_mode) or file_status.st_nlink != 1:
            raise OSError('Archive extraction status is not a private regular file.')
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        content = os.read(descriptor, 16385)
        if len(content) > 16384:
            raise ValueError('Archive extraction status is too large.')
        payload = json.loads(content.decode('utf-8'))
        payload['state'] = state
        payload['message'] = message
        payload['updated'] = int(time.time())
        encoded = json.dumps(payload).encode('utf-8')
        os.lseek(descriptor, 0, os.SEEK_SET)
        os.ftruncate(descriptor, 0)
        os.write(descriptor, encoded)
        os.fsync(descriptor)
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def _demote_to_user(username):
    account = pwd.getpwnam(username)

    def demote():
        os.initgroups(account.pw_name, account.pw_gid)
        os.setgid(account.pw_gid)
        os.setuid(account.pw_uid)

    return demote


def run_archive_extraction_job(
        token,
        status_path,
        allowed_root,
        archive_path,
        destination,
        archive_type,
        run_as=None,
        python_path='/usr/local/CyberCP/bin/python'):
    if os.path.basename(status_path) != token:
        raise ValueError('Archive extraction job token does not match its status path.')
    if archive_type not in ('zip', 'tar', 'tar.gz', 'tgz'):
        raise ValueError('Unsupported archive type.')
    if run_as is not None and not is_safe_system_user(run_as):
        raise ValueError('Invalid website account.')

    _update_archive_extraction_status(
        status_path,
        'running',
        'Archive extraction is running.',
    )
    extraction_script = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'safeArchiveExtraction.py',
    )
    command = [
        python_path,
        extraction_script,
        '--allowed-root', allowed_root,
        '--archive', archive_path,
        '--destination', destination,
        '--type', archive_type,
    ]
    try:
        completed = subprocess.run(
            command,
            cwd='/',
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors='replace',
            preexec_fn=_demote_to_user(run_as) if run_as else None,
        )
        if completed.returncode != 0:
            output = (completed.stdout or '').strip()
            if output:
                logging.writeToFile(
                    'Archive extraction job %s failed: %s' % (token, output[-4000:])
                )
            _update_archive_extraction_status(
                status_path,
                'failed',
                'Archive extraction was rejected or failed.',
            )
            return False
    except BaseException as error:
        logging.writeToFile(
            'Archive extraction job %s could not run: %s' % (token, str(error))
        )
        _update_archive_extraction_status(
            status_path,
            'failed',
            'Archive extraction was rejected or failed.',
        )
        return False

    _update_archive_extraction_status(
        status_path,
        'completed',
        'Archive extracted successfully.',
    )
    return True


def build_archive_extraction_command(
        token,
        status_path,
        allowed_root,
        archive_path,
        destination,
        archive_type,
        run_as=None,
        python_path='/usr/local/CyberCP/bin/python',
        systemd_run='/usr/bin/systemd-run'):
    job_script = os.path.abspath(__file__)
    arguments = [
        systemd_run,
        '--quiet',
        '--collect',
        '--unit=cyberpanel-extract-%s' % token,
        python_path,
        job_script,
        '--token', token,
        '--status-path', status_path,
        '--allowed-root', allowed_root,
        '--archive', archive_path,
        '--destination', destination,
        '--type', archive_type,
    ]
    if run_as:
        arguments.extend(['--run-as', run_as])
    return ' '.join(shlex.quote(argument) for argument in arguments)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--token', required=True)
    parser.add_argument('--status-path', required=True)
    parser.add_argument('--allowed-root', required=True)
    parser.add_argument('--archive', required=True)
    parser.add_argument('--destination', required=True)
    parser.add_argument('--type', required=True, choices=('zip', 'tar', 'tar.gz', 'tgz'))
    parser.add_argument('--run-as')
    arguments = parser.parse_args()

    if not is_private_token_path(arguments.status_path, FILE_EXTRACTION_DIRECTORY):
        raise SystemExit('Invalid archive extraction status path.')
    result = run_archive_extraction_job(
        token=arguments.token,
        status_path=arguments.status_path,
        allowed_root=arguments.allowed_root,
        archive_path=arguments.archive,
        destination=arguments.destination,
        archive_type=arguments.type,
        run_as=arguments.run_as,
        python_path=sys.executable,
    )
    raise SystemExit(0 if result else 1)


if __name__ == '__main__':
    main()
