#!/usr/local/CyberCP/bin/python

import os.path
import sys
import django
from datetime import datetime

from plogical.DockerSites import Docker_Sites

sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import json
from plogical.acl import ACLManager
import plogical.CyberCPLogFileWriter as logging
from plogical.errorSanitizer import secure_error_response, secure_log_error
from django.shortcuts import HttpResponse, render, redirect
from django.urls import reverse
from django.db.utils import OperationalError
from loginSystem.models import Administrator
import subprocess
import shlex
import time
from dockerManager.models import Containers
from math import ceil
import docker
import docker.utils
import requests
from plogical.processUtilities import ProcessUtilities
from serverStatus.serverStatusUtil import ServerStatusUtil
import threading as multi
from plogical.httpProc import httpProc

# Use default socket to connect
class ContainerManager(multi.Thread):

    def __init__(self, name=None, function=None, request = None, templateName = None, data = None):
        multi.Thread.__init__(self)
        self.name = name
        self.function = function
        self.request = request
        self.templateName = templateName
        self.data = data

    def renderDM(self):
        proc = httpProc(self.request, self.templateName, self.data, 'admin')
        return proc.render()

    def run(self):
        try:
            if self.function == 'submitInstallDocker':
                self.submitInstallDocker()
            elif self.function == 'restartGunicorn':
                command = 'sudo systemctl restart gunicorn.socket'
                ProcessUtilities.executioner(command)
        except Exception as msg:
            logging.CyberCPLogFileWriter.writeToFile( str(msg) + ' [ContainerManager.run]')

    @staticmethod
    def executioner(command, statusFile):
        try:
            res = subprocess.call(shlex.split(command), stdout=statusFile, stderr=statusFile)
            if res == 1:
                return 0
            else:
                return 1
        except Exception as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return 0

    def submitInstallDocker(self):
        try:
            currentACL = ACLManager.loadedACL(self.name)

            if ACLManager.currentContextPermission(currentACL, 'createContainer') == 0:
                return ACLManager.loadError()

            writeToFile = open(ServerStatusUtil.lswsInstallStatusPath, 'w')
            writeToFile.close()

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/dockerManager/dockerInstall.py"
            ProcessUtilities.executioner(execPath)

            time.sleep(2)

        except Exception as msg:
            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath, str(msg) + ' [404].', 1)

    def createContainer(self, request=None, userID=None, data=None):
        client = docker.from_env()
        dockerAPI = docker.APIClient()

        adminNames = ACLManager.loadAllUsers(userID)
        tag = request.GET.get('tag')
        image = request.GET.get('image')
        tag = tag.split(" (")[0]

        if "/" in image:
            name = image.split("/")[0] + "." + image.split("/")[1]
        else:
            name = image

        try:
            inspectImage = dockerAPI.inspect_image(image + ":" + tag)
        except docker.errors.ImageNotFound:
            val = request.session['userID']
            admin = Administrator.objects.get(pk=val)
            proc = httpProc(request, 'dockerManager/images.html', {"type": admin.type,
                                                                 'image': image,
                                                                 'tag': tag})
            return proc.render()

        envList = {};
        if 'Env' in inspectImage['Config']:
            for item in inspectImage['Config']['Env']:
                if '=' in item:
                    splitedItem = item.split('=', 1)
                    print(splitedItem)
                    envList[splitedItem[0]] = splitedItem[1]
                else:
                    envList[item] = ""

        portConfig = {};
        if 'ExposedPorts' in inspectImage['Config']:
            for item in inspectImage['Config']['ExposedPorts']:
                portDef = item.split('/')
                portConfig[portDef[0]] = portDef[1]

        if image is None or image == '' or tag is None or tag == '':
            return redirect(reverse('containerImage'))

        Data = {"ownerList": adminNames, "image": image, "name": name, "tag": tag, "portConfig": portConfig,
                "envList": envList}

        template = 'dockerManager/runContainer.html'
        proc = httpProc(request, template, Data, 'admin')
        return proc.render()

    def loadContainerHome(self, request=None, userID=None, data=None):
        try:
            name = self.name

            # Check if user is admin or has container access
            currentACL = ACLManager.loadedACL(userID)
            if currentACL['admin'] != 1:
                # For non-admin users, check container ownership
                if ACLManager.checkContainerOwnership(name, userID) != 1:
                    return ACLManager.loadError()
            # Admin users can access any container, including ones not in database

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            try:
                container = client.containers.get(name)
            except docker.errors.NotFound as err:
                return HttpResponse("Container not found")

            data = {}
            try:
                con = Containers.objects.get(name=name)
                data['name'] = name
                data['image'] = con.image + ":" + con.tag
                data['ports'] = json.loads(con.ports)
                data['cid'] = con.cid
                data['envList'] = json.loads(con.env)
                data['volList'] = json.loads(con.volumes)
                data['memoryLimit'] = con.memory
                if con.startOnReboot == 1:
                    data['startOnReboot'] = 'true'
                    data['restartPolicy'] = "Yes"
                else:
                    data['startOnReboot'] = 'false'
                    data['restartPolicy'] = "No"
            except Containers.DoesNotExist:
                # Container exists in Docker but not in database
                data['name'] = name
                data['image'] = container.image.tags[0] if container.image.tags else "Unknown"
                data['ports'] = {}
                data['cid'] = container.id
                data['envList'] = {}
                data['volList'] = {}
                data['memoryLimit'] = 512
                data['startOnReboot'] = 'false'
                data['restartPolicy'] = "No"

            stats = container.stats(decode=False, stream=False)
            logs = container.logs(stream=True)

            data['status'] = container.status

            if 'usage' in stats['memory_stats']:
                # Calculate Usage
                # Source: https://github.com/docker/docker/blob/28a7577a029780e4533faf3d057ec9f6c7a10948/api/client/stats.go#L309
                data['memoryUsage'] = (stats['memory_stats']['usage'] / stats['memory_stats']['limit']) * 100

                try:
                    cpu_count = len(stats["cpu_stats"]["cpu_usage"]["percpu_usage"])
                except:
                    cpu_count = 0

                data['cpuUsage'] = 0.0
                cpu_delta = float(stats["cpu_stats"]["cpu_usage"]["total_usage"]) - \
                            float(stats["precpu_stats"]["cpu_usage"]["total_usage"])
                system_delta = float(stats["cpu_stats"]["system_cpu_usage"]) - \
                               float(stats["precpu_stats"]["system_cpu_usage"])
                if system_delta > 0.0:
                    data['cpuUsage'] = round(cpu_delta / system_delta * 100.0 * cpu_count, 3)
            else:
                data['memoryUsage'] = 0
                data['cpuUsage'] = 0

            template = 'dockerManager/viewContainer.html'
            proc = httpProc(request, template, data, 'admin')
            return proc.render()
        except Exception as e:
            secure_log_error(e, 'container_operation')
            return HttpResponse('Operation failed')

    def listContainers(self, request=None, userID=None, data=None):
        def _render_list():
            client = docker.from_env()
            docker.APIClient()  # ensure API is usable

            currentACL = ACLManager.loadedACL(userID)
            containers = ACLManager.findAllContainers(currentACL, userID)

            allContainers = client.containers.list()
            showUnlistedContainer = True

            unlistedContainers = []
            for container in allContainers:
                if container.name not in containers:
                    unlistedContainers.append(container)

            if not unlistedContainers:
                showUnlistedContainer = False

            adminNames = ACLManager.loadAllUsers(userID)

            pages = float(len(containers)) / float(10)
            pagination = []

            if pages <= 1.0:
                pages = 1
                pagination.append('<li><a href="\#"></a></li>')
            else:
                pages = ceil(pages)
                finalPages = int(pages) + 1

                for i in range(1, finalPages):
                    pagination.append('<li><a href="\#">' + str(i) + '</a></li>')

            template = 'dockerManager/listContainers.html'
            proc = httpProc(request, template, {"pagination": pagination,
                                                "unlistedContainers": unlistedContainers,
                                                "adminNames": adminNames,
                                                "showUnlistedContainer": showUnlistedContainer}, 'admin')
            return proc.render()

        try:
            return _render_list()
        except OperationalError as e:
            logging.writeToFile(
                "Docker containers list: DB error (table may be missing). Running migrations. Error: %s" % str(e)
            )
            try:
                from django.core.management import call_command
                call_command('migrate', 'dockerManager', verbosity=0)
                return _render_list()
            except Exception as migrate_err:
                logging.writeToFile(
                    "Docker containers list: migrate failed. Error: %s" % str(migrate_err)
                )
                return render(
                    request,
                    'baseTemplate/error.html',
                    {'error_message': 'Docker Manager database not ready. Please run upgrade or: manage.py migrate dockerManager'}
                )
        except Exception as e:
            secure_log_error(e, 'docker_list_containers')
            return render(
                request,
                'baseTemplate/error.html',
                {'error_message': 'Containers list could not be loaded. Check error logs.'}
            )

    def getContainerLogs(self, userID=None, data=None):
        try:
            name = data['name']

            # Check if container is registered in database or unlisted
            if Containers.objects.filter(name=name).exists():
                if ACLManager.checkContainerOwnership(name, userID) != 1:
                    return ACLManager.loadErrorJson('containerLogStatus', 0)

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            container = client.containers.get(name)
            
            # Get logs with proper formatting
            try:
                # Get logs with timestamps and proper formatting
                logs = container.logs(
                    stdout=True, 
                    stderr=True, 
                    timestamps=True,
                    tail=1000  # Limit to last 1000 lines for performance
                ).decode("utf-8", errors='replace')
                
                # Clean up the logs for better display
                if logs:
                    # Split into lines and clean up
                    log_lines = logs.split('\n')
                    cleaned_lines = []
                    
                    for line in log_lines:
                        # Remove Docker's log prefix if present
                        if line.startswith('[') and ']' in line:
                            # Extract timestamp and message
                            try:
                                timestamp_end = line.find(']')
                                if timestamp_end > 0:
                                    timestamp = line[1:timestamp_end]
                                    message = line[timestamp_end + 1:].strip()
                                    
                                    # Format the line nicely
                                    if message:
                                        cleaned_lines.append(f"[{timestamp}] {message}")
                                else:
                                    cleaned_lines.append(line)
                            except:
                                cleaned_lines.append(line)
                        else:
                            cleaned_lines.append(line)
                    
                    logs = '\n'.join(cleaned_lines)
                else:
                    logs = "No logs available for this container."
                    
            except Exception as log_err:
                # Fallback to basic logs if timestamped logs fail
                try:
                    logs = container.logs().decode("utf-8", errors='replace')
                    if not logs:
                        logs = "No logs available for this container."
                except:
                    logs = f"Error retrieving logs: {str(log_err)}"

            data_ret = {
                'containerLogStatus': 1, 
                'containerLog': logs, 
                'error_message': "None",
                'container_status': container.status,
                'log_count': len(logs.split('\n')) if logs else 0
            }
            json_data = json.dumps(data_ret, ensure_ascii=False)
            return HttpResponse(json_data)

        except Exception as e:
            secure_log_error(e, 'containerLogStatus')
            data_ret = secure_error_response(e, 'Failed to containerLogStatus')
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def submitContainerCreation(self, userID=None, data=None):
        try:

            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadErrorJson('createContainerStatus', 0)

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            name = data['name']
            image = data['image']
            tag = data['tag']
            dockerOwner = data['dockerOwner']
            memory = data['memory']
            envList = data['envList']
            volList = data['volList']

            try:
                inspectImage = dockerAPI.inspect_image(image + ":" + tag)
            except docker.errors.APIError as err:
                error_message = str(err)
                data_ret = {'createContainerStatus': 0, 'error_message': f'Failed to inspect image: {error_message}'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except docker.errors.ImageNotFound as err:
                error_message = str(err)
                data_ret = {'createContainerStatus': 0, 'error_message': f'Image not found: {error_message}'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except Exception as err:
                error_message = str(err)
                data_ret = {'createContainerStatus': 0, 'error_message': f'Error inspecting image: {error_message}'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            
            portConfig = {}

            # Formatting envList for usage - handle both simple and advanced modes
            envDict = {}
            
            # Check if advanced mode is being used
            advanced_mode = data.get('advancedEnvMode', False)
            
            if advanced_mode:
                # Advanced mode: envList is already a dictionary of key-value pairs
                envDict = envList
            else:
                # Simple mode: envList is an array of objects with name/value properties
                for key, value in envList.items():
                    if isinstance(value, dict) and (value.get('name', '') != '' or value.get('value', '') != ''):
                        envDict[value['name']] = value['value']
                    elif isinstance(value, str) and value != '':
                        # Handle case where value might be a string (fallback)
                        envDict[key] = value

            if 'ExposedPorts' in inspectImage['Config']:
                for item in inspectImage['Config']['ExposedPorts']:
                    # Check if port data exists and is valid
                    if item in data and data[item]:
                        try:
                            port_num = int(data[item])
                            # Do not allow priviledged port numbers
                            if port_num < 1024 or port_num > 65535:
                                data_ret = {'createContainerStatus': 0, 'error_message': "Choose port between 1024 and 65535"}
                                json_data = json.dumps(data_ret)
                                return HttpResponse(json_data)
                            portConfig[item] = data[item]
                        except (ValueError, TypeError):
                            data_ret = {'createContainerStatus': 0, 'error_message': f"Invalid port number: {data[item]}"}
                            json_data = json.dumps(data_ret)
                            return HttpResponse(json_data)

            volumes = {}
            if volList:
                for index, volume in volList.items():
                    if isinstance(volume, dict) and 'src' in volume and 'dest' in volume:
                        volumes[volume['src']] = {'bind': volume['dest'], 'mode': 'rw'}

            # Network configuration
            network = data.get('network', 'bridge')  # Default to bridge network
            network_mode = data.get('network_mode', 'bridge')
            
            # Extra options support (like --add-host)
            extra_hosts = {}
            extra_options = data.get('extraOptions', {})
            if extra_options:
                for option, value in extra_options.items():
                    if option == 'add_host' and value:
                        # Parse --add-host entries (format: hostname:ip)
                        for host_entry in value.split(','):
                            if ':' in host_entry:
                                hostname, ip = host_entry.strip().split(':', 1)
                                extra_hosts[hostname.strip()] = ip.strip()

            ## Create Configurations
            admin = Administrator.objects.get(userName=dockerOwner)

            containerArgs = {'image': image + ":" + tag,
                             'detach': True,
                             'name': name,
                             'ports': portConfig,
                             'publish_all_ports': True,
                             'environment': envDict,
                             'volumes': volumes,
                             'network_mode': network_mode}

            # Add network configuration
            if network != 'bridge' or network_mode == 'bridge':
                containerArgs['network'] = network
            
            # Add extra hosts if specified
            if extra_hosts:
                containerArgs['extra_hosts'] = extra_hosts

            containerArgs['mem_limit'] = memory * 1048576;  # Converts MB to bytes ( 0 * x = 0 for unlimited memory)

            try:
                container = client.containers.create(**containerArgs)
            except docker.errors.APIError as err:
                # Handle Docker API errors properly
                error_message = str(err)
                if "port is already allocated" in error_message:  # We need to delete container if port is not available
                    print("Deleting container")
                    try:
                        container.remove(force=True)
                    except:
                        pass  # Container might not exist yet
                data_ret = {'createContainerStatus': 0, 'error_message': f'Docker API error: {error_message}'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except docker.errors.ImageNotFound as err:
                error_message = str(err)
                data_ret = {'createContainerStatus': 0, 'error_message': f'Image not found: {error_message}'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except docker.errors.ContainerError as err:
                error_message = str(err)
                data_ret = {'createContainerStatus': 0, 'error_message': f'Container error: {error_message}'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except Exception as err:
                # Handle any other exceptions
                error_message = str(err) if err else "Unknown error occurred"
                data_ret = {'createContainerStatus': 0, 'error_message': f'Container creation error: {error_message}'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            con = Containers(admin=admin,
                             name=name,
                             tag=tag,
                             image=image,
                             memory=memory,
                             ports=json.dumps(portConfig),
                             network=network,
                             network_mode=network_mode,
                             extra_options=json.dumps(extra_options),
                             volumes=json.dumps(volumes),
                             env=json.dumps(envDict),
                             cid=container.id)

            con.save()

            data_ret = {'createContainerStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except Exception as msg:
            # Ensure error message is properly converted to string
            error_message = str(msg) if msg else "Unknown error occurred"
            data_ret = {'createContainerStatus': 0, 'error_message': error_message}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def submitInstallImage(self, userID=None, data=None):
        try:

            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadErrorJson('installImageStatus', 0)

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            image = data['image']
            tag = data['tag']

            try:
                inspectImage = dockerAPI.inspect_image(image + ":" + tag)
                data_ret = {'installImageStatus': 0, 'error_message': "Image already installed"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except docker.errors.ImageNotFound:
                pass

            try:
                image = client.images.pull(image, tag=tag)
                print(image.id)
            except docker.errors.APIError as msg:
                data_ret = {'installImageStatus': 0, 'error_message': str(msg)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            data_ret = {'installImageStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except Exception as msg:
            data_ret = {'installImageStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def pullImage(self, userID=None, data=None):
        """
        Pull a Docker image from registry with proper error handling and security checks
        """
        try:
            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadErrorJson('pullImageStatus', 0)

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            image = data['image']
            tag = data.get('tag', 'latest')

            # Validate image name to prevent injection
            if not self._validate_image_name(image):
                data_ret = {'pullImageStatus': 0, 'error_message': 'Invalid image name format'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            # Check if image already exists
            try:
                inspectImage = dockerAPI.inspect_image(image + ":" + tag)
                data_ret = {'pullImageStatus': 0, 'error_message': "Image already exists locally"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except docker.errors.ImageNotFound:
                pass

            # Pull the image
            try:
                pulled_image = client.images.pull(image, tag=tag)
                data_ret = {
                    'pullImageStatus': 1, 
                    'error_message': "None",
                    'image_id': pulled_image.id,
                    'image_name': image,
                    'tag': tag
                }
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except docker.errors.APIError as err:
                data_ret = {'pullImageStatus': 0, 'error_message': f'Docker API error: {str(err)}'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except docker.errors.ImageNotFound as err:
                data_ret = {'pullImageStatus': 0, 'error_message': f'Image not found: {str(err)}'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except Exception as msg:
            data_ret = {'pullImageStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def _validate_image_name(self, image_name):
        """Validate Docker image name to prevent injection attacks"""
        if not image_name or len(image_name) > 255:
            return False
        
        # Allow alphanumeric, hyphens, underscores, dots, and forward slashes
        import re
        pattern = r'^[a-zA-Z0-9._/-]+$'
        return re.match(pattern, image_name) is not None

    def submitContainerDeletion(self, userID=None, data=None, called=False):
        try:
            name = data['name']
            # Check if container is registered in database or unlisted
            if Containers.objects.filter(name=name).exists():
                if ACLManager.checkContainerOwnership(name, userID) != 1:
                    if called:
                        return 'Permission error'
                    else:
                        return ACLManager.loadErrorJson('websiteDeleteStatus', 0)

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            unlisted = data['unlisted']

            if 'force' in data:
                force = True
            else:
                force = False

            if not unlisted:
                containerOBJ = Containers.objects.get(name=name)

            if not force:
                try:
                    container = client.containers.get(name)
                except docker.errors.NotFound as err:
                    if called:
                        return 'Container does not exist'
                    else:
                        data_ret = {'delContainerStatus': 2, 'error_message': 'Container does not exist'}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)

                try:
                    container.stop()  # Stop container
                    container.kill()  # INCASE graceful stop doesn't work
                except:
                    pass

                try:
                    container.remove()  # Finally remove container
                except docker.errors.APIError as err:
                    data_ret = {'delContainerStatus': 0, 'error_message': str(err)}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                except:
                    if called:
                        return "Unknown"
                    else:
                        data_ret = {'delContainerStatus': 0, 'error_message': 'Unknown error'}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)

            if not unlisted and not called:
                containerOBJ.delete()

            if called:
                return 0
            else:
                data_ret = {'delContainerStatus': 1, 'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            if called:
                return str(msg)
            else:
                data_ret = {'delContainerStatus': 0, 'error_message': str(msg)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

    def getContainerList(self, userID=None, data=None):
        try:
            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadErrorJson('listContainerStatus', 0)

            currentACL = ACLManager.loadedACL(userID)
            pageNumber = max(1, int(data.get('page', 1)))
            items_per_page = 10

            all_containers = ACLManager.findContainersObjects(currentACL, userID)
            totalCount = len(all_containers)
            totalPages = max(1, int(ceil(float(totalCount) / float(items_per_page))))

            start = (pageNumber - 1) * items_per_page
            end = start + items_per_page
            page_containers = all_containers[start:end]

            rows = []
            for items in page_containers:
                rows.append({'name': items.name, 'admin': items.admin.userName, 'tag': items.tag, 'image': items.image})
            json_data = json.dumps(rows)

            final_dic = {
                'listContainerStatus': 1,
                'error_message': 'None',
                'data': json_data,
                'totalCount': totalCount,
                'totalPages': totalPages,
                'currentPage': pageNumber,
                'itemsPerPage': items_per_page
            }
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
        except BaseException as msg:
            dic = {'listContainerStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    def findContainersJson(self, currentACL, userID, pageNumber):
        admin = Administrator.objects.get(pk=userID)
        if admin.acl.adminStatus != 1:
            return ACLManager.loadError()

        finalPageNumber = ((pageNumber * 10)) - 10
        endPageNumber = finalPageNumber + 10
        containers = ACLManager.findContainersObjects(currentACL, userID)[finalPageNumber:endPageNumber]

        json_data = "["
        checker = 0

        for items in containers:
            dic = {'name': items.name, 'admin': items.admin.userName, 'tag': items.tag, 'image': items.image}

            if checker == 0:
                json_data = json_data + json.dumps(dic)
                checker = 1
            else:
                json_data = json_data + ',' + json.dumps(dic)

        json_data = json_data + ']'

        return json_data

    def doContainerAction(self, userID=None, data=None):
        try:

            name = data['name']
            if ACLManager.checkContainerOwnership(name, userID) != 1:
                return ACLManager.loadErrorJson('containerActionStatus', 0)

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            action = data['action']
            try:
                container = client.containers.get(name)
            except docker.errors.NotFound as err:
                data_ret = {'containerActionStatus': 0, 'error_message': 'Container does not exist'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except:
                data_ret = {'containerActionStatus': 0, 'error_message': 'Unknown'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            try:
                if action == 'start':
                    container.start()
                elif action == 'stop':
                    container.stop()
                elif action == 'restart':
                    container.restart()
                else:
                    data_ret = {'containerActionStatus': 0, 'error_message': 'Unknown Action'}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
            except docker.errors.APIError as err:
                data_ret = {'containerActionStatus': 0, 'error_message': str(err)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            time.sleep(3)  # Wait 3 seconds for container to finish starting/stopping/restarting
            status = container.status
            data_ret = {'containerActionStatus': 1, 'error_message': 'None', 'status': status}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except Exception as e:
            secure_log_error(e, 'containerActionStatus')
            data_ret = secure_error_response(e, 'Failed to containerActionStatus')
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def getContainerStatus(self, userID=None, data=None):
        try:
            name = data['name']
            if ACLManager.checkContainerOwnership(name, userID) != 1:
                return ACLManager.loadErrorJson('containerStatus', 0)

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            try:
                container = client.containers.get(name)
            except docker.errors.NotFound as err:
                data_ret = {'containerStatus': 0, 'error_message': 'Container does not exist'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except:
                data_ret = {'containerStatus': 0, 'error_message': 'Unknown'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            status = container.status
            data_ret = {'containerStatus': 1, 'error_message': 'None', 'status': status}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except Exception as e:
            secure_log_error(e, 'containerStatus')
            data_ret = secure_error_response(e, 'Failed to containerStatus')
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def exportContainer(self, request=None, userID=None, data=None):
        try:
            name = request.GET.get('name')
            if ACLManager.checkContainerOwnership(name, userID) != 1:
                return ACLManager.loadErrorJson('containerStatus', 0)

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            try:
                container = client.containers.get(name)
            except docker.errors.NotFound as err:
                data_ret = {'containerStatus': 0, 'error_message': 'Container does not exist'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except:
                data_ret = {'containerStatus': 0, 'error_message': 'Unknown'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            eFile = container.export()  # Export with default chunk size
            response = HttpResponse(eFile, content_type='application/force-download')
            response['Content-Disposition'] = 'attachment; filename="' + name + '.tar"'
            return response

        except Exception as e:
            secure_log_error(e, 'containerStatus')
            data_ret = secure_error_response(e, 'Failed to containerStatus')
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def getContainerTop(self, userID=None, data=None):
        try:
            name = data['name']
            if ACLManager.checkContainerOwnership(name, userID) != 1:
                return ACLManager.loadErrorJson('containerTopStatus', 0)

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            try:
                container = client.containers.get(name)
            except docker.errors.NotFound as err:
                data_ret = {'containerTopStatus': 0, 'error_message': 'Container does not exist'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except:
                data_ret = {'containerTopStatus': 0, 'error_message': 'Unknown'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            try:
                top = container.top()
            except docker.errors.APIError as err:
                data_ret = {'containerTopStatus': 0, 'error_message': str(err)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            data_ret = {'containerTopStatus': 1, 'error_message': 'None', 'processes': top}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except Exception as e:
            secure_log_error(e, 'containerTopStatus')
            data_ret = secure_error_response(e, 'Failed to containerTopStatus')
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def assignContainer(self, userID=None, data=None):
        try:
            # Todo: add check only for super user i.e. main admin
            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadErrorJson('assignContainerStatus', 0)

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            name = data['name']
            dockerOwner = data['admin']

            admin = Administrator.objects.get(userName=dockerOwner)

            try:
                container = client.containers.get(name)
            except docker.errors.NotFound as err:
                data_ret = {'assignContainerStatus': 0, 'error_message': 'Container does not exist'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except:
                data_ret = {'assignContainerStatus': 0, 'error_message': 'Unknown'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            con = Containers(admin=admin,
                             name=name,
                             cid=container.id)

            con.save()

            data_ret = {'assignContainerStatus': 1, 'error_message': 'None'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except Exception as e:
            secure_log_error(e, 'assignContainerStatus')
            data_ret = secure_error_response(e, 'Failed to assignContainerStatus')
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def searchImage(self, userID=None, data=None):
        try:
            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadErrorJson('searchImageStatus', 0)

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            string = data['string']
            try:
                matches = client.images.search(term=string)
            except docker.errors.APIError as err:
                data_ret = {'searchImageStatus': 0, 'error_message': str(err)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except:
                data_ret = {'searchImageStatus': 0, 'error_message': 'Unknown'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            print(json.dumps(matches))

            for image in matches:
                if "/" in image['name']:
                    image['name2'] = image['name'].split("/")[0] + ":" + image['name'].split("/")[1]
                else:
                    image['name2'] = image['name']

            data_ret = {'searchImageStatus': 1, 'error_message': 'None', 'matches': matches}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except Exception as e:
            secure_log_error(e, 'searchImageStatus')
            data_ret = secure_error_response(e, 'Failed to searchImageStatus')
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def images(self, request=None, userID=None, data=None):
        try:
            admin = Administrator.objects.get(pk=userID)

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            try:
                imageList = client.images.list()
            except docker.errors.APIError as err:
                return HttpResponse(str(err))

            images = {}
            names = []

            for image in imageList:
                try:
                    name = image.attrs['RepoTags'][0].split(":")[0]
                    if "/" in name:
                        name2 = ""
                        for item in name.split("/"):
                            name2 += ":" + item
                    else:
                        name2 = name

                    tags = []
                    for tag in image.tags:
                        getTag = tag.split(":")
                        if len(getTag) == 2:
                            tags.append(getTag[1])
                    print(tags)
                    if name in names:
                        images[name]['tags'].extend(tags)
                    else:
                        names.append(name)
                        images[name] = {"name": name,
                                        "name2": name2,
                                        "tags": tags}
                except:
                    continue

            template = 'dockerManager/images.html'
            proc = httpProc(request, template, {"images": images, "test": ''}, 'admin')
            return proc.render()

        except Exception as e:
            secure_log_error(e, 'container_operation')
            return HttpResponse('Operation failed')

    def manageImages(self, request=None, userID=None, data=None):
        try:

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            imageList = client.images.list()

            images = {}
            names = []

            for image in imageList:
                try:
                    name = image.attrs['RepoTags'][0].split(":")[0]
                    if name in names:
                        images[name]['tags'].extend(image.tags)
                    else:
                        names.append(name)
                        images[name] = {"name": name,
                                        "tags": image.tags}
                except:
                    continue

            template = 'dockerManager/manageImages.html'
            proc = httpProc(request, template, {"images": images}, 'admin')
            return proc.render()

        except Exception as e:
            secure_log_error(e, 'container_operation')
            return HttpResponse('Operation failed')

    def getImageHistory(self, userID=None, data=None):
        try:

            name = data['name']

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            try:
                image = client.images.get(name)
            except docker.errors.APIError as err:
                data_ret = {'imageHistoryStatus': 0, 'error_message': str(err)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except:
                data_ret = {'imageHistoryStatus': 0, 'error_message': 'Unknown'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            data_ret = {'imageHistoryStatus': 1, 'error_message': 'None', 'history': image.history()}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except Exception as e:
            secure_log_error(e, 'imageHistoryStatus')
            data_ret = secure_error_response(e, 'Failed to imageHistoryStatus')
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def removeImage(self, userID=None, data=None):
        try:
            admin = Administrator.objects.get(pk=userID)

            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            name = data['name']
            force = data.get('force', False)
            
            try:
                if name == 0:
                    # Prune unused images
                    action = client.images.prune()
                else:
                    # First, try to remove containers that might be using this image
                    containers_using_image = []
                    try:
                        for container in client.containers.list(all=True):
                            container_image = container.attrs['Config']['Image']
                            if container_image == name or container_image.startswith(name + ':'):
                                containers_using_image.append(container)
                    except Exception as e:
                        logging.CyberCPLogFileWriter.writeToFile(f'Error checking containers for image {name}: {str(e)}')
                    
                    # Remove containers that are using this image
                    for container in containers_using_image:
                        try:
                            if container.status == 'running':
                                container.stop()
                                time.sleep(1)
                            container.remove(force=True)
                            logging.CyberCPLogFileWriter.writeToFile(f'Removed container {container.name} that was using image {name}')
                        except Exception as e:
                            logging.CyberCPLogFileWriter.writeToFile(f'Error removing container {container.name}: {str(e)}')
                    
                    # Now try to remove the image
                    try:
                        if force:
                            action = client.images.remove(name, force=True)
                        else:
                            action = client.images.remove(name)
                        logging.CyberCPLogFileWriter.writeToFile(f'Successfully removed image {name}')
                    except docker.errors.APIError as err:
                        error_msg = str(err)
                        if "conflict: unable to remove repository reference" in error_msg and "must force" in error_msg:
                            # Try with force if not already forced
                            if not force:
                                logging.CyberCPLogFileWriter.writeToFile(f'Retrying image removal with force: {name}')
                                action = client.images.remove(name, force=True)
                            else:
                                raise err
                        else:
                            raise err
                
                print(action)
            except docker.errors.APIError as err:
                error_message = str(err)
                # Provide more helpful error messages
                if "conflict: unable to remove repository reference" in error_message:
                    error_message = f"Image {name} is still being used by containers. Use force removal to delete it."
                elif "No such image" in error_message:
                    error_message = f"Image {name} not found or already removed."
                
                data_ret = {'removeImageStatus': 0, 'error_message': error_message}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except Exception as e:
                data_ret = {'removeImageStatus': 0, 'error_message': f'Unknown error: {str(e)}'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            data_ret = {'removeImageStatus': 1, 'error_message': 'None'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except Exception as e:
            secure_log_error(e, 'removeImageStatus')
            data_ret = secure_error_response(e, 'Failed to removeImageStatus')
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

            # Internal function for recreating containers

    def doRecreateContainer(self, userID, data, con):
        try:

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            name = data['name']
            unlisted = data['unlisted']  # Pass this as 1 if image is not known for container
            image = data['image']
            tag = data['tag']
            env = data['env']
            volumes = data['volumes']
            port = data['ports']
            memory = data['memory']

            if image == 'unknown':
                return "Image name not known"
            # Call container delete function
            delStatus = self.submitContainerDeletion(userID, data, True)
            if delStatus != 0:
                return delStatus

            containerArgs = {'image': image + ":" + tag,
                             'detach': True,
                             'name': name,
                             'ports': port,
                             'environment': env,
                             'volumes': volumes,
                             'publish_all_ports': True,
                             'mem_limit': memory * 1048576}

            if con.startOnReboot == 1:
                containerArgs['restart_policy'] = {"Name": "always"}

            container = client.containers.create(**containerArgs)
            con.cid = container.id
            con.save()

            return 0
        except Exception as e:
            secure_log_error(e, 'container_operation')
            return 'Operation failed'

    def saveContainerSettings(self, userID=None, data=None):
        try:
            name = data['name']
            if ACLManager.checkContainerOwnership(name, userID) != 1:
                return ACLManager.loadErrorJson('saveSettingsStatus', 0)

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            memory = data['memory']
            startOnReboot = data['startOnReboot']
            envList = data['envList']
            volList = data['volList']

            if startOnReboot == True:
                startOnReboot = 1
                rPolicy = {"Name": "always"}
            else:
                startOnReboot = 0
                rPolicy = {}

            try:
                container = client.containers.get(name)
            except docker.errors.NotFound as err:
                data_ret = {'saveSettingsStatus': 0, 'error_message': 'Container does not exist'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except:
                data_ret = {'saveSettingsStatus': 0, 'error_message': 'Unknown'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            try:
                container.update(mem_limit=memory * 1048576,
                                 restart_policy=rPolicy)
            except docker.errors.APIError as err:
                data_ret = {'saveSettingsStatus': 0, 'error_message': str(err)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            con = Containers.objects.get(name=name)
            con.memory = memory
            con.startOnReboot = startOnReboot

            if 'envConfirmation' in data and data['envConfirmation']:
                # Formatting envList for usage - handle both simple and advanced modes
                envDict = {}
                
                # Check if advanced mode is being used
                advanced_mode = data.get('advancedEnvMode', False)
                
                if advanced_mode:
                    # Advanced mode: envList is already a dictionary of key-value pairs
                    envDict = envList
                else:
                    # Simple mode: envList is an array of objects with name/value properties
                    for key, value in envList.items():
                        if isinstance(value, dict) and (value.get('name', '') != '' or value.get('value', '') != ''):
                            envDict[value['name']] = value['value']
                        elif isinstance(value, str) and value != '':
                            # Handle case where value might be a string (fallback)
                            envDict[key] = value

                volumes = {}
                for index, volume in volList.items():
                    if volume['src'] == '' or volume['dest'] == '':
                        continue
                    volumes[volume['src']] = {'bind': volume['dest'],
                                              'mode': 'rw'}
                # Prepare data for recreate function
                data = {
                    'name': name,
                    'unlisted': 0,
                    'image': con.image,
                    'tag': con.tag,
                    'env': envDict,
                    'ports': json.loads(con.ports),
                    'volumes': volumes,
                    'memory': con.memory
                }

                recreateStatus = self.doRecreateContainer(userID, data, con)
                if recreateStatus != 0:
                    data_ret = {'saveSettingsStatus': 0, 'error_message': str(recreateStatus)}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                con.env = json.dumps(envDict)
                con.volumes = json.dumps(volumes)
            con.save()

            data_ret = {'saveSettingsStatus': 1, 'error_message': 'None'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except Exception as e:
            secure_log_error(e, 'saveSettingsStatus')
            data_ret = secure_error_response(e, 'Failed to saveSettingsStatus')
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def recreateContainer(self, userID=None, data=None):
        try:
            name = data['name']
            if ACLManager.checkContainerOwnership(name, userID) != 1:
                return ACLManager.loadErrorJson('saveSettingsStatus', 0)

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            try:
                container = client.containers.get(name)
            except docker.errors.NotFound as err:
                data_ret = {'recreateContainerStatus': 0, 'error_message': 'Container does not exist'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except:
                data_ret = {'recreateContainerStatus': 0, 'error_message': 'Unknown'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            con = Containers.objects.get(name=name)

            # Prepare data for recreate function
            data = {
                'name': name,
                'unlisted': 0,
                'image': con.image,
                'tag': con.tag,
                'env': json.loads(con.env),
                'ports': json.loads(con.ports),
                'volumes': json.loads(con.volumes),
                # No filter needed now as its ports are filtered when adding to database
                'memory': con.memory
            }

            recreateStatus = self.doRecreateContainer(userID, data, con)
            if recreateStatus != 0:
                data_ret = {'recreateContainerStatus': 0, 'error_message': str(recreateStatus)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            data_ret = {'recreateContainerStatus': 1, 'error_message': 'None'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except Exception as e:
            secure_log_error(e, 'recreateContainerStatus')
            data_ret = secure_error_response(e, 'Failed to recreateContainerStatus')
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def getTags(self, userID=None, data=None):
        try:

            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()

            image = data['image']
            page = data['page']

            if ":" in image:
                image2 = image.split(":")[0] + "/" + image.split(":")[1]
            else:
                image2 = "library/" + image

            print(image)
            registryData = requests.get('https://registry.hub.docker.com/v2/repositories/' + image2 + '/tags',
                                        {'page': page}).json()

            tagList = []
            for tag in registryData['results']:
                tagList.append(tag['name'])

            data_ret = {'getTagsStatus': 1, 'list': tagList, 'next': registryData['next'], 'error_message': None}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except Exception as e:
            secure_log_error(e, 'getTagsStatus')
            data_ret = secure_error_response(e, 'Failed to getTagsStatus')
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


    def getDockersiteList(self, userID=None, data=None):
        try:
            admin = Administrator.objects.get(pk=userID)

            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()


            name = data['name']

            passdata = {}
            passdata["JobID"] = None
            passdata['name'] = name
            da = Docker_Sites(None, passdata)
            retdata = da.ListContainers()

            data_ret = {'status': 1, 'error_message': 'None', 'data':retdata}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except Exception as e:
            secure_log_error(e, 'removeImageStatus')
            data_ret = secure_error_response(e, 'Failed to removeImageStatus')
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

            # Internal function for recreating containers

    def getContainerAppinfo(self, userID=None, data=None):
        try:
            admin = Administrator.objects.get(pk=userID)

            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()

            name = data['name']
            containerID = data['id']

            # Create a Docker client
            client = docker.from_env()
            container = client.containers.get(containerID)

            # Get detailed container info
            container_info = container.attrs

            # Calculate uptime
            started_at = container_info.get('State', {}).get('StartedAt', '')
            if started_at:
                started_time = datetime.strptime(started_at.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                uptime = datetime.now() - started_time
                uptime_str = str(uptime).split('.')[0]  # Format as HH:MM:SS
            else:
                uptime_str = "N/A"

            # Get container details
            details = {
                'id': container.short_id,
                'name': container.name,
                'status': container.status,
                'created': container_info.get('Created', ''),
                'started_at': started_at,
                'uptime': uptime_str,
                'image': container_info.get('Config', {}).get('Image', ''),
                'ports': container_info.get('NetworkSettings', {}).get('Ports', {}),
                'volumes': container_info.get('Mounts', []),
                'environment': self._mask_sensitive_env(container_info.get('Config', {}).get('Env', [])),
                'memory_usage': container.stats(stream=False)['memory_stats'].get('usage', 0),
                'cpu_usage': container.stats(stream=False)['cpu_stats']['cpu_usage'].get('total_usage', 0)
            }

            data_ret = {'status': 1, 'error_message': 'None', 'data': [1, details]}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except Exception as e:
            secure_log_error(e, 'getContainerAppinfo')
            data_ret = secure_error_response(e, 'Failed to get container app info')
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def _mask_sensitive_env(self, env_vars):
        """Helper method to mask sensitive data in environment variables"""
        masked_vars = []
        sensitive_keywords = ['password', 'secret', 'key', 'token', 'auth']
        
        for var in env_vars:
            if '=' in var:
                name, value = var.split('=', 1)
                # Check if this is a sensitive variable
                if any(keyword in name.lower() for keyword in sensitive_keywords):
                    masked_vars.append(f"{name}=********")
                else:
                    masked_vars.append(var)
            else:
                masked_vars.append(var)
        
        return masked_vars

    def getContainerApplog(self, userID=None, data=None):
        try:
            admin = Administrator.objects.get(pk=userID)

            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()


            name = data['name']
            containerID = data['id']

            passdata = {}
            passdata["JobID"] = None
            passdata['name'] = name
            passdata['containerID'] = containerID
            passdata['numberOfLines'] = 50
            da = Docker_Sites(None, passdata)
            retdata = da.ContainerLogs()


            data_ret = {'status': 1, 'error_message': 'None', 'data':retdata}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except Exception as e:
            secure_log_error(e, 'removeImageStatus')
            data_ret = secure_error_response(e, 'Failed to removeImageStatus')
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def recreateappcontainer(self, userID=None, data=None):
        try:
            from websiteFunctions.models import DockerSites
            admin = Administrator.objects.get(pk=userID)

            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()

            name = data['name']
            WPusername = data['WPusername']
            WPemail = data['WPemail']
            WPpasswd = data['WPpasswd']

            dockersite = DockerSites.objects.get(SiteName=name)

            passdata ={}
            data['JobID'] = ''
            data['Domain'] = dockersite.admin.domain
            data['domain'] = dockersite.admin.domain
            data['WPemail'] = WPemail
            data['Owner'] = dockersite.admin.admin.userName
            data['userID'] = userID
            data['MysqlCPU'] = dockersite.CPUsMySQL
            data['MYsqlRam'] = dockersite.MemoryMySQL
            data['SiteCPU'] = dockersite.CPUsSite
            data['SiteRam'] = dockersite.MemorySite
            data['sitename'] = dockersite.SiteName
            data['WPusername'] = WPusername
            data['WPpasswd'] = WPpasswd
            data['externalApp'] = dockersite.admin.externalApp

            da = Docker_Sites(None, passdata)
            da.RebuildApp()


            data_ret = {'status': 1, 'error_message': 'None',}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except Exception as e:
            secure_log_error(e, 'removeImageStatus')
            data_ret = secure_error_response(e, 'Failed to removeImageStatus')
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def RestartContainerAPP(self, userID=None, data=None):
        try:
            admin = Administrator.objects.get(pk=userID)

            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()

            name = data['name']
            containerID = data['id']

            passdata = {}
            passdata['containerID'] = containerID

            da = Docker_Sites(None, passdata)
            retdata = da.RestartContainer()


            data_ret = {'status': 1, 'error_message': 'None', 'data':retdata}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except Exception as e:
            secure_log_error(e, 'removeImageStatus')
            data_ret = secure_error_response(e, 'Failed to removeImageStatus')
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def StopContainerAPP(self, userID=None, data=None):
        try:
            admin = Administrator.objects.get(pk=userID)

            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()

            name = data['name']
            containerID = data['id']

            passdata = {}
            passdata['containerID'] = containerID

            da = Docker_Sites(None, passdata)
            retdata = da.StopContainer()


            data_ret = {'status': 1, 'error_message': 'None', 'data':retdata}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except Exception as e:
            secure_log_error(e, 'removeImageStatus')
            data_ret = secure_error_response(e, 'Failed to removeImageStatus')
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def executeContainerCommand(self, userID=None, data=None):
        """
        Execute a SAFE command inside a running Docker container with comprehensive security checks
        """
        try:
            # Input validation
            if not data or 'name' not in data or 'command' not in data:
                data_ret = {'commandStatus': 0, 'error_message': 'Missing required parameters: name and command'}
                return HttpResponse(json.dumps(data_ret))

            name = data['name']
            command = data['command'].strip()
            
            # Validate container name
            if not self._validate_container_name(name):
                data_ret = {'commandStatus': 0, 'error_message': 'Invalid container name'}
                return HttpResponse(json.dumps(data_ret))
            
            # Validate and sanitize command
            validation_result = self._validate_command(command)
            if not validation_result['valid']:
                data_ret = {'commandStatus': 0, 'error_message': validation_result['reason']}
                return HttpResponse(json.dumps(data_ret))
            
            # Check container ownership
            if Containers.objects.filter(name=name).exists():
                if ACLManager.checkContainerOwnership(name, userID) != 1:
                    return ACLManager.loadErrorJson('commandStatus', 0)

            # Rate limiting check
            if not self._check_rate_limit(userID, name):
                data_ret = {'commandStatus': 0, 'error_message': 'Rate limit exceeded. Please wait before executing more commands'}
                return HttpResponse(json.dumps(data_ret))

            client = docker.from_env()
            
            try:
                container = client.containers.get(name)
            except docker.errors.NotFound:
                data_ret = {'commandStatus': 0, 'error_message': 'Container does not exist'}
                return HttpResponse(json.dumps(data_ret))
            except Exception as err:
                data_ret = {'commandStatus': 0, 'error_message': f'Error accessing container: {str(err)}'}
                return HttpResponse(json.dumps(data_ret))

            # Handle container status - try to start if not running
            container_was_stopped = False
            if container.status != 'running':
                try:
                    # Try to start the container temporarily
                    container.start()
                    container_was_stopped = True
                    # Wait a moment for container to fully start
                    import time
                    time.sleep(2)
                    
                    # Verify container is now running
                    container.reload()
                    if container.status != 'running':
                        data_ret = {'commandStatus': 0, 'error_message': 'Failed to start container for command execution'}
                        return HttpResponse(json.dumps(data_ret))
                        
                except Exception as start_err:
                    data_ret = {'commandStatus': 0, 'error_message': f'Container is not running and cannot be started: {str(start_err)}'}
                    return HttpResponse(json.dumps(data_ret))

            # Log the command execution attempt
            self._log_command_execution(userID, name, command)

            try:
                # Parse command safely
                import shlex
                try:
                    command_parts = shlex.split(command)
                except ValueError as e:
                    data_ret = {'commandStatus': 0, 'error_message': f'Invalid command syntax: {str(e)}'}
                    return HttpResponse(json.dumps(data_ret))
                
                # Execute command with security restrictions
                # Note: Some commands may need privileged access, but we validate commands first
                exec_result = container.exec_run(
                    command_parts,
                    stdout=True,
                    stderr=True,
                    stdin=False,
                    tty=False,
                    privileged=True,   # Allow privileged mode since commands are whitelisted
                    user='',           # Use container's default user (often root, but commands are validated)
                    detach=False,
                    demux=False,
                    workdir=None,      # Use container's default working directory
                    environment=None   # Use container's default environment
                )
                
                # Get output and exit code
                output = exec_result.output.decode('utf-8', errors='replace') if exec_result.output else ''
                exit_code = exec_result.exit_code
                
                # Limit output size to prevent memory exhaustion
                if len(output) > 10000:  # 10KB limit
                    output = output[:10000] + "\n[Output truncated - exceeded 10KB limit]"
                
                # Log successful execution
                self._log_command_result(userID, name, command, exit_code, len(output))
                
                # Stop container if it was started temporarily
                if container_was_stopped:
                    try:
                        container.stop()
                        logging.CyberCPLogFileWriter.writeToFile(f'Stopped container {name} after command execution')
                    except Exception as stop_err:
                        logging.CyberCPLogFileWriter.writeToFile(f'Warning: Could not stop container {name} after command execution: {str(stop_err)}')
                
                # Format the response
                data_ret = {
                    'commandStatus': 1, 
                    'error_message': 'None' if exit_code == 0 else f'Command executed with exit code {exit_code}',
                    'output': output,
                    'exit_code': exit_code,
                    'command': command,
                    'timestamp': time.time(),
                    'container_was_started': container_was_stopped
                }
                
                return HttpResponse(json.dumps(data_ret, ensure_ascii=False))
                
            except docker.errors.APIError as err:
                # Stop container if it was started temporarily
                if container_was_stopped:
                    try:
                        container.stop()
                        logging.CyberCPLogFileWriter.writeToFile(f'Stopped container {name} after API error')
                    except Exception as stop_err:
                        logging.CyberCPLogFileWriter.writeToFile(f'Warning: Could not stop container {name} after API error: {str(stop_err)}')
                
                error_msg = f'Docker API error: {str(err)}'
                self._log_command_error(userID, name, command, error_msg)
                data_ret = {'commandStatus': 0, 'error_message': error_msg}
                return HttpResponse(json.dumps(data_ret))
            except Exception as err:
                # Stop container if it was started temporarily
                if container_was_stopped:
                    try:
                        container.stop()
                        logging.CyberCPLogFileWriter.writeToFile(f'Stopped container {name} after execution error')
                    except Exception as stop_err:
                        logging.CyberCPLogFileWriter.writeToFile(f'Warning: Could not stop container {name} after execution error: {str(stop_err)}')
                
                error_msg = f'Execution error: {str(err)}'
                self._log_command_error(userID, name, command, error_msg)
                data_ret = {'commandStatus': 0, 'error_message': error_msg}
                return HttpResponse(json.dumps(data_ret))

        except Exception as msg:
            error_msg = f'System error: {str(msg)}'
            logging.CyberCPLogFileWriter.writeToFile(f'executeContainerCommand error: {error_msg}')
            data_ret = {'commandStatus': 0, 'error_message': error_msg}
            return HttpResponse(json.dumps(data_ret))

    # Security helper methods for executeContainerCommand
    def _validate_container_name(self, name):
        """Validate container name to prevent injection"""
        if not name or len(name) > 100:
            return False
        # Allow only alphanumeric, hyphens, underscores, and dots
        import re
        return re.match(r'^[a-zA-Z0-9._-]+$', name) is not None

    def _validate_command(self, command):
        """Comprehensive command validation with whitelist approach"""
        if not command or len(command) > 1000:  # Reasonable command length limit
            return {'valid': False, 'reason': 'Command is empty or too long (max 1000 characters)'}
        
        # Define allowed commands (whitelist approach)
        ALLOWED_COMMANDS = {
            # System information
            'whoami', 'id', 'pwd', 'date', 'uptime', 'hostname', 'uname', 'df', 'free', 'lscpu',
            # File operations (safe and necessary)
            'ls', 'cat', 'head', 'tail', 'wc', 'find', 'file', 'stat', 'du', 'tree',
            'mkdir', 'touch', 'ln', 'readlink',
            # Process monitoring
            'ps', 'top', 'htop', 'jobs', 'pgrep', 'pkill', 'killall', 'kill',
            # Network tools
            'ping', 'wget', 'curl', 'nslookup', 'dig', 'netstat', 'ss', 'ifconfig', 'ip',
            # Text processing
            'grep', 'awk', 'sed', 'sort', 'uniq', 'cut', 'tr', 'wc', 'diff',
            # Package management
            'dpkg', 'rpm', 'yum', 'apt', 'apt-get', 'apt-cache', 'aptitude',
            'pip', 'pip3', 'npm', 'composer', 'gem',
            # Environment and system
            'env', 'printenv', 'which', 'type', 'locale', 'timedatectl',
            # Archives and compression
            'tar', 'gzip', 'gunzip', 'zip', 'unzip',
            # Editors (safe ones)
            'nano', 'vi', 'vim',
            # Database clients
            'mysql', 'psql', 'sqlite3', 'redis-cli', 'mongo',
            # Development tools
            'git', 'node', 'python', 'python3', 'php', 'ruby', 'perl', 'java',
            # System services (read-only operations)
            'systemctl', 'service', 'journalctl',
            # Safe utilities
            'echo', 'printf', 'test', 'expr', 'basename', 'dirname', 'realpath',
            'sleep', 'timeout', 'watch', 'yes', 'seq',
            # Log viewing
            'dmesg', 'last', 'lastlog', 'w', 'who'
        }
        
        # Dangerous commands/patterns (blacklist - these override the whitelist)
        DANGEROUS_PATTERNS = [
            # Command injection patterns
            ';', '&&', '||', '`', '$(',
            # Path traversal
            '../', '~/', 
            # Destructive file operations
            'rm -rf', 'rm -r', 'dd if=', 'dd of=', '>>', 'mkfs', 'fdisk',
            # System modification
            'mount', 'umount', 'crontab -e', 'crontab -r',
            # Package installation/removal (allow read-only package commands)
            'apt install', 'apt remove', 'apt purge', 'apt-get install', 
            'apt-get remove', 'apt-get purge', 'yum install', 'yum remove',
            'pip install', 'pip uninstall', 'npm install -g', 'gem install',
            # Dangerous network utilities
            'nc ', 'netcat', 'ncat', 'telnet', 'ssh ', 'scp ', 'rsync',
            # Shell escapes and dangerous execution
            'bash', 'sh ', '/bin/sh', '/bin/bash', 'sudo', 'su ', 'exec',
            'chroot', 'docker ', 'systemctl start', 'systemctl stop', 
            'systemctl enable', 'systemctl disable', 'service start',
            'service stop', 'service restart'
        ]
        
        command_lower = command.lower()
        
        # Check for dangerous patterns
        for pattern in DANGEROUS_PATTERNS:
            if pattern in command_lower:
                return {'valid': False, 'reason': f'Command contains dangerous pattern: {pattern}'}
        
        # Extract base command
        first_word = command.strip().split()[0] if command.strip() else ''
        base_command = first_word.split('/')[-1]  # Remove path if present
        
        # Check if base command is in whitelist
        if base_command not in ALLOWED_COMMANDS:
            return {'valid': False, 'reason': f'Command "{base_command}" is not in the allowed list'}
        
        # Additional checks for specific commands
        if base_command in ['find']:
            # Ensure no -exec or dangerous flags
            if '-exec' in command_lower or '-delete' in command_lower:
                return {'valid': False, 'reason': 'Dangerous flags (-exec, -delete) not allowed with find'}
        
        if base_command in ['systemctl', 'service']:
            # Only allow read-only operations
            readonly_ops = ['status', 'show', 'list-units', 'list-unit-files', 'is-active', 'is-enabled']
            if not any(op in command_lower for op in readonly_ops):
                return {'valid': False, 'reason': 'Only read-only operations allowed for systemctl/service'}
        
        if base_command in ['kill', 'pkill', 'killall']:
            # Ensure no dangerous signals
            if '-9' in command or 'SIGKILL' in command.upper():
                return {'valid': False, 'reason': 'SIGKILL (-9) not allowed for safety'}
        
        if base_command in ['wget', 'curl']:
            # Ensure no output redirection to critical system locations
            critical_paths = ['/etc/', '/boot/', '/usr/bin/', '/bin/', '/sbin/', '/usr/sbin/']
            if any(path in command_lower for path in critical_paths):
                return {'valid': False, 'reason': 'Cannot download to critical system directories'}
        
        return {'valid': True, 'reason': 'Command passed validation'}

    def _check_rate_limit(self, userID, containerName):
        """Enhanced rate limiting: max 10 commands per minute per user-container pair"""
        import time
        import os
        import json
        
        # Create rate limit tracking directory
        rate_limit_dir = '/tmp/cyberpanel_docker_rate_limit'
        if not os.path.exists(rate_limit_dir):
            try:
                os.makedirs(rate_limit_dir, mode=0o755)
            except Exception as e:
                # If we can't create rate limit tracking, allow the command but log it
                logging.CyberCPLogFileWriter.writeToFile(f'Warning: Could not create rate limit directory: {str(e)}')
                return True
        
        # Rate limit file per user-container
        rate_file = os.path.join(rate_limit_dir, f'user_{userID}_container_{containerName}')
        current_time = time.time()
        
        try:
            # Read existing timestamps
            timestamps = []
            if os.path.exists(rate_file):
                with open(rate_file, 'r') as f:
                    try:
                        data = json.load(f)
                        timestamps = data.get('timestamps', [])
                    except (json.JSONDecodeError, KeyError):
                        # Fallback to old format
                        f.seek(0)
                        timestamps = [float(line.strip()) for line in f if line.strip()]
            
            # Remove timestamps older than 1 minute
            recent_timestamps = [ts for ts in timestamps if current_time - ts < 60]
            
            # Check if limit exceeded
            if len(recent_timestamps) >= 10:
                logging.CyberCPLogFileWriter.writeToFile(f'Rate limit exceeded for user {userID}, container {containerName}')
                return False
            
            # Add current timestamp
            recent_timestamps.append(current_time)
            
            # Write back to file with JSON format
            with open(rate_file, 'w') as f:
                json.dump({
                    'timestamps': recent_timestamps,
                    'last_updated': current_time,
                    'user_id': userID,
                    'container_name': containerName
                }, f)
            
            return True
            
        except Exception as e:
            # If rate limiting fails, log but allow the command
            logging.CyberCPLogFileWriter.writeToFile(f'Rate limiting error: {str(e)}')
            return True

    def _log_command_execution(self, userID, containerName, command):
        """Log command execution attempts for security monitoring"""
        try:
            from loginSystem.models import Administrator
            admin = Administrator.objects.get(pk=userID)
            username = admin.userName
        except:
            username = f'UserID_{userID}'
        
        log_message = f'DOCKER_COMMAND_EXEC: User={username} Container={containerName} Command="{command}" Time={time.time()}'
        logging.CyberCPLogFileWriter.writeToFile(log_message)

    def _log_command_result(self, userID, containerName, command, exitCode, outputLength):
        """Log command execution results"""
        try:
            from loginSystem.models import Administrator
            admin = Administrator.objects.get(pk=userID)
            username = admin.userName
        except:
            username = f'UserID_{userID}'
        
        log_message = f'DOCKER_COMMAND_RESULT: User={username} Container={containerName} ExitCode={exitCode} OutputLength={outputLength} Time={time.time()}'
        logging.CyberCPLogFileWriter.writeToFile(log_message)

    def _log_command_error(self, userID, containerName, command, errorMsg):
        """Log command execution errors"""
        try:
            from loginSystem.models import Administrator
            admin = Administrator.objects.get(pk=userID)
            username = admin.userName
        except:
            username = f'UserID_{userID}'
        
        log_message = f'DOCKER_COMMAND_ERROR: User={username} Container={containerName} Error="{errorMsg}" Command="{command[:100]}" Time={time.time()}'
        logging.CyberCPLogFileWriter.writeToFile(log_message)

    def updateContainer(self, userID=None, data=None):
        """
        Update container with new image while preserving data using Docker volumes
        """
        try:
            name = data['name']
            newImage = data.get('newImage', '')
            newTag = data.get('newTag', 'latest')
            
            if ACLManager.checkContainerOwnership(name, userID) != 1:
                return ACLManager.loadErrorJson('updateContainerStatus', 0)

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            try:
                container = client.containers.get(name)
            except docker.errors.NotFound:
                data_ret = {'updateContainerStatus': 0, 'error_message': 'Container does not exist'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            # Get current container configuration
            container_attrs = container.attrs
            current_image = container_attrs['Config']['Image']
            
            # If no new image specified, use current image with latest tag
            if not newImage:
                if ':' in current_image:
                    newImage = current_image.split(':')[0]
                else:
                    newImage = current_image
                    newTag = 'latest'
            
            full_new_image = f"{newImage}:{newTag}"
            
            # Check if image exists locally, if not pull it
            try:
                client.images.get(full_new_image)
            except docker.errors.ImageNotFound:
                try:
                    logging.CyberCPLogFileWriter.writeToFile(f'Pulling new image: {full_new_image}')
                    client.images.pull(newImage, tag=newTag)
                except Exception as e:
                    data_ret = {'updateContainerStatus': 0, 'error_message': f'Failed to pull image {full_new_image}: {str(e)}'}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

            # Get current container configuration for recreation
            container_config = container_attrs['Config']
            container_host_config = container_attrs['HostConfig']
            
            # Extract volumes from current container
            volumes = {}
            if 'Mounts' in container_attrs:
                for mount in container_attrs['Mounts']:
                    if mount['Type'] == 'volume':
                        volumes[mount['Destination']] = mount['Name']
                    elif mount['Type'] == 'bind':
                        volumes[mount['Destination']] = mount['Source']
            
            # Extract environment variables
            env_vars = container_config.get('Env', [])
            env_dict = {}
            for env_var in env_vars:
                if '=' in env_var:
                    key, value = env_var.split('=', 1)
                    env_dict[key] = value
            
            # Extract ports
            port_bindings = {}
            if 'PortBindings' in container_host_config and container_host_config['PortBindings']:
                for container_port, host_bindings in container_host_config['PortBindings'].items():
                    if host_bindings:
                        port_bindings[container_port] = host_bindings[0]['HostPort']
            
            # Stop current container
            if container.status == 'running':
                container.stop()
                time.sleep(2)
            
            # Create new container with same configuration but new image
            new_container_name = f"{name}_updated_{int(time.time())}"
            
            # Create volume mounts
            volume_mounts = []
            for dest, src in volumes.items():
                volume_mounts.append(f"{src}:{dest}")
            
            # Create new container
            new_container = client.containers.create(
                image=full_new_image,
                name=new_container_name,
                environment=env_dict,
                volumes=volume_mounts,
                ports=port_bindings,
                detach=True,
                restart_policy=container_host_config.get('RestartPolicy', {'Name': 'no'})
            )
            
            # Start new container
            new_container.start()
            
            # Wait a moment for container to start
            time.sleep(3)
            
            # Check if new container is running
            new_container.reload()
            if new_container.status == 'running':
                # Remove old container
                container.remove()
                
                # Rename new container to original name
                new_container.rename(name)
                
                # Update database record
                try:
                    container_record = Containers.objects.get(name=name)
                    container_record.image = newImage
                    container_record.tag = newTag
                    container_record.cid = new_container.short_id
                    container_record.save()
                except Containers.DoesNotExist:
                    pass
                
                data_ret = {'updateContainerStatus': 1, 'error_message': 'Container updated successfully', 'new_image': full_new_image}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                # New container failed to start, remove it and restore old one
                new_container.remove()
                container.start()
                data_ret = {'updateContainerStatus': 0, 'error_message': 'New container failed to start, old container restored'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except Exception as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + ' [ContainerManager.updateContainer]')
            data_ret = {'updateContainerStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def deleteContainerWithData(self, userID=None, data=None):
        """
        Delete container and all associated data (volumes)
        """
        try:
            name = data['name']
            
            if ACLManager.checkContainerOwnership(name, userID) != 1:
                return ACLManager.loadErrorJson('deleteContainerWithDataStatus', 0)

            client = docker.from_env()

            try:
                container = client.containers.get(name)
            except docker.errors.NotFound:
                data_ret = {'deleteContainerWithDataStatus': 0, 'error_message': 'Container does not exist'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            # Get container volumes before deletion
            container_attrs = container.attrs
            volumes_to_remove = []
            
            if 'Mounts' in container_attrs:
                for mount in container_attrs['Mounts']:
                    if mount['Type'] == 'volume':
                        volumes_to_remove.append(mount['Name'])

            # Stop and remove container
            if container.status == 'running':
                container.stop()
                time.sleep(2)
            
            container.remove(force=True)
            
            # Remove associated volumes
            for volume_name in volumes_to_remove:
                try:
                    volume = client.volumes.get(volume_name)
                    volume.remove()
                    logging.CyberCPLogFileWriter.writeToFile(f'Removed volume: {volume_name}')
                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile(f'Failed to remove volume {volume_name}: {str(e)}')

            # Remove from database
            try:
                container_record = Containers.objects.get(name=name)
                container_record.delete()
            except Containers.DoesNotExist:
                pass

            data_ret = {'deleteContainerWithDataStatus': 1, 'error_message': 'Container and data deleted successfully'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except Exception as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + ' [ContainerManager.deleteContainerWithData]')
            data_ret = {'deleteContainerWithDataStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def deleteContainerKeepData(self, userID=None, data=None):
        """
        Delete container but preserve data (volumes)
        """
        try:
            name = data['name']
            
            if ACLManager.checkContainerOwnership(name, userID) != 1:
                return ACLManager.loadErrorJson('deleteContainerKeepDataStatus', 0)

            client = docker.from_env()

            try:
                container = client.containers.get(name)
            except docker.errors.NotFound:
                data_ret = {'deleteContainerKeepDataStatus': 0, 'error_message': 'Container does not exist'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            # Get container volumes before deletion
            container_attrs = container.attrs
            preserved_volumes = []
            
            if 'Mounts' in container_attrs:
                for mount in container_attrs['Mounts']:
                    if mount['Type'] == 'volume':
                        preserved_volumes.append(mount['Name'])
                    elif mount['Type'] == 'bind':
                        preserved_volumes.append(f"Bind mount: {mount['Source']} -> {mount['Destination']}")

            # Stop and remove container
            if container.status == 'running':
                container.stop()
                time.sleep(2)
            
            container.remove(force=True)

            # Remove from database
            try:
                container_record = Containers.objects.get(name=name)
                container_record.delete()
            except Containers.DoesNotExist:
                pass

            data_ret = {
                'deleteContainerKeepDataStatus': 1, 
                'error_message': 'Container deleted successfully, data preserved',
                'preserved_volumes': preserved_volumes
            }
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except Exception as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + ' [ContainerManager.deleteContainerKeepData]')
            data_ret = {'deleteContainerKeepDataStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def updateContainer(self, userID=None, data=None):
        """
        Update container with new image while preserving data using Docker volumes
        This function handles the complete container update process:
        1. Stops the current container
        2. Creates a backup of the container configuration
        3. Removes the old container
        4. Pulls the new image
        5. Creates a new container with the same configuration but new image
        6. Preserves all volumes and data
        """
        try:
            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()

            client = docker.from_env()
            dockerAPI = docker.APIClient()
            
            containerName = data['containerName']
            newImage = data['newImage']
            newTag = data.get('newTag', 'latest')
            
            # Get the current container
            try:
                currentContainer = client.containers.get(containerName)
            except docker.errors.NotFound:
                data_ret = {'updateContainerStatus': 0, 'error_message': f'Container {containerName} not found'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except Exception as e:
                data_ret = {'updateContainerStatus': 0, 'error_message': f'Error accessing container: {str(e)}'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            # Get container configuration for recreation
            containerConfig = currentContainer.attrs['Config']
            hostConfig = currentContainer.attrs['HostConfig']
            
            # Extract volumes for data preservation
            volumes = {}
            if 'Binds' in hostConfig and hostConfig['Binds']:
                for bind in hostConfig['Binds']:
                    if ':' in bind:
                        parts = bind.split(':')
                        if len(parts) >= 2:
                            host_path = parts[0]
                            container_path = parts[1]
                            mode = parts[2] if len(parts) > 2 else 'rw'
                            volumes[host_path] = {'bind': container_path, 'mode': mode}

            # Extract environment variables
            environment = containerConfig.get('Env', [])
            envDict = {}
            for env in environment:
                if '=' in env:
                    key, value = env.split('=', 1)
                    envDict[key] = value

            # Extract port mappings
            portConfig = {}
            if 'PortBindings' in hostConfig and hostConfig['PortBindings']:
                for container_port, host_bindings in hostConfig['PortBindings'].items():
                    if host_bindings and len(host_bindings) > 0:
                        host_port = host_bindings[0]['HostPort']
                        portConfig[container_port] = host_port

            # Extract memory limit
            memory_limit = hostConfig.get('Memory', 0)
            if memory_limit > 0:
                memory_limit = memory_limit // 1048576  # Convert bytes to MB

            # Stop the current container
            try:
                if currentContainer.status == 'running':
                    currentContainer.stop(timeout=30)
                    logging.CyberCPLogFileWriter.writeToFile(f'Stopped container {containerName} for update')
            except Exception as e:
                logging.CyberCPLogFileWriter.writeToFile(f'Error stopping container {containerName}: {str(e)}')
                data_ret = {'updateContainerStatus': 0, 'error_message': f'Error stopping container: {str(e)}'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            # Remove the old container
            try:
                currentContainer.remove(force=True)
                logging.CyberCPLogFileWriter.writeToFile(f'Removed old container {containerName}')
            except Exception as e:
                logging.CyberCPLogFileWriter.writeToFile(f'Error removing old container {containerName}: {str(e)}')
                data_ret = {'updateContainerStatus': 0, 'error_message': f'Error removing old container: {str(e)}'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            # Pull the new image
            try:
                image_name = f"{newImage}:{newTag}"
                logging.CyberCPLogFileWriter.writeToFile(f'Pulling new image {image_name}')
                client.images.pull(newImage, tag=newTag)
                logging.CyberCPLogFileWriter.writeToFile(f'Successfully pulled image {image_name}')
            except Exception as e:
                logging.CyberCPLogFileWriter.writeToFile(f'Error pulling image {newImage}:{newTag}: {str(e)}')
                data_ret = {'updateContainerStatus': 0, 'error_message': f'Error pulling new image: {str(e)}'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            # Create new container with same configuration but new image
            try:
                containerArgs = {
                    'image': image_name,
                    'detach': True,
                    'name': containerName,
                    'ports': portConfig,
                    'publish_all_ports': True,
                    'environment': envDict,
                    'volumes': volumes
                }
                
                if memory_limit > 0:
                    containerArgs['mem_limit'] = memory_limit * 1048576

                newContainer = client.containers.create(**containerArgs)
                logging.CyberCPLogFileWriter.writeToFile(f'Created new container {containerName} with image {image_name}')
                
                # Start the new container
                newContainer.start()
                logging.CyberCPLogFileWriter.writeToFile(f'Started updated container {containerName}')
                
            except docker.errors.APIError as err:
                error_message = str(err)
                if "port is already allocated" in error_message:
                    try:
                        newContainer.remove(force=True)
                    except:
                        pass
                data_ret = {'updateContainerStatus': 0, 'error_message': f'Docker API error creating container: {error_message}'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except docker.errors.ImageNotFound as err:
                error_message = str(err)
                data_ret = {'updateContainerStatus': 0, 'error_message': f'New image not found: {error_message}'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except Exception as e:
                logging.CyberCPLogFileWriter.writeToFile(f'Error creating new container {containerName}: {str(e)}')
                data_ret = {'updateContainerStatus': 0, 'error_message': f'Error creating new container: {str(e)}'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            # Log successful update
            logging.CyberCPLogFileWriter.writeToFile(f'Successfully updated container {containerName} to image {image_name}')
            
            data_ret = {
                'updateContainerStatus': 1, 
                'error_message': 'None',
                'message': f'Container {containerName} successfully updated to {image_name}'
            }
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except Exception as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + ' [ContainerManager.updateContainer]')
            data_ret = {'updateContainerStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def listContainersJson(self, userID=None):
        """
        Get list of all Docker containers as JSON (for Angular API).
        """
        try:
            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()

            client = docker.from_env()
            
            # Get all containers (including stopped ones)
            containers = client.containers.list(all=True)
            
            container_list = []
            for container in containers:
                container_info = {
                    'name': container.name,
                    'image': container.image.tags[0] if container.image.tags else container.image.short_id,
                    'status': container.status,
                    'state': container.attrs['State']['Status'],
                    'created': container.attrs['Created'],
                    'ports': container.attrs['NetworkSettings']['Ports'],
                    'mounts': container.attrs['Mounts'],
                    'id': container.short_id
                }
                container_list.append(container_info)
            
            data_ret = {
                'status': 1,
                'error_message': 'None',
                'containers': container_list
            }
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data, content_type='application/json')

        except Exception as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + ' [ContainerManager.listContainersJson]')
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data, content_type='application/json')

    def getDockerNetworks(self, userID=None):
        """
        Get list of all Docker networks
        """
        try:
            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()

            client = docker.from_env()
            
            # Get all networks
            networks = client.networks.list()
            
            network_list = []
            for network in networks:
                network_info = {
                    'id': network.id,
                    'name': network.name,
                    'driver': network.attrs.get('Driver', 'unknown'),
                    'scope': network.attrs.get('Scope', 'local'),
                    'created': network.attrs.get('Created', ''),
                    'containers': len(network.attrs.get('Containers', {})),
                    'ipam': network.attrs.get('IPAM', {}),
                    'labels': network.attrs.get('Labels', {})
                }
                network_list.append(network_info)
            
            data_ret = {
                'status': 1,
                'error_message': 'None',
                'networks': network_list
            }
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except Exception as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + ' [ContainerManager.getDockerNetworks]')
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def createDockerNetwork(self, userID=None, data=None):
        """
        Create a new Docker network
        """
        try:
            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()

            client = docker.from_env()
            
            name = data.get('name')
            driver = data.get('driver', 'bridge')
            subnet = data.get('subnet', '')
            gateway = data.get('gateway', '')
            ip_range = data.get('ip_range', '')
            
            if not name:
                data_ret = {'status': 0, 'error_message': 'Network name is required'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            
            # Prepare IPAM configuration
            ipam_config = []
            if subnet:
                ipam_entry = {'subnet': subnet}
                if gateway:
                    ipam_entry['gateway'] = gateway
                if ip_range:
                    ipam_entry['ip_range'] = ip_range
                ipam_config.append(ipam_entry)
            
            ipam = {'driver': 'default', 'config': ipam_config} if ipam_config else None
            
            # Create the network
            network = client.networks.create(
                name=name,
                driver=driver,
                ipam=ipam
            )
            
            data_ret = {
                'status': 1,
                'error_message': 'None',
                'network_id': network.id,
                'message': f'Network {name} created successfully'
            }
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except Exception as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + ' [ContainerManager.createDockerNetwork]')
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def updateContainerPorts(self, userID=None, data=None):
        """
        Update port mappings for an existing container
        """
        try:
            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()

            client = docker.from_env()
            
            container_name = data.get('name')
            new_ports = data.get('ports', {})
            
            if not container_name:
                data_ret = {'status': 0, 'error_message': 'Container name is required'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            
            # Get the container
            try:
                container = client.containers.get(container_name)
            except docker.errors.NotFound:
                data_ret = {'status': 0, 'error_message': f'Container {container_name} not found'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            
            # Check if container is running
            if container.status != 'running':
                data_ret = {'status': 0, 'error_message': 'Container must be running to update port mappings'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            
            # Get current container configuration
            container_config = container.attrs['Config']
            host_config = container.attrs['HostConfig']
            
            # Update port bindings
            port_bindings = {}
            for container_port, host_port in new_ports.items():
                if host_port:  # Only add if host port is specified
                    port_bindings[container_port] = host_port
            
            # Stop the container
            container.stop(timeout=10)
            
            # Create new container with updated port configuration
            new_container = client.containers.create(
                image=container_config['Image'],
                name=f"{container_name}_temp",
                ports=list(new_ports.keys()),
                host_config=client.api.create_host_config(port_bindings=port_bindings),
                environment=container_config.get('Env', []),
                volumes=host_config.get('Binds', []),
                detach=True
            )
            
            # Remove old container and rename new one
            container.remove()
            new_container.rename(container_name)
            
            # Start the updated container
            new_container.start()
            
            # Update database record if it exists
            try:
                db_container = Containers.objects.get(name=container_name)
                db_container.ports = json.dumps(new_ports)
                db_container.save()
            except Containers.DoesNotExist:
                pass  # Container not in database, that's okay
            
            data_ret = {
                'status': 1,
                'error_message': 'None',
                'message': f'Port mappings updated for container {container_name}'
            }
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except Exception as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + ' [ContainerManager.updateContainerPorts]')
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)