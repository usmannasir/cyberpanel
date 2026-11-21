"""Rebuild the panel's web worker (lswsgi) during an upgrade started from the panel.

A command-line upgrade builds the worker in cyberpanel_upgrade.sh. An upgrade
started from the panel's own page runs only the Python upgrader, so without
this step such a server keeps the worker it was installed with.

Nobody is at a shell during that upgrade. The installed worker is therefore
replaced only by a complete build of the expected source that starts; in every
other case it is left exactly as it is.
"""
import hashlib
import io
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import PurePosixPath
from urllib.request import Request, urlopen

SOURCE = 'https://www.litespeedtech.com/packages/lsapi/wsgi-lsapi-2.1.tgz'
DIRECTORY = 'wsgi-lsapi-2.1'
PYTHON = '/usr/local/CyberCP/bin/python'
WORKER = '/usr/local/CyberCP/bin/lswsgi'
EDIT = '/usr/local/CyberCP/install/lswsgi_idle_lock.py'
ARCHIVE_LIMIT = 4 * 1024 * 1024
SOURCE_LIMIT = 16 * 1024 * 1024
SEARCH_PATH = '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'


def download(url=SOURCE, limit=ARCHIVE_LIMIT, timeout=60):
    request = Request(url, headers={'User-Agent': 'CyberPanel-Upgrade', 'Accept-Encoding': 'identity'})
    with urlopen(request, timeout=timeout) as response:
        if not response.geturl().startswith('https://'):
            raise RuntimeError('the worker source was not served over HTTPS')
        archive = response.read(limit + 1)
    if len(archive) > limit:
        raise RuntimeError('the worker source archive is larger than expected')
    return archive


def unpack(archive, directory, limit=SOURCE_LIMIT):
    """Write the archive's plain files below `directory`; anything else is refused."""
    written = 0
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as source:
        for member in source:
            path = PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts or path.parts[:1] != (DIRECTORY,):
                raise RuntimeError('unexpected path in the worker source: ' + member.name)
            target = os.path.join(directory, *path.parts)
            if member.isdir():
                os.makedirs(target, exist_ok=True)
            elif member.isreg():
                written += member.size
                if written > limit:
                    raise RuntimeError('the worker source is larger than expected')
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, 'wb') as output:
                    shutil.copyfileobj(source.extractfile(member), output)
            else:
                raise RuntimeError('unexpected entry in the worker source: ' + member.name)


def run(arguments, directory, timeout):
    # The panel service sets PYTHONHOME for its worker; a build must not inherit it.
    environment = {name: value for name, value in os.environ.items()
                   if name not in ('PYTHONHOME', 'PYTHONPATH')}
    environment.setdefault('PATH', SEARCH_PATH)
    result = subprocess.run(arguments, cwd=directory, env=environment, timeout=timeout,
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, universal_newlines=True, errors='replace')
    if result.returncode:
        raise RuntimeError('%s ended with status %d: %s' % (
            os.path.basename(arguments[0]), result.returncode, result.stdout[-400:].strip()))
    return result.stdout


def starts(worker):
    """True when the built worker loads its libraries and reports itself."""
    result = subprocess.run([worker, '-v'], timeout=30, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            universal_newlines=True, errors='replace')
    return result.stdout.startswith('lswsgi version ')


def rebuild(python=PYTHON, worker=WORKER, edit=EDIT, fetch=download):
    """Build the worker and put it in place of the installed one, or raise."""
    archive = fetch()
    with tempfile.TemporaryDirectory(prefix='cyberpanel-lswsgi.') as directory:
        unpack(archive, directory)
        source = os.path.join(directory, DIRECTORY)
        # A source the edit does not recognise would only give the worker that
        # is already installed, so it is not built at all.
        try:
            run([python, '-I', edit, 'main.c'], source, 60)
        except RuntimeError:
            raise RuntimeError('the worker source is not the one this release expects')
        run([python, './configure.py'], source, 120)
        run(['make'], source, 900)
        # Temporary directories may forbid execution; test the copy that will be installed.
        descriptor, staged = tempfile.mkstemp(dir=os.path.dirname(worker), prefix='lswsgi.upgrade.')
        try:
            with os.fdopen(descriptor, 'wb') as output, open(os.path.join(source, 'lswsgi'), 'rb') as built:
                shutil.copyfileobj(built, output)
                os.fchmod(output.fileno(), 0o755)
                try:
                    installed = os.stat(worker)
                    os.fchown(output.fileno(), installed.st_uid, installed.st_gid)
                except FileNotFoundError:
                    pass
            if not starts(staged):
                raise RuntimeError('the rebuilt worker did not start')
            with open(staged, 'rb') as content:
                digest = hashlib.sha256(content.read()).hexdigest()
            os.replace(staged, worker)
        finally:
            try:
                os.unlink(staged)
            except FileNotFoundError:
                pass
    return {'state': 'rebuilt', 'sha256': digest}
