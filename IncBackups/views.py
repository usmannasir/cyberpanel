import json
import os
import stat
import time
from pathlib import Path
from random import randint

from django.shortcuts import HttpResponse, redirect

from backup.backupManager import BackupManager
from loginSystem.models import Administrator
from loginSystem.views import loadLoginPage
from plogical.Backupsv2 import CPBackupsV2
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from plogical.acl import ACLManager
from plogical.httpProc import httpProc
from plogical.processUtilities import ProcessUtilities as pu
from plogical.virtualHostUtilities import virtualHostUtilities as vhu
from websiteFunctions.models import Websites
from .IncBackupProvider import IncBackupProvider
from .IncBackupPath import IncBackupPath
from .IncBackupsControl import IncJobs
from .models import IncJob, BackupJob, JobSites


def def_renderer(request, templateName, args, context=None):
    proc = httpProc(request, templateName,
                    args, context)
    return proc.render()


def _get_destinations(local: bool = False):
    destinations = []
    if local:
        destinations.append('local')
    path = Path(IncBackupPath.SFTP.value)
    if path.exists():
        for item in path.iterdir():
            destinations.append('sftp:%s' % item.name)

    path = Path(IncBackupPath.AWS.value)
    if path.exists():
        for item in path.iterdir():
            destinations.append('s3:s3.amazonaws.com/%s' % item.name)
    return destinations


def _get_user_acl(request):
    user_id = request.session['userID']
    current_acl = ACLManager.loadedACL(user_id)
    return user_id, current_acl




def create_backup(request):

    try:
        user_id, current_acl = _get_user_acl(request)
        if ACLManager.currentContextPermission(current_acl, 'createBackup') == 0:
            return ACLManager.loadError()

        websites = ACLManager.findAllSites(current_acl, user_id)

        destinations = _get_destinations(local=True)

        return def_renderer(request, 'IncBackups/createBackup.html',
                            {'websiteList': websites, 'destinations': destinations}, 'createBackup')
    except BaseException as msg:
        logging.writeToFile(str(msg))
        return redirect(loadLoginPage)


def backup_destinations(request):
    try:
        user_id, current_acl = _get_user_acl(request)
        if ACLManager.currentContextPermission(current_acl, 'addDeleteDestinations') == 0:
            return ACLManager.loadError()

        return def_renderer(request, 'IncBackups/incrementalDestinations.html', {}, 'addDeleteDestinations')
    except BaseException as msg:
        logging.writeToFile(str(msg))
        return redirect(loadLoginPage)


