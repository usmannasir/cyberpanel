# Mindset Laravel Manager - Views
# Copyright (C) 2024 Mindset Contributors
# Licensed under GPLv3

import json
import subprocess
from pathlib import Path
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, Http404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.core.paginator import Paginator

from websiteFunctions.models import Websites
from .models import LaravelSite, Deployment, QueueWorker, ScheduledTask, EnvironmentVariable


@login_required
def dashboard(request):
    """Laravel Manager Dashboard - List all Laravel sites"""
    # Get all Laravel sites for the current user
    if request.user.is_superuser:
        laravel_sites = LaravelSite.objects.select_related('website').all()
    else:
        laravel_sites = LaravelSite.objects.select_related('website').filter(
            website__admin=request.user
        )

    # Get recent deployments
    recent_deployments = Deployment.objects.select_related(
        'laravel_site__website'
    ).order_by('-started_at')[:10]

    context = {
        'laravel_sites': laravel_sites,
        'recent_deployments': recent_deployments,
        'total_sites': laravel_sites.count(),
        'active_deployments': Deployment.objects.filter(status='running').count(),
    }

    return render(request, 'laravelManager/dashboard.html', context)


@login_required
def create_laravel_site(request):
    """Create a new Laravel site"""
    if request.method == 'POST':
        try:
            website_id = request.POST.get('website_id')
            website = get_object_or_404(Websites, pk=website_id)

            # Check if Laravel config already exists
            if hasattr(website, 'laravel_config'):
                messages.error(request, 'This site is already configured as a Laravel site.')
                return redirect('laravelManager:dashboard')

            # Create Laravel configuration
            laravel_site = LaravelSite.objects.create(
                website=website,
                laravel_version=request.POST.get('laravel_version', '12.x'),
                php_version=request.POST.get('php_version', '8.3'),
                deployment_strategy=request.POST.get('deployment_strategy', 'zero-downtime'),
                git_repository=request.POST.get('git_repository', ''),
                git_branch=request.POST.get('git_branch', 'main'),
                horizon_enabled=request.POST.get('horizon_enabled') == 'on',
                scheduler_enabled=request.POST.get('scheduler_enabled') == 'on',
            )

            # Initialize Laravel directory structure
            _initialize_laravel_structure(laravel_site)

            messages.success(request, f'Laravel site {website.domain} created successfully!')
            return redirect('laravelManager:site_detail', site_id=laravel_site.id)

        except Exception as e:
            messages.error(request, f'Error creating Laravel site: {str(e)}')
            return redirect('laravelManager:dashboard')

    # GET request - show form
    # Get websites that don't have Laravel config yet
    if request.user.is_superuser:
        available_websites = Websites.objects.filter(laravel_config__isnull=True)
    else:
        available_websites = Websites.objects.filter(
            admin=request.user,
            laravel_config__isnull=True
        )

    context = {
        'available_websites': available_websites,
        'php_versions': LaravelSite.PHP_VERSIONS,
        'deployment_strategies': LaravelSite.DEPLOYMENT_STRATEGIES,
    }

    return render(request, 'laravelManager/create.html', context)


@login_required
def site_detail(request, site_id):
    """Laravel site detail view"""
    laravel_site = get_object_or_404(LaravelSite, pk=site_id)

    # Get recent deployments
    deployments = laravel_site.deployments.order_by('-started_at')[:5]

    # Get queue workers
    workers = laravel_site.queue_workers.all()

    # Get site metrics
    metrics = _get_site_metrics(laravel_site)

    context = {
        'site': laravel_site,
        'deployments': deployments,
        'workers': workers,
        'metrics': metrics,
    }

    return render(request, 'laravelManager/site_detail.html', context)


@login_required
def site_settings(request, site_id):
    """Update Laravel site settings"""
    laravel_site = get_object_or_404(LaravelSite, pk=site_id)

    if request.method == 'POST':
        try:
            laravel_site.php_version = request.POST.get('php_version', laravel_site.php_version)
            laravel_site.deployment_strategy = request.POST.get('deployment_strategy', laravel_site.deployment_strategy)
            laravel_site.git_repository = request.POST.get('git_repository', '')
            laravel_site.git_branch = request.POST.get('git_branch', 'main')
            laravel_site.keep_releases = int(request.POST.get('keep_releases', 5))
            laravel_site.auto_migrate = request.POST.get('auto_migrate') == 'on'
            laravel_site.auto_npm_build = request.POST.get('auto_npm_build') == 'on'
            laravel_site.horizon_enabled = request.POST.get('horizon_enabled') == 'on'
            laravel_site.scheduler_enabled = request.POST.get('scheduler_enabled') == 'on'
            laravel_site.save()

            messages.success(request, 'Settings updated successfully!')
        except Exception as e:
            messages.error(request, f'Error updating settings: {str(e)}')

        return redirect('laravelManager:site_detail', site_id=site_id)

    context = {
        'site': laravel_site,
        'php_versions': LaravelSite.PHP_VERSIONS,
        'deployment_strategies': LaravelSite.DEPLOYMENT_STRATEGIES,
    }

    return render(request, 'laravelManager/settings.html', context)


