import json
import docker
from django.http import HttpResponse
from .models import DockerSites
from loginSystem.models import Administrator
from plogical.acl import ACLManager
from django.shortcuts import redirect
from loginSystem.views import loadLoginPage
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from plogical.DockerSites import COMPOSE_PROJECT_LABEL, compose_project_names

def require_login(view_func):
    def wrapper(request, *args, **kwargs):
        try:
            userID = request.session['userID']
            return view_func(request, *args, **kwargs)
        except KeyError:
            return redirect(loadLoginPage)
    return wrapper

class DockerManager:
    def __init__(self):
        self.client = docker.from_env()

    def get_container(self, container_id):
        try:
            return self.client.containers.get(container_id)
        except docker.errors.NotFound:
            return None
        except Exception as e:
            logging.writeToFile(f"Error getting container {container_id}: {str(e)}")
            return None

def refusal(message):
    return HttpResponse(json.dumps({'status': 0, 'error_message': message}))


def container_of_owned_site(request):
    """
    Return (container, None) for the container the request names when it belongs
    to a Docker site of the signed-in user, else (None, the refusal to send).

    The request names a Docker site and a container. The user must own the
    website the site is installed on, and the container must carry the label of
    that site's Docker Compose project: a container of another site, or one the
    administrator started, is not found.
    """
    userID = request.session['userID']
    currentACL = ACLManager.loadedACL(userID)
    admin = Administrator.objects.get(pk=userID)

    data = json.loads(request.body)
    container_id = data.get('container_id')
    site_name = data.get('name')

    if not isinstance(site_name, str) or not isinstance(container_id, str) or not container_id.strip():
        return None, refusal('Docker site not found')

    try:
        docker_site = DockerSites.objects.get(SiteName=site_name)
    except DockerSites.DoesNotExist:
        return None, refusal('Docker site not found')

    if ACLManager.checkOwnership(docker_site.admin.domain, admin, currentACL) != 1:
        return None, refusal('Not authorized to access this container')

    container = DockerManager().get_container(container_id.strip())

    if container is None:
        return None, refusal('Container not found')

    project = (container.labels or {}).get(COMPOSE_PROJECT_LABEL)

    if not project or project not in compose_project_names(docker_site.SiteName):
        return None, refusal('Container not found')

    return container, None


def container_action(request, action):
    try:
        if request.method != 'POST':
            return HttpResponse('Not allowed')

        container, refused = container_of_owned_site(request)

        if refused is not None:
            return refused

        getattr(container, action)()
        return HttpResponse(json.dumps({'status': 1}))
    except Exception as e:
        return refusal(str(e))


@require_login
def startContainer(request):
    return container_action(request, 'start')


@require_login
def stopContainer(request):
    return container_action(request, 'stop')


@require_login
def restartContainer(request):
    return container_action(request, 'restart')