def add_destination(request):
    try:
        user_id, current_acl = _get_user_acl(request)
        if ACLManager.currentContextPermission(current_acl, 'addDeleteDestinations') == 0:
            return ACLManager.loadErrorJson('destStatus', 0)

        data = json.loads(request.body)

        if data['type'].lower() == IncBackupProvider.SFTP.name.lower():
            path = Path(IncBackupPath.SFTP.value)
            path.mkdir(exist_ok=True)

            ip_address = data['IPAddress']
            password = data['password']

            address_file = path / ip_address
            port = data.get('backupSSHPort', '22')

            if address_file.exists():
                final_dic = {'status': 0, 'error_message': 'This destination already exists.'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

            python_path = Path('/usr/local/CyberCP/bin/python')
            backup_utils = Path(vhu.cyberPanel) / "plogical/backupUtilities.py"

            exec_args = "submitDestinationCreation --ipAddress %s --password %s --port %s --user %s" % \
                        (ip_address, password, port, 'root')

            exec_cmd = "%s %s %s" % (python_path, backup_utils, exec_args)

            if Path(pu.debugPath).exists():
                logging.writeToFile(exec_cmd)

            output = pu.outputExecutioner(exec_cmd)

            if Path(pu.debugPath).exists():
                logging.writeToFile(output)

            if output.find('1,') > -1:
                content = '%s\n%s' % (ip_address, port)
                with open(address_file, 'w') as outfile:
                    outfile.write(content)

                command = 'cat /root/.ssh/config'
                current_config = pu.outputExecutioner(command)

                tmp_file = '/home/cyberpanel/sshconfig'
                with open(tmp_file, 'w') as outfile:
                    if current_config.find('cat') == -1:
                        outfile.write(current_config)

                    content = "Host %s\n" \
                              "    IdentityFile ~/.ssh/cyberpanel\n" \
                              "    Port %s\n" % (ip_address, port)
                    if current_config.find(ip_address) == -1:
                        outfile.write(content)

                command = 'mv %s /root/.ssh/config' % tmp_file
                pu.executioner(command)

                command = 'chown root:root /root/.ssh/config'
                pu.executioner(command)

                final_dic = {'status': 1, 'error_message': 'None'}
            else:
                final_dic = {'status': 0, 'error_message': output}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        if data['type'].lower() == IncBackupProvider.AWS.name.lower():
            path = Path(IncBackupPath.AWS.value)
            path.mkdir(exist_ok=True)

            access_key = data['AWS_ACCESS_KEY_ID']
            secret_key = data['AWS_SECRET_ACCESS_KEY']

            aws_file = path / access_key

            with open(aws_file, 'w') as outfile:
                outfile.write(secret_key)

            aws_file.chmod(stat.S_IRUSR | stat.S_IWUSR)

            final_dic = {'status': 1}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except BaseException as msg:
        final_dic = {'status': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def populate_current_records(request):
    try:
        user_id, current_acl = _get_user_acl(request)
        if ACLManager.currentContextPermission(current_acl, 'addDeleteDestinations') == 0:
            return ACLManager.loadErrorJson('fetchStatus', 0)

        data = json.loads(request.body)

        json_data = []
        if data['type'].lower() == IncBackupProvider.SFTP.name.lower():
            path = Path(IncBackupPath.SFTP.value)

            if path.exists():
                for item in path.iterdir():
                    with open(item, 'r') as infile:
                        _file = infile.readlines()
                        json_data.append({
                            'ip': _file[0].strip('\n'),
                            'port': _file[1],
                        })
            else:
                final_json = json.dumps({'status': 1, 'error_message': "None", "data": ''})
                return HttpResponse(final_json)

        if data['type'].lower() == IncBackupProvider.AWS.name.lower():
            path = Path(IncBackupPath.AWS.value)

            if path.exists():
                for item in path.iterdir():
                    json_data.append({'AWS_ACCESS_KEY_ID': item.name})
            else:
                final_json = json.dumps({'status': 1, 'error_message': "None", "data": ''})
                return HttpResponse(final_json)

        final_json = json.dumps({'status': 1, 'error_message': "None", "data": json_data})
        return HttpResponse(final_json)
    except BaseException as msg:
        final_dic = {'status': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def remove_destination(request):
    try:
        user_id, current_acl = _get_user_acl(request)
        if ACLManager.currentContextPermission(current_acl, 'addDeleteDestinations') == 0:
            return ACLManager.loadErrorJson('destStatus', 0)

        data = json.loads(request.body)

        if 'IPAddress' in data:
            file_name = data['IPAddress']

            if data['type'].lower() == IncBackupProvider.SFTP.name.lower():
                dest_file = Path(IncBackupPath.SFTP.value) / file_name
                dest_file.unlink()

            if data['type'].lower() == IncBackupProvider.AWS.name.lower():
                dest_file = Path(IncBackupPath.AWS.value) / file_name
                dest_file.unlink()

        final_dic = {'status': 1, 'error_message': 'None'}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)
    except BaseException as msg:
        final_dic = {'destStatus': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def fetch_current_backups(request):
    try:
        user_id, current_acl = _get_user_acl(request)
        admin = Administrator.objects.get(pk=user_id)

        data = json.loads(request.body)
        backup_domain = data['websiteToBeBacked']

        if ACLManager.checkOwnership(backup_domain, admin, current_acl) == 1:
            pass
        else:
            return ACLManager.loadErrorJson('fetchStatus', 0)

        if 'backupDestinations' in data:
            backup_destinations = data['backupDestinations']
            extra_args = {'website': backup_domain, 'backupDestinations': backup_destinations}

            if 'password' in data:
                extra_args['password'] = data['password']
            else:
                final_json = json.dumps({'status': 0, 'error_message': "Please supply the password."})
                return HttpResponse(final_json)

            start_job = IncJobs('Dummy', extra_args)
            return start_job.fetchCurrentBackups()
        else:
            website = Websites.objects.get(domain=backup_domain)
            backups = website.incjob_set.all()
            json_data = []
            for backup in reversed(backups):
                snapshots = []
                jobs = backup.jobsnapshots_set.all()
                for job in jobs:
                    snapshots.append({'type': job.type, 'snapshotid': job.snapshotid, 'destination': job.destination})
                json_data.append({'id': backup.id,
                                  'date': str(backup.date),
                                  'snapshots': snapshots
                                  })
            final_json = json.dumps({'status': 1, 'error_message': "None", "data": json_data})
            return HttpResponse(final_json)
    except BaseException as msg:
        final_dic = {'status': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def submit_backup_creation(request):
    try:
        user_id, current_acl = _get_user_acl(request)
        admin = Administrator.objects.get(pk=user_id)

        data = json.loads(request.body)
        backup_domain = data['websiteToBeBacked']
        backup_destinations = data['backupDestinations']

        if ACLManager.checkOwnership(backup_domain, admin, current_acl) == 1:
            pass
        else:
            return ACLManager.loadErrorJson('metaStatus', 0)

        temp_path = Path("/home/cyberpanel/") / str(randint(1000, 9999))

        extra_args = {}
        extra_args['website'] = backup_domain
        extra_args['tempPath'] = str(temp_path)
        extra_args['backupDestinations'] = backup_destinations
        extra_args['websiteData'] = data['websiteData'] if 'websiteData' in data else False
        extra_args['websiteEmails'] = data['websiteEmails'] if 'websiteEmails' in data else False
        extra_args['websiteSSLs'] = data['websiteSSLs'] if 'websiteSSLs' in data else False
        extra_args['websiteDatabases'] = data['websiteDatabases'] if 'websiteDatabases' in data else False

        start_job = IncJobs('createBackup', extra_args)
        start_job.start()

        time.sleep(2)

        final_json = json.dumps({'status': 1, 'error_message': "None", 'tempPath': str(temp_path)})
        return HttpResponse(final_json)
    except BaseException as msg:
        logging.writeToFile(str(msg))
        final_dic = {'status': 0, 'metaStatus': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def get_backup_status(request):
    try:
        data = json.loads(request.body)

        status = data['tempPath']
        backup_domain = data['websiteToBeBacked']

        user_id, current_acl = _get_user_acl(request)
        admin = Administrator.objects.get(pk=user_id)
        if ACLManager.checkOwnership(backup_domain, admin, current_acl) == 1:
            pass
        else:
            return ACLManager.loadErrorJson('fetchStatus', 0)

        if ACLManager.CheckStatusFilleLoc(status):
            pass
        else:
            data_ret = {'abort': 1, 'installStatus': 0, 'installationProgress': "100",
                        'currentStatus': 'Invalid status file.'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        ## file name read ends

        if os.path.exists(status):
            command = "cat " + status
            result = pu.outputExecutioner(command, 'cyberpanel')

            if result.find("Completed") > -1:

                ### Removing Files

                os.remove(status)

                final_json = json.dumps(
                    {'backupStatus': 1, 'error_message': "None", "status": result, "abort": 1})
                return HttpResponse(final_json)

            elif result.find("[5009]") > -1:
                ## removing status file, so that backup can re-run
                try:
                    os.remove(status)
                except:
                    pass

                final_json = json.dumps(
                    {'backupStatus': 1, 'error_message': "None", "status": result,
                     "abort": 1})
                return HttpResponse(final_json)
            else:
                final_json = json.dumps(
                    {'backupStatus': 1, 'error_message': "None", "status": result,
                     "abort": 0})
                return HttpResponse(final_json)
        else:
            final_json = json.dumps({'backupStatus': 1, 'error_message': "None", "status": 1, "abort": 0})
            return HttpResponse(final_json)
    except BaseException as msg:
        final_dic = {'backupStatus': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        logging.writeToFile(str(msg) + " [backupStatus]")
        return HttpResponse(final_json)

def delete_backup(request):
    try:

        user_id, current_acl = _get_user_acl(request)
        admin = Administrator.objects.get(pk=user_id)
        data = json.loads(request.body)
        backup_domain = data['websiteToBeBacked']

        if ACLManager.checkOwnership(backup_domain, admin, current_acl) == 1:
            pass
        else:
            return ACLManager.loadErrorJson('fetchStatus', 0)

        backup_id = data['backupID']

        inc_job = IncJob.objects.get(id=backup_id)

        job = IncJobs(None, None)
        job.DeleteSnapShot(inc_job)

        inc_job.delete()

        final_dic = {'status': 1, 'error_message': 'None'}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)
    except BaseException as msg:
        final_dic = {'destStatus': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def fetch_restore_points(request):
    try:
        user_id, current_acl = _get_user_acl(request)
        admin = Administrator.objects.get(pk=user_id)
        data = json.loads(request.body)
        backup_domain = data['websiteToBeBacked']

        if ACLManager.checkOwnership(backup_domain, admin, current_acl) == 1:
            pass
        else:
            return ACLManager.loadErrorJson('fetchStatus', 0)

        data = json.loads(request.body)
        job_id = data['id']

        inc_job = IncJob.objects.get(id=job_id)

        backups = inc_job.jobsnapshots_set.all()

        json_data = []
        for items in backups:
            json_data.append({'id': items.id,
                              'snapshotid': items.snapshotid,
                              'type': items.type,
                              'destination': items.destination,
                              })

        final_json = json.dumps({'status': 1, 'error_message': "None", "data": json_data})
        return HttpResponse(final_json)
    except BaseException as msg:
        final_dic = {'status': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def restore_point(request):
    try:
        user_id, current_acl = _get_user_acl(request)
        admin = Administrator.objects.get(pk=user_id)

        data = json.loads(request.body)
        backup_domain = data['websiteToBeBacked']
        job_id = data['jobid']

        if ACLManager.checkOwnership(backup_domain, admin, current_acl) == 1:
            pass
        else:
            return ACLManager.loadErrorJson('metaStatus', 0)

        temp_path = Path("/home/cyberpanel/") / str(randint(1000, 9999))

        if data['reconstruct'] == 'remote':
            extraArgs = {}
            extraArgs['website'] = backup_domain
            extraArgs['jobid'] = job_id
            extraArgs['tempPath'] = str(temp_path)
            extraArgs['reconstruct'] = data['reconstruct']
            extraArgs['backupDestinations'] = data['backupDestinations']
            extraArgs['password'] = data['password']
            extraArgs['path'] = data['path']
        else:
            extraArgs = {}
            extraArgs['website'] = backup_domain
            extraArgs['jobid'] = job_id
            extraArgs['tempPath'] = str(temp_path)
            extraArgs['reconstruct'] = data['reconstruct']

        start_job = IncJobs('restorePoint', extraArgs)
        start_job.start()

        time.sleep(2)

        final_json = json.dumps({'status': 1, 'error_message': "None", 'tempPath': str(temp_path)})
        return HttpResponse(final_json)
    except BaseException as msg:
        logging.writeToFile(str(msg))
        final_dic = {'status': 0, 'metaStatus': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def schedule_backups(request):
    try:
        user_id, current_acl = _get_user_acl(request)
        if ACLManager.currentContextPermission(current_acl, 'scheduleBackups') == 0:
            return ACLManager.loadError()

        websites = ACLManager.findAllSites(current_acl, user_id)

        destinations = _get_destinations(local=True)

        return def_renderer(request, 'IncBackups/backupSchedule.html',
                            {'websiteList': websites, 'destinations': destinations}, 'scheduleBackups')
    except BaseException as msg:
        logging.writeToFile(str(msg))
        return redirect(loadLoginPage)


def submit_backup_schedule(request):
    try:
        user_id, current_acl = _get_user_acl(request)
        if ACLManager.currentContextPermission(current_acl, 'scheduleBackups') == 0:
            return ACLManager.loadErrorJson('scheduleStatus', 0)

        data = json.loads(request.body)

        backup_dest = data['backupDestinations']
        backup_freq = data['backupFreq']
        backup_retention = data['backupRetention']
        backup_sites = data['websitesToBeBacked']

        backup_data = 1 if 'websiteData' in data else 0
        backup_emails = 1 if 'websiteEmails' in data else 0
        backup_databases = 1 if 'websiteDatabases' in data else 0

        backup_job = BackupJob(websiteData=backup_data, websiteDataEmails=backup_emails,
                               websiteDatabases=backup_databases, destination=backup_dest, frequency=backup_freq,
                               retention=backup_retention)
        backup_job.save()

        for site in backup_sites:
            backup_site_job = JobSites(job=backup_job, website=site)
            backup_site_job.save()

        final_json = json.dumps({'status': 1, 'error_message': "None"})
        return HttpResponse(final_json)
    except BaseException as msg:
        final_json = json.dumps({'status': 0, 'error_message': str(msg)})
        return HttpResponse(final_json)


def get_current_backup_schedules(request):
    try:
        user_id, current_acl = _get_user_acl(request)
        if ACLManager.currentContextPermission(current_acl, 'scheduleBackups') == 0:
            return ACLManager.loadErrorJson('fetchStatus', 0)

        records = BackupJob.objects.all()

        json_data = []
        for items in records:
            json_data.append({'id': items.id,
                              'destination': items.destination,
                              'frequency': items.frequency,
                              'retention': items.retention,
                              'numberOfSites': items.jobsites_set.all().count()
                              })
        final_json = json.dumps({'status': 1, 'error_message': "None", "data": json_data})
        return HttpResponse(final_json)
    except BaseException as msg:
        final_dic = {'status': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def fetch_sites(request):
    try:
        user_id, current_acl = _get_user_acl(request)
        if ACLManager.currentContextPermission(current_acl, 'scheduleBackups') == 0:
            return ACLManager.loadErrorJson('fetchStatus', 0)

        data = json.loads(request.body)

        job = BackupJob.objects.get(pk=data['id'])

        json_data = []
        for jobsite in job.jobsites_set.all():
            json_data.append({'id': jobsite.id,
                              'website': jobsite.website,
                              })
        final_json = json.dumps({'status': 1, 'error_message': "None", "data": json_data,
                                 'websiteData': job.websiteData, 'websiteDatabases': job.websiteDatabases,
                                 'websiteEmails': job.websiteDataEmails})
        return HttpResponse(final_json)
    except BaseException as msg:
        final_dic = {'status': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def schedule_delete(request):
    try:
        user_id, current_acl = _get_user_acl(request)
        if ACLManager.currentContextPermission(current_acl, 'scheduleBackups') == 0:
            return ACLManager.loadErrorJson('scheduleStatus', 0)

        data = json.loads(request.body)

        job_id = data['id']

        backup_job = BackupJob.objects.get(id=job_id)
        backup_job.delete()

        final_json = json.dumps({'status': 1, 'error_message': "None"})
        return HttpResponse(final_json)
    except BaseException as msg:
        final_json = json.dumps({'status': 0, 'error_message': str(msg)})
        return HttpResponse(final_json)


def restore_remote_backups(request):
    try:
        user_id, current_acl = _get_user_acl(request)
        if ACLManager.currentContextPermission(current_acl, 'createBackup') == 0:
            return ACLManager.loadError()

        websites = ACLManager.findAllSites(current_acl, user_id)

        destinations = _get_destinations()

        return def_renderer(request, 'IncBackups/restoreRemoteBackups.html',
                            {'websiteList': websites, 'destinations': destinations}, 'createBackup')
    except BaseException as msg:
        logging.writeToFile(str(msg))
        return redirect(loadLoginPage)


def save_changes(request):
    try:
        user_id, current_acl = _get_user_acl(request)
        if ACLManager.currentContextPermission(current_acl, 'scheduleBackups') == 0:
            return ACLManager.loadErrorJson('scheduleStatus', 0)

        data = json.loads(request.body)

        job_id = data['id']

        backup_data = data['websiteData'] if 'websiteData' in data else 0
        backup_emails = data['websiteEmails'] if 'websiteEmails' in data else 0
        backup_databases = data['websiteDatabases'] if 'websiteDatabases' in data else 0

        job = BackupJob.objects.get(pk=job_id)

        job.websiteData = int(backup_data)
        job.websiteDatabases = int(backup_databases)
        job.websiteDataEmails = int(backup_emails)
        job.save()

        final_json = json.dumps({'status': 1, 'error_message': "None"})
        return HttpResponse(final_json)
    except BaseException as msg:
        final_json = json.dumps({'status': 0, 'error_message': str(msg)})
        return HttpResponse(final_json)


def remove_site(request):
    try:
        _, current_acl = _get_user_acl(request)
        if ACLManager.currentContextPermission(current_acl, 'scheduleBackups') == 0:
            return ACLManager.loadErrorJson('scheduleStatus', 0)

        data = json.loads(request.body)

        job_id = data['id']
        website = data['website']
        job = BackupJob.objects.get(pk=job_id)
        site = JobSites.objects.get(job=job, website=website)
        site.delete()

        final_json = json.dumps({'status': 1, 'error_message': "None"})
        return HttpResponse(final_json)
    except BaseException as msg:
        final_json = json.dumps({'status': 0, 'error_message': str(msg)})
        return HttpResponse(final_json)


def add_website(request):
    try:
        _, current_acl = _get_user_acl(request)
        if ACLManager.currentContextPermission(current_acl, 'scheduleBackups') == 0:
            return ACLManager.loadErrorJson('scheduleStatus', 0)

        data = json.loads(request.body)

        job_id = data['id']
        website = data['website']

        job = BackupJob.objects.get(pk=job_id)

        try:
            JobSites.objects.get(job=job, website=website)
        except BaseException:
            site = JobSites(job=job, website=website)
            site.save()

        final_json = json.dumps({'status': 1, 'error_message': "None"})
        return HttpResponse(final_json)
    except BaseException as msg:
        final_json = json.dumps({'status': 0, 'error_message': str(msg)})
        return HttpResponse(final_json)



def ConfigureV2Backup(request):
    try:
        user_id, current_acl = _get_user_acl(request)
        if ACLManager.currentContextPermission(current_acl, 'createBackup') == 0:
            return ACLManager.loadError()

        try:
            req_data = {}
            req_data['token'] = request.GET.get('t')
            req_data['refresh_token'] = request.GET.get('r')
            req_data['token_uri'] = request.GET.get('to')
            req_data['scopes'] = request.GET.get('s')
            req_data['name'] = request.GET.get('n')

            cpbuv2 = CPBackupsV2(
                {'domain': 'cyberpanel.net', 'BasePath': '/home/backup', 'BackupDatabase': 1, 'BackupData': 1,
                 'BackupEmails': 1, 'BackendName': 'testremote'})

            # RcloneData = {"name": 'testremote', "host": "staging.cyberpanel.net", "user": "abcds2751", "port": "22",
            #               "password": "hosting", }
            cpbuv2.SetupRcloneBackend(CPBackupsV2.GDrive, req_data)
        except BaseException as msg:
            logging.writeToFile(str(msg))

        # websites = ACLManager.findAllSites(current_acl, user_id)
        #
        # destinations = _get_destinations(local=True)
        proc = httpProc(request, 'IncBackups/ConfigureV2Backup.html')
        return proc.render()


    except BaseException as msg:
        logging.writeToFile(str(msg))
        return redirect(loadLoginPage)
def CreateV2Backup(request):
    try:
        userID = request.session['userID']
        bm = BackupManager()
        return bm.CreateV2backupSite(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def createV2BackupSetup(request):
    try:
        userID = request.session['userID']

        req_data={}
        req_data['token'] = request.GET.get('t')
        req_data['refresh_token'] = request.GET.get('r')
        req_data['token_uri'] = request.GET.get('to')
        req_data['scopes'] = request.GET.get('s')
        req_data['accountname'] = request.GET.get('n')

        cpbuv2 = CPBackupsV2(
            {'domain': 'cyberpanel.net', 'BasePath': '/home/backup', 'BackupDatabase': 1, 'BackupData': 1,
             'BackupEmails': 1, 'BackendName': 'testremote'})

        # RcloneData = {"name": 'testremote', "host": "staging.cyberpanel.net", "user": "abcds2751", "port": "22",
        #               "password": "hosting", }
        cpbuv2.SetupRcloneBackend(CPBackupsV2.GDrive, req_data)
        cpbuv2.InitiateBackup()

        # wm = BackupManager()
        # return wm.gDriveSetup(userID, request)

        final_dic = {'status': 1}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)
    except KeyError:
        return redirect(loadLoginPage)


def CreateV2BackupButton(request):
    import re
    try:
        userID = request.session['userID']
        data = json.loads(request.body)
        Selectedwebsite = data['Selectedwebsite']
        Selectedrepo = data['Selectedrepo']

        final_dic = {'status': 1, 'Selectedwebsite': Selectedwebsite, 'Selectedrepo': Selectedrepo}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

    except BaseException as msg:
        final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def RestoreV2backupSite(request):
    try:
        userID = request.session['userID']
        bm = BackupManager()
        return bm.RestoreV2backupSite(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def RestorePathV2(request):
    import re
    try:
        userID = request.session['userID']
        data = json.loads(request.body)
        SnapShotId = data['snapshotid']
        Path = data['path']

        final_dic = {'status': 1, 'SnapShotId': SnapShotId, 'Path': Path}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

    except BaseException as msg:
        final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def selectwebsiteRetorev2(request):
    import re
    try:
        userID = request.session['userID']
        data = json.loads(request.body)
        Selectedwebsite = data['Selectedwebsite']
        admin = Administrator.objects.get(pk=userID)

        obj = Websites.objects.get(domain = str(Selectedwebsite), admin = admin)
        #/home/cyberpanel.net/.config/rclone/rclone.conf
        path = '/home/%s/.config/rclone/rclone.conf' %(obj.domain)

        command = 'cat %s'%(path)
        result = pu.outputExecutioner(command)

        if result.find('host') > -1:
            pattern = r'\[(.*?)\]'
            matches = re.findall(pattern, result)
            final_json = json.dumps({'status': 1, 'fetchStatus': 1, 'error_message': "None", "data": matches})
            return HttpResponse(final_json)
        else:
            final_json = json.dumps({'status': 0, 'fetchStatus': 0, 'error_message': 'Could not Find repo'})
            return HttpResponse(final_json)


        # final_json = json.dumps({'status': 1, 'fetchStatus': 1, 'error_message': "None", "data": 1})
        # return HttpResponse(final_json)
    except BaseException as msg:
        final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def selectreporestorev2(request):
    try:
        userID = request.session['userID']
        data = json.loads(request.body)
        Selectedrepo = data['Selectedrepo']
        Selectedwebsite= data['Selectedwebsite']
        admin = Administrator.objects.get(pk=userID)

        # f'rustic -r testremote snapshots --password "" --json 2>/dev/null'
        # final_json = json.dumps({'status': 0, 'fetchStatus': 1, 'error_message': Selectedrepo })
        # return HttpResponse(final_json)

        vm = CPBackupsV2({'domain': Selectedwebsite, 'BackendName': Selectedrepo, })
        status, data = vm.FetchSnapShots()

        # ac=[
        #       [
        #         {
        #           "hostname": "ip-172-31-15-45.eu-central-1.compute.internal",
        #           "label": "",
        #           "paths": [
        #             "/home/backup/cyberpanel.net/config.json",
        #             "/home/cyberpanel.net",
        #             "MxS2hpJkGLVhZW.sql",
        #             "cybe_usman.sql",
        #             "cybe_usmans.sql",
        #             "qf4fza8IocVVqU.sql",
        #             "yKtbkp1THRlmBk.sql"
        #           ]
        #         },
        #         [
        #           {
        #             "time": "2023-03-10T09:32:14.116381993+00:00",
        #             "program_version": "rustic v0.4.4-38-g81650ff",
        #             "tree": "b398a0c342dbba4073f24ee72fe4b25123c76db1cbc59e99d014bf545726e93b",
        #             "paths": [
        #               "/home/backup/cyberpanel.net/config.json",
        #               "/home/cyberpanel.net",
        #               "MxS2hpJkGLVhZW.sql",
        #               "cybe_usman.sql",
        #               "cybe_usmans.sql",
        #               "qf4fza8IocVVqU.sql",
        #               "yKtbkp1THRlmBk.sql"
        #             ],
        #             "hostname": "ip-172-31-15-45.eu-central-1.compute.internal",
        #             "username": "",
        #             "uid": 0,
        #             "gid": 0,
        #             "tags": [],
        #             "original": "2f1003db93946aeea1dd02bea3648794fc547c61863423bfb002667079baa1e0",
        #             "summary": {
        #               "files_new": 0,
        #               "files_changed": 0,
        #               "files_unmodified": 3469,
        #               "dirs_new": 0,
        #               "dirs_changed": 2,
        #               "dirs_unmodified": 659,
        #               "data_blobs": 0,
        #               "tree_blobs": 2,
        #               "data_added": 1007,
        #               "data_added_packed": 618,
        #               "data_added_files": 0,
        #               "data_added_files_packed": 0,
        #               "data_added_trees": 1007,
        #               "data_added_trees_packed": 618,
        #               "total_files_processed": 3469,
        #               "total_dirs_processed": 661,
        #               "total_bytes_processed": 95956649,
        #               "total_dirsize_processed": 1612281,
        #               "total_duration": 0.105304887,
        #               "command": "rustic -r rclone:testremote:cyberpanel.net merge 22fa1914edaf884d722e8ad761863aab34e5d626602911602af4051efd73c587 e305fbceddc516972d18972830e340c24b436a17c8d8df25c5ef726ca1ce462d 12366c9ed1f4b31d288e9419d91236cebf0623ac05845605193977efae1a2880 e2dcdb6e3a96ff235a813c0b60ce2c34eddb5aa0abd15a2aec9bd6dcc2bb26bb b6a4bae0ff82d6bf4863c6b1860db239c8b91f7f980217fb3296749833ee4281 4799a31682522a17286f45689205991ce2cee238f556a51c71ac823c186ea332 aa9324a2807accc30b91b6578c62a5ca752a67e3caef5f9de6a684041554db7a --password  --json",
        #               "backup_start": "2023-03-10T09:32:14.127752385+00:00",
        #               "backup_end": "2023-03-10T09:32:14.221686880+00:00",
        #               "backup_duration": 0.093934495
        #             },
        #             "id": "2f1003db93946aeea1dd02bea3648794fc547c61863423bfb002667079baa1e0"
        #           },
        #           {
        #             "time": "2023-03-10T09:32:27.903095150+00:00",
        #             "program_version": "rustic v0.4.4-38-g81650ff",
        #             "tree": "397ebf2e96308728763b6ed6a5415852e5b1312d4eafcdf93909521d35933a49",
        #             "paths": [
        #               "/home/backup/cyberpanel.net/config.json",
        #               "/home/cyberpanel.net",
        #               "MxS2hpJkGLVhZW.sql",
        #               "cybe_usman.sql",
        #               "cybe_usmans.sql",
        #               "qf4fza8IocVVqU.sql",
        #               "yKtbkp1THRlmBk.sql"
        #             ],
        #             "hostname": "ip-172-31-15-45.eu-central-1.compute.internal",
        #             "username": "",
        #             "uid": 0,
        #             "gid": 0,
        #             "tags": [],
        #             "original": "2c899e20ad27d25a9b731c03a33e0b98d7d040eda47b6a34c97f4a3c9cbf2fc7",
        #             "summary": {
        #               "files_new": 0,
        #               "files_changed": 0,
        #               "files_unmodified": 3476,
        #               "dirs_new": 0,
        #               "dirs_changed": 2,
        #               "dirs_unmodified": 673,
        #               "data_blobs": 0,
        #               "tree_blobs": 2,
        #               "data_added": 1007,
        #               "data_added_packed": 619,
        #               "data_added_files": 0,
        #               "data_added_files_packed": 0,
        #               "data_added_trees": 1007,
        #               "data_added_trees_packed": 619,
        #               "total_files_processed": 3476,
        #               "total_dirs_processed": 675,
        #               "total_bytes_processed": 96567760,
        #               "total_dirsize_processed": 1620704,
        #               "total_duration": 0.101950563,
        #               "command": "rustic -r rclone:testremote:cyberpanel.net merge 6340ecbae01618a1f5def5e2620d778b6dcd9fc36074edcf9b8f0e52509798ed 1de78d7916fb6391bc7445b4a77967b6bf99ad9d0ed09d473ccb80c0be412fe0 2a31010ab415940d2c7d203ecabdd85d0dcc03f74351607808bc16137ec17b29 4a8e1bc5fbf6f228f1af619d97e1864e62b7e57c62840c0ecc68d255fed06e45 a510f06887c3d8535232ccec3a99a055c33e1a0d5671929b440a1f7a3e0fb396 f1d53a4d7d706a110d945d34f69f8fbffb4ec77787ec6fd36771572ef8f91a64 dd4a7eef8c8836624f11b0f5bff25303371886aaa5de30cf8035104529f193e3 --password  --json",
        #               "backup_start": "2023-03-10T09:32:27.913203884+00:00",
        #               "backup_end": "2023-03-10T09:32:28.005045713+00:00",
        #               "backup_duration": 0.091841829
        #             },
        #             "id": "2c899e20ad27d25a9b731c03a33e0b98d7d040eda47b6a34c97f4a3c9cbf2fc7"
        #           },
        #           {
        #             "time": "2023-03-10T09:34:44.180484566+00:00",
        #             "program_version": "rustic v0.4.4-38-g81650ff",
        #             "tree": "0e44a3eeca24698340f4c5a852570c2c7ae35f7c881c2208478516b576caa1e9",
        #             "paths": [
        #               "/home/backup/cyberpanel.net/config.json",
        #               "/home/cyberpanel.net",
        #               "MxS2hpJkGLVhZW.sql",
        #               "cybe_usman.sql",
        #               "cybe_usmans.sql",
        #               "qf4fza8IocVVqU.sql",
        #               "yKtbkp1THRlmBk.sql"
        #             ],
        #             "hostname": "ip-172-31-15-45.eu-central-1.compute.internal",
        #             "username": "",
        #             "uid": 0,
        #             "gid": 0,
        #             "tags": [],
        #             "original": "b2e3c5f38343531305538e53192c7499d81989ba98ec2356f8b578c4d8f758e6",
        #             "summary": {
        #               "files_new": 0,
        #               "files_changed": 0,
        #               "files_unmodified": 3483,
        #               "dirs_new": 0,
        #               "dirs_changed": 2,
        #               "dirs_unmodified": 686,
        #               "data_blobs": 0,
        #               "tree_blobs": 2,
        #               "data_added": 1007,
        #               "data_added_packed": 617,
        #               "data_added_files": 0,
        #               "data_added_files_packed": 0,
        #               "data_added_trees": 1007,
        #               "data_added_trees_packed": 617,
        #               "total_files_processed": 3483,
        #               "total_dirs_processed": 688,
        #               "total_bytes_processed": 96583806,
        #               "total_dirsize_processed": 1628726,
        #               "total_duration": 0.105863471,
        #               "command": "rustic -r rclone:testremote:cyberpanel.net merge da3e8ac0d680095d7317393b5403e8745638c385e9131ad82e69c7274acfea39 6b5b6a5471c91bfafc0cdc362c2bb231cad9b349407e6ff9641159c396862d6d 34e6356574fd57f61af52806b6190c4e0b765ca6e46e2c2fbb9dc597cabeeaa3 eec2b9a55d7e6c23a5c80f9804504efd838b51881d3181372d77d47abd45ffa2 cfa880f8d28aca6ecfab0a36681146cbabece413fbea91317e7255af14feb73a ef6fe3f125710a4d7a6b1026ecc14345f68cfdea4994399d4ae5af44cc97f966 a1c1e536f51dbf7fbf1565875b233e5ea2a72953ab22df9d8ba95d1b7d29185c --password  --json",
        #               "backup_start": "2023-03-10T09:34:44.191031543+00:00",
        #               "backup_end": "2023-03-10T09:34:44.286348037+00:00",
        #               "backup_duration": 0.095316494
        #             },
        #             "id": "b2e3c5f38343531305538e53192c7499d81989ba98ec2356f8b578c4d8f758e6"
        #           }
        #         ]
        #       ]
        #     ]
        # id = []
        # for item in ac[0][1]:
        #     id.append(item['id'])
        if status == 1:
            final_json = json.dumps({'status': 1, 'fetchStatus': 1, 'error_message': "None", "data": data})
            return HttpResponse(final_json)
        else:
            # final_json = json.dumps({'status': 0, 'fetchStatus': 1, 'error_message': ac,})
            final_json = json.dumps({'status': 0, 'fetchStatus': 1, 'error_message': 'Cannot Find!',})
            return HttpResponse(final_json)


    except BaseException as msg:
        final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)