@login_required
@require_http_methods(['POST'])
def deploy(request, site_id):
    """Trigger a deployment"""
    laravel_site = get_object_or_404(LaravelSite, pk=site_id)

    try:
        # Create deployment record
        release_id = datetime.now().strftime('%Y%m%d%H%M%S')
        deployment = Deployment.objects.create(
            laravel_site=laravel_site,
            release_id=release_id,
            git_branch=request.POST.get('branch', laravel_site.git_branch),
            status='pending',
            triggered_by='manual',
            triggered_by_user=request.user.username,
        )

        # Start deployment in background
        # In production, this would use Celery or similar
        _run_deployment(deployment)

        messages.success(request, f'Deployment {release_id} started!')
        return redirect('laravelManager:deployment_detail', site_id=site_id, deploy_id=deployment.id)

    except Exception as e:
        messages.error(request, f'Error starting deployment: {str(e)}')
        return redirect('laravelManager:site_detail', site_id=site_id)


@login_required
def deployment_list(request, site_id):
    """List all deployments for a site"""
    laravel_site = get_object_or_404(LaravelSite, pk=site_id)
    deployments = laravel_site.deployments.order_by('-started_at')

    paginator = Paginator(deployments, 20)
    page = request.GET.get('page', 1)
    deployments_page = paginator.get_page(page)

    context = {
        'site': laravel_site,
        'deployments': deployments_page,
    }

    return render(request, 'laravelManager/deployments.html', context)


@login_required
def deployment_detail(request, site_id, deploy_id):
    """View deployment details"""
    laravel_site = get_object_or_404(LaravelSite, pk=site_id)
    deployment = get_object_or_404(Deployment, pk=deploy_id, laravel_site=laravel_site)

    context = {
        'site': laravel_site,
        'deployment': deployment,
    }

    return render(request, 'laravelManager/deployment_detail.html', context)


@login_required
@require_http_methods(['POST'])
def rollback(request, site_id):
    """Rollback to a previous release"""
    laravel_site = get_object_or_404(LaravelSite, pk=site_id)

    try:
        releases_back = int(request.POST.get('releases_back', 1))

        # Get successful deployments
        deployments = laravel_site.deployments.filter(
            status='success'
        ).order_by('-started_at')

        if deployments.count() <= releases_back:
            messages.error(request, 'Not enough releases to rollback')
            return redirect('laravelManager:site_detail', site_id=site_id)

        target_deployment = deployments[releases_back]

        # Perform rollback
        _perform_rollback(laravel_site, target_deployment)

        messages.success(request, f'Rolled back to release {target_deployment.release_id}')

    except Exception as e:
        messages.error(request, f'Rollback failed: {str(e)}')

    return redirect('laravelManager:site_detail', site_id=site_id)


@login_required
def artisan(request, site_id):
    """Artisan command interface"""
    laravel_site = get_object_or_404(LaravelSite, pk=site_id)

    # Get list of common artisan commands
    common_commands = [
        {'name': 'cache:clear', 'description': 'Flush the application cache'},
        {'name': 'config:cache', 'description': 'Create a cache file for faster configuration loading'},
        {'name': 'config:clear', 'description': 'Remove the configuration cache file'},
        {'name': 'route:cache', 'description': 'Create a route cache file for faster route registration'},
        {'name': 'route:clear', 'description': 'Remove the route cache file'},
        {'name': 'view:cache', 'description': 'Compile all of the application\'s Blade templates'},
        {'name': 'view:clear', 'description': 'Clear all compiled view files'},
        {'name': 'optimize', 'description': 'Cache the framework bootstrap files'},
        {'name': 'optimize:clear', 'description': 'Remove the cached bootstrap files'},
        {'name': 'migrate', 'description': 'Run the database migrations'},
        {'name': 'migrate:status', 'description': 'Show the status of each migration'},
        {'name': 'queue:restart', 'description': 'Restart queue worker daemons after their current job'},
        {'name': 'schedule:list', 'description': 'List all scheduled tasks'},
        {'name': 'about', 'description': 'Display basic information about your application'},
    ]

    context = {
        'site': laravel_site,
        'common_commands': common_commands,
    }

    return render(request, 'laravelManager/artisan.html', context)


