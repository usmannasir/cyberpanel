import os
import subprocess
import time

from serverStatus.serverStatusUtil import ServerStatusUtil
from plogical import CyberCPLogFileWriter as logging
from manageServices.application_backup import (
    CHOWN_CMDS,
    cleanup_managed_backup,
    create_managed_app_backup,
    merge_data_from_backup,
    restore_full_backup,
    service_is_active,
)
from manageServices.application_detection import detect_app_state, is_debian_family


def _es_major_normalized(es_major):
    m = str(es_major).strip()
    if m in ('7', '8', '9'):
        return m
    return '8'


def _write_repo(es_major):
    major = _es_major_normalized(es_major)
    if is_debian_family():
        repo_file = '/etc/apt/sources.list.d/elastic-{0}.x.list'.format(major)
        cmd = 'echo "deb https://artifacts.elastic.co/packages/{0}.x/apt stable main" | sudo tee {1}'.format(major, repo_file)
        subprocess.call(cmd, shell=True)
        return repo_file

    repo_file = '/etc/yum.repos.d/elasticsearch.repo'
    content = '''
[elasticsearch]
name=Elasticsearch repository for {0}.x packages
baseurl=https://artifacts.elastic.co/packages/{0}.x/yum
gpgcheck=1
gpgkey=https://artifacts.elastic.co/GPG-KEY-elasticsearch
enabled=0
autorefresh=1
type=rpm-md
'''.format(major)
    with open(repo_file, 'w') as handle:
        handle.write(content)
    return repo_file


def _ensure_tmpdir(status_file):
    ServerStatusUtil.executioner('mkdir -p /home/elasticsearch/tmp', status_file)
    ServerStatusUtil.executioner('chown elasticsearch:elasticsearch /home/elasticsearch/tmp', status_file)
    jvm_options = '/etc/elasticsearch/jvm.options'
    line = '-Djava.io.tmpdir=/home/elasticsearch/tmp\n'
    try:
        if os.path.exists(jvm_options):
            with open(jvm_options, 'r') as handle:
                body = handle.read()
            if line.strip() not in body:
                with open(jvm_options, 'a') as handle:
                    handle.write(line)
    except Exception:
        pass


def adopt_or_reconcile(status_file):
    state = detect_app_state('Elasticsearch')
    if state['installed'] and not state['markerExists']:
        ServerStatusUtil.executioner('touch /home/cyberpanel/elasticsearch', status_file)
        logging.CyberCPLogFileWriter.statusWriter(
            ServerStatusUtil.lswsInstallStatusPath,
            'Elasticsearch detected and adopted by marker reconciliation.\n'
        )
    return state


def _resolve_target_version(version, es_major):
    if version and str(version).strip() != 'latest':
        return str(version).strip()
    from manageServices.application_versions import get_latest_version
    return get_latest_version('Elasticsearch', es_major, '3') or ''


def _run_elasticsearch_packages(version, es_major, status_file, allow_downgrade):
    if is_debian_family():
        subprocess.call(
            'wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -',
            shell=True,
        )
        ServerStatusUtil.executioner('apt-get install apt-transport-https -y', status_file)
        _write_repo(es_major)
        ServerStatusUtil.executioner('apt-get update -y', status_file)
        if version and version != 'latest':
            cmd = (
                'DEBIAN_FRONTEND=noninteractive apt-get install -y '
                '--allow-downgrades elasticsearch={0}'
            ).format(version)
        else:
            cmd = 'DEBIAN_FRONTEND=noninteractive apt-get install elasticsearch -y'
        ServerStatusUtil.executioner(cmd, status_file)
        return

    ServerStatusUtil.executioner(
        'rpm --import https://artifacts.elastic.co/GPG-KEY-elasticsearch', status_file
    )
    _write_repo(es_major)
    ad = ' --allow-downgrade' if allow_downgrade else ''
    if version and version != 'latest':
        cmd = 'dnf install{0} -y --enablerepo=elasticsearch elasticsearch-{1}'.format(
            ad, version
        )
        ServerStatusUtil.executioner(cmd, status_file)
    else:
        cmd = 'dnf install{0} -y --enablerepo=elasticsearch elasticsearch'.format(ad)
        ServerStatusUtil.executioner(cmd, status_file)


def install(version='latest', es_major='8'):
    status_file = open(ServerStatusUtil.lswsInstallStatusPath, 'w')
    adopt_or_reconcile(status_file)

    from manageServices.application_versions import version_compare

    state = detect_app_state('Elasticsearch')
    backup_dir = ''
    allow_downgrade = False
    target = _resolve_target_version(version, es_major)

    if state['installed'] and state.get('installedVersion'):
        status_file.write(
            'Pre-version-change backup and service stop (Elasticsearch)...\n'
        )
        status_file.flush()
        iv = state['installedVersion']
        if target and version_compare(iv, target) > 0:
            allow_downgrade = True
            status_file.write(
                'Downgrade path: allowing package manager downgrade where supported.\n'
            )
            status_file.flush()
        backup_dir = create_managed_app_backup('Elasticsearch', status_file)
        ServerStatusUtil.executioner('systemctl stop elasticsearch', status_file)

    _run_elasticsearch_packages(version, es_major, status_file, allow_downgrade)
    if backup_dir:
        merge_data_from_backup('Elasticsearch', backup_dir, status_file)
        ServerStatusUtil.executioner(CHOWN_CMDS['Elasticsearch'], status_file)

    _ensure_tmpdir(status_file)
    ServerStatusUtil.executioner('systemctl enable elasticsearch', status_file)
    ServerStatusUtil.executioner('systemctl start elasticsearch', status_file)
    time.sleep(3)

    if backup_dir:
        if service_is_active('Elasticsearch'):
            cleanup_managed_backup(backup_dir, status_file)
            status_file.write(
                'Elasticsearch version change completed; backup removed after success.\n'
            )
        else:
            status_file.write(
                'Elasticsearch failed to start; restoring from backup...\n'
            )
            restore_full_backup(backup_dir, status_file)
            ServerStatusUtil.executioner(CHOWN_CMDS['Elasticsearch'], status_file)
            ServerStatusUtil.executioner('systemctl start elasticsearch', status_file)
            time.sleep(2)
            if not service_is_active('Elasticsearch'):
                status_file.write(
                    'Recovery unclear — backup kept at {0}\n'.format(backup_dir)
                )
            else:
                status_file.write(
                    'Prior state restored from backup. Backup retained for safety.\n'
                )
        status_file.flush()

    ServerStatusUtil.executioner('touch /home/cyberpanel/elasticsearch', status_file)
    logging.CyberCPLogFileWriter.statusWriter(
        ServerStatusUtil.lswsInstallStatusPath, 'Elasticsearch installed.[200]\n', 1
    )
    return 0


def upgrade(version='latest', es_major='8'):
    return install(version=version, es_major=es_major)


def remove():
    status_file = open(ServerStatusUtil.lswsInstallStatusPath, 'w')
    if is_debian_family():
        for major in ('7', '8', '9'):
            path = '/etc/apt/sources.list.d/elastic-{0}.x.list'.format(major)
            try:
                os.remove(path)
            except Exception:
                pass
        ServerStatusUtil.executioner(
            'DEBIAN_FRONTEND=noninteractive apt-get remove elasticsearch -y', status_file
        )
    else:
        try:
            os.remove('/etc/yum.repos.d/elasticsearch.repo')
        except Exception:
            pass
        ServerStatusUtil.executioner('yum erase elasticsearch -y', status_file)

    ServerStatusUtil.executioner('rm -rf /home/elasticsearch/tmp', status_file)
    ServerStatusUtil.executioner('rm -f /home/cyberpanel/elasticsearch', status_file)
    logging.CyberCPLogFileWriter.statusWriter(
        ServerStatusUtil.lswsInstallStatusPath, 'Elasticsearch removed.[200]\n', 1
    )
    return 0