@login_required
@require_http_methods(['POST'])
def run_artisan(request, site_id):
    """Execute an artisan command"""
    laravel_site = get_object_or_404(LaravelSite, pk=site_id)

    command = request.POST.get('command', '').strip()
    if not command:
        return JsonResponse({'success': False, 'error': 'No command provided'})

    # Security: Whitelist allowed commands
    allowed_commands = [
        'cache:clear', 'config:cache', 'config:clear',
        'route:cache', 'route:clear', 'view:cache', 'view:clear',
        'optimize', 'optimize:clear', 'migrate', 'migrate:status',
        'queue:restart', 'schedule:list', 'about', 'env',
        'storage:link', 'key:generate',
    ]

    base_command = command.split()[0] if command else ''
    if base_command not in allowed_commands:
        return JsonResponse({
            'success': False,
            'error': f'Command not allowed: {base_command}'
        })

    try:
        site_path = Path(laravel_site.current_release_path)

        result = subprocess.run(
            ['php', 'artisan'] + command.split(),
            cwd=site_path,
            capture_output=True,
            text=True,
            timeout=60
        )

        return JsonResponse({
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr if result.returncode != 0 else None,
            'exit_code': result.returncode,
        })

    except subprocess.TimeoutExpired:
        return JsonResponse({
            'success': False,
            'error': 'Command timed out after 60 seconds'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def tinker(request, site_id):
    """Laravel Tinker interface (limited)"""
    laravel_site = get_object_or_404(LaravelSite, pk=site_id)

    context = {
        'site': laravel_site,
    }

    return render(request, 'laravelManager/tinker.html', context)


@login_required
def workers(request, site_id):
    """Queue workers management"""
    laravel_site = get_object_or_404(LaravelSite, pk=site_id)
    workers = laravel_site.queue_workers.all()

    context = {
        'site': laravel_site,
        'workers': workers,
    }

    return render(request, 'laravelManager/workers.html', context)


@login_required
def create_worker(request, site_id):
    """Create a new queue worker"""
    laravel_site = get_object_or_404(LaravelSite, pk=site_id)

    if request.method == 'POST':
        try:
            worker = QueueWorker.objects.create(
                laravel_site=laravel_site,
                name=request.POST.get('name', 'default'),
                queue=request.POST.get('queue', 'default'),
                connection=request.POST.get('connection', 'redis'),
                processes=int(request.POST.get('processes', 1)),
                tries=int(request.POST.get('tries', 3)),
                timeout=int(request.POST.get('timeout', 60)),
            )

            # Update supervisor configuration
            _update_supervisor_config(laravel_site)

            messages.success(request, f'Worker {worker.name} created!')
            return redirect('laravelManager:workers', site_id=site_id)

        except Exception as e:
            messages.error(request, f'Error creating worker: {str(e)}')

    context = {
        'site': laravel_site,
    }

    return render(request, 'laravelManager/create_worker.html', context)


@login_required
def worker_detail(request, site_id, worker_id):
    """Worker detail and management"""
    laravel_site = get_object_or_404(LaravelSite, pk=site_id)
    worker = get_object_or_404(QueueWorker, pk=worker_id, laravel_site=laravel_site)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update':
            worker.processes = int(request.POST.get('processes', worker.processes))
            worker.tries = int(request.POST.get('tries', worker.tries))
            worker.timeout = int(request.POST.get('timeout', worker.timeout))
            worker.enabled = request.POST.get('enabled') == 'on'
            worker.save()
            _update_supervisor_config(laravel_site)
            messages.success(request, 'Worker updated!')

        elif action == 'delete':
            worker.delete()
            _update_supervisor_config(laravel_site)
            messages.success(request, 'Worker deleted!')
            return redirect('laravelManager:workers', site_id=site_id)

        elif action == 'restart':
            _restart_worker(worker)
            messages.success(request, 'Worker restarted!')

    context = {
        'site': laravel_site,
        'worker': worker,
    }

    return render(request, 'laravelManager/worker_detail.html', context)


@login_required
def horizon(request, site_id):
    """Laravel Horizon dashboard proxy"""
    laravel_site = get_object_or_404(LaravelSite, pk=site_id)

    if not laravel_site.horizon_enabled:
        messages.warning(request, 'Horizon is not enabled for this site.')
        return redirect('laravelManager:site_detail', site_id=site_id)

    context = {
        'site': laravel_site,
        'horizon_url': f"https://{laravel_site.website.domain}/horizon",
    }

    return render(request, 'laravelManager/horizon.html', context)


@login_required
def scheduler(request, site_id):
    """Scheduler management"""
    laravel_site = get_object_or_404(LaravelSite, pk=site_id)

    # Get scheduled tasks by running artisan schedule:list
    tasks = []
    try:
        site_path = Path(laravel_site.current_release_path)
        result = subprocess.run(
            ['php', 'artisan', 'schedule:list'],
            cwd=site_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            # Parse output
            for line in result.stdout.splitlines():
                if line.strip() and not line.startswith('-'):
                    tasks.append({'raw': line})
    except Exception:
        pass

    context = {
        'site': laravel_site,
        'tasks': tasks,
        'scheduler_enabled': laravel_site.scheduler_enabled,
    }

    return render(request, 'laravelManager/scheduler.html', context)


@login_required
def env_editor(request, site_id):
    """Environment variables editor"""
    laravel_site = get_object_or_404(LaravelSite, pk=site_id)

    # Read current .env file
    env_path = Path(laravel_site.shared_path) / '.env'
    env_content = ''
    env_vars = {}

    if env_path.exists():
        env_content = env_path.read_text()
        for line in env_content.splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # Mask sensitive values
                if any(s in key.upper() for s in ['PASSWORD', 'SECRET', 'KEY', 'TOKEN']):
                    env_vars[key] = '********'
                else:
                    env_vars[key] = value.strip('"\'')

    context = {
        'site': laravel_site,
        'env_vars': env_vars,
    }

    return render(request, 'laravelManager/env_editor.html', context)


@login_required
@require_http_methods(['POST'])
def update_env(request, site_id):
    """Update environment variables"""
    laravel_site = get_object_or_404(LaravelSite, pk=site_id)

    try:
        env_path = Path(laravel_site.shared_path) / '.env'

        # Get updated content
        env_content = request.POST.get('env_content', '')

        # Validate - basic check for APP_KEY
        if 'APP_KEY=' not in env_content:
            messages.error(request, 'APP_KEY is required in .env file')
            return redirect('laravelManager:env_editor', site_id=site_id)

        # Write new content
        env_path.write_text(env_content)

        # Clear config cache
        site_path = Path(laravel_site.current_release_path)
        subprocess.run(
            ['php', 'artisan', 'config:clear'],
            cwd=site_path,
            capture_output=True,
            timeout=30
        )

        messages.success(request, 'Environment updated successfully!')

    except Exception as e:
        messages.error(request, f'Error updating environment: {str(e)}')

    return redirect('laravelManager:env_editor', site_id=site_id)


@login_required
def logs(request, site_id):
    """Laravel logs viewer"""
    laravel_site = get_object_or_404(LaravelSite, pk=site_id)

    log_path = Path(laravel_site.shared_path) / 'storage' / 'logs'
    log_files = []

    if log_path.exists():
        for log_file in sorted(log_path.glob('*.log'), reverse=True):
            stat = log_file.stat()
            log_files.append({
                'name': log_file.name,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime),
            })

    # Get content of selected log file
    selected_log = request.GET.get('file', 'laravel.log')
    log_content = ''

    selected_path = log_path / selected_log
    if selected_path.exists() and selected_path.is_file():
        # Read last 1000 lines
        try:
            with open(selected_path, 'r') as f:
                lines = f.readlines()
                log_content = ''.join(lines[-1000:])
        except Exception:
            log_content = 'Error reading log file'

    context = {
        'site': laravel_site,
        'log_files': log_files,
        'selected_log': selected_log,
        'log_content': log_content,
    }

    return render(request, 'laravelManager/logs.html', context)


@login_required
def download_logs(request, site_id):
    """Download log file"""
    laravel_site = get_object_or_404(LaravelSite, pk=site_id)

    filename = request.GET.get('file', 'laravel.log')
    log_path = Path(laravel_site.shared_path) / 'storage' / 'logs' / filename

    if not log_path.exists() or not log_path.is_file():
        raise Http404("Log file not found")

    # Security check - ensure path is within logs directory
    logs_dir = Path(laravel_site.shared_path) / 'storage' / 'logs'
    if not str(log_path.resolve()).startswith(str(logs_dir.resolve())):
        raise Http404("Invalid path")

    response = HttpResponse(log_path.read_bytes(), content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# API Endpoints

@login_required
def api_site_status(request, site_id):
    """Get site status via API"""
    laravel_site = get_object_or_404(LaravelSite, pk=site_id)

    status = {
        'site_id': laravel_site.id,
        'domain': laravel_site.website.domain,
        'php_version': laravel_site.php_version,
        'laravel_version': laravel_site.laravel_version,
        'last_deployed': laravel_site.last_deployed.isoformat() if laravel_site.last_deployed else None,
        'horizon_enabled': laravel_site.horizon_enabled,
        'scheduler_enabled': laravel_site.scheduler_enabled,
        'active_workers': laravel_site.queue_workers.filter(enabled=True).count(),
    }

    return JsonResponse(status)


@login_required
def api_site_metrics(request, site_id):
    """Get site metrics via API"""
    laravel_site = get_object_or_404(LaravelSite, pk=site_id)

    metrics = _get_site_metrics(laravel_site)

    return JsonResponse(metrics)


# Webhook endpoint

@csrf_exempt
@require_http_methods(['POST'])
def webhook_deploy(request, token):
    """Handle deployment webhooks from GitHub/GitLab/Bitbucket"""
    try:
        # Find site by webhook token
        laravel_site = LaravelSite.objects.get(
            # Assuming we store webhook token somewhere
            # For now, use a simple lookup
            website__domain__icontains=token[:10]  # Placeholder
        )

        # Verify webhook signature (implementation depends on provider)
        # ...

        # Parse payload
        payload = json.loads(request.body)

        # Determine branch
        branch = 'main'
        if 'ref' in payload:  # GitHub/GitLab
            branch = payload['ref'].replace('refs/heads/', '')

        # Only deploy if branch matches
        if branch != laravel_site.git_branch:
            return JsonResponse({'status': 'skipped', 'reason': 'branch mismatch'})

        # Create deployment
        release_id = datetime.now().strftime('%Y%m%d%H%M%S')
        deployment = Deployment.objects.create(
            laravel_site=laravel_site,
            release_id=release_id,
            git_branch=branch,
            git_commit=payload.get('after', payload.get('checkout_sha', '')),
            status='pending',
            triggered_by='webhook',
        )

        # Run deployment asynchronously
        _run_deployment(deployment)

        return JsonResponse({
            'status': 'accepted',
            'deployment_id': deployment.id,
            'release_id': release_id,
        })

    except LaravelSite.DoesNotExist:
        return JsonResponse({'status': 'error', 'reason': 'site not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'reason': str(e)}, status=500)


# Helper functions

def _initialize_laravel_structure(laravel_site):
    """Initialize Laravel directory structure for a new site"""
    site_path = Path(laravel_site.site_path)

    directories = [
        site_path / 'releases',
        site_path / 'shared' / 'storage' / 'app' / 'public',
        site_path / 'shared' / 'storage' / 'framework' / 'cache',
        site_path / 'shared' / 'storage' / 'framework' / 'sessions',
        site_path / 'shared' / 'storage' / 'framework' / 'views',
        site_path / 'shared' / 'storage' / 'logs',
        site_path / '.mindset' / 'hooks',
        site_path / '.mindset' / 'logs',
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def _get_site_metrics(laravel_site):
    """Get metrics for a Laravel site"""
    metrics = {
        'deployments_today': laravel_site.deployments.filter(
            started_at__date=datetime.today().date()
        ).count(),
        'failed_deployments_week': laravel_site.deployments.filter(
            status='failed'
        ).count(),
        'active_workers': laravel_site.queue_workers.filter(enabled=True).count(),
    }

    return metrics


def _run_deployment(deployment):
    """Run a deployment (should be async in production)"""
    # This is a placeholder - in production, use Celery
    deployment.status = 'running'
    deployment.save()

    try:
        # Deployment logic would go here
        # For now, just mark as success
        deployment.status = 'success'
        deployment.finished_at = datetime.now()
        deployment.laravel_site.last_deployed = datetime.now()
        deployment.laravel_site.save()
    except Exception as e:
        deployment.status = 'failed'
        deployment.log = str(e)
        deployment.finished_at = datetime.now()

    deployment.save()


def _perform_rollback(laravel_site, target_deployment):
    """Perform a rollback to a previous release"""
    # Placeholder implementation
    pass


def _update_supervisor_config(laravel_site):
    """Update supervisor configuration for queue workers"""
    # Placeholder implementation
    pass


def _restart_worker(worker):
    """Restart a queue worker"""
    # Placeholder implementation
    pass
