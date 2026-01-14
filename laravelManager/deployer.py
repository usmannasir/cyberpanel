# Mindset Laravel Manager - Zero-Downtime Deployer
# Copyright (C) 2024 Mindset Contributors
# Licensed under GPLv3

import os
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field

from .models import LaravelSite, Deployment


@dataclass
class DeploymentStep:
    """Represents a single deployment step"""
    name: str
    description: str
    success: bool = False
    output: str = ""
    error: str = ""
    duration_ms: int = 0


@dataclass
class DeploymentResult:
    """Result of a deployment operation"""
    success: bool
    release_id: str
    steps: List[DeploymentStep] = field(default_factory=list)
    error: Optional[str] = None
    duration_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "release_id": self.release_id,
            "steps": [
                {
                    "name": s.name,
                    "description": s.description,
                    "success": s.success,
                    "output": s.output[-1000:] if s.output else "",
                    "error": s.error,
                    "duration_ms": s.duration_ms,
                }
                for s in self.steps
            ],
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


class LaravelDeployer:
    """
    Zero-downtime deployment engine for Laravel applications

    Implements the Capistrano-style deployment pattern:
    - releases/ directory contains timestamped releases
    - shared/ contains persistent files (.env, storage)
    - current symlink points to active release
    """

    def __init__(self, laravel_site: LaravelSite):
        self.site = laravel_site
        self.site_path = Path(laravel_site.site_path)
        self.releases_path = self.site_path / "releases"
        self.shared_path = self.site_path / "shared"
        self.current_path = self.site_path / "current"

        # Deployment hooks
        self.pre_deploy_hooks: List[Callable] = []
        self.post_deploy_hooks: List[Callable] = []

    async def deploy(
        self,
        source: str,
        branch: str = "main",
        run_migrations: bool = True,
        run_npm_build: bool = True,
        deployment: Optional[Deployment] = None,
    ) -> DeploymentResult:
        """
        Execute a zero-downtime deployment

        Args:
            source: Git repository URL or local path
            branch: Git branch to deploy
            run_migrations: Whether to run database migrations
            run_npm_build: Whether to run npm build
            deployment: Optional Deployment model instance for logging

        Returns:
            DeploymentResult with success status and details
        """
        start_time = datetime.now()
        release_id = start_time.strftime('%Y%m%d%H%M%S')
        release_path = self.releases_path / release_id

        steps: List[DeploymentStep] = []

        try:
            # Update deployment status
            if deployment:
                deployment.status = 'running'
                deployment.release_id = release_id
                deployment.save()

            # Run pre-deploy hooks
            for hook in self.pre_deploy_hooks:
                await hook(self.site, release_id)

            # Step 1: Clone/Copy source
            step = await self._clone_release(source, branch, release_path)
            steps.append(step)
            if not step.success:
                raise DeploymentError(f"Clone failed: {step.error}")

            # Step 2: Link shared resources
            step = await self._link_shared(release_path)
            steps.append(step)
            if not step.success:
                raise DeploymentError(f"Linking shared failed: {step.error}")

            # Step 3: Install Composer dependencies
            step = await self._composer_install(release_path)
            steps.append(step)
            if not step.success:
                raise DeploymentError(f"Composer install failed: {step.error}")

            # Step 4: Install NPM and build (optional)
            if run_npm_build:
                step = await self._npm_build(release_path)
                steps.append(step)
                # NPM build failure is not always fatal
                if not step.success:
                    # Log warning but continue
                    pass

            # Step 5: Run migrations (optional)
            if run_migrations:
                step = await self._run_migrations(release_path)
                steps.append(step)
                if not step.success:
                    raise DeploymentError(f"Migrations failed: {step.error}")

            # Step 6: Optimize Laravel
            step = await self._optimize_laravel(release_path)
            steps.append(step)

            # Step 7: Health check
            step = await self._health_check(release_path)
            steps.append(step)
            if not step.success:
                raise DeploymentError(f"Health check failed: {step.error}")

            # Step 8: Activate release (atomic symlink swap)
            step = await self._activate_release(release_path)
            steps.append(step)
            if not step.success:
                raise DeploymentError(f"Activation failed: {step.error}")

            # Step 9: Reload PHP-FPM
            step = await self._reload_php_fpm()
            steps.append(step)

            # Step 10: Cleanup old releases
            step = await self._cleanup_releases()
            steps.append(step)

            # Step 11: Restart queue workers
            step = await self._restart_workers()
            steps.append(step)

            # Run post-deploy hooks
            for hook in self.post_deploy_hooks:
                await hook(self.site, release_id)

            # Update deployment record
            if deployment:
                deployment.status = 'success'
                deployment.finished_at = datetime.now()
                deployment.log = self._format_log(steps)
                deployment.save()

            # Update site last_deployed
            self.site.last_deployed = datetime.now()
            self.site.save()

            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            return DeploymentResult(
                success=True,
                release_id=release_id,
                steps=steps,
                duration_ms=duration_ms,
            )

        except Exception as e:
            # Rollback on failure
            await self._rollback_release(release_path)

            if deployment:
                deployment.status = 'failed'
                deployment.finished_at = datetime.now()
                deployment.log = self._format_log(steps) + f"\n\nERROR: {str(e)}"
                deployment.save()

            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            return DeploymentResult(
                success=False,
                release_id=release_id,
                steps=steps,
                error=str(e),
                duration_ms=duration_ms,
            )

    async def rollback(self, releases_back: int = 1) -> DeploymentResult:
        """
        Rollback to a previous release

        Args:
            releases_back: Number of releases to go back (1 = previous)

        Returns:
            DeploymentResult
        """
        start_time = datetime.now()
        steps = []

        try:
            # Get list of releases
            releases = sorted(self.releases_path.iterdir(), reverse=True)

            if len(releases) <= releases_back:
                raise DeploymentError("Not enough releases to rollback")

            target_release = releases[releases_back]
            release_id = target_release.name

            # Activate the target release
            step = await self._activate_release(target_release)
            steps.append(step)
            if not step.success:
                raise DeploymentError(f"Activation failed: {step.error}")

            # Reload PHP-FPM
            step = await self._reload_php_fpm()
            steps.append(step)

            # Restart workers
            step = await self._restart_workers()
            steps.append(step)

            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            return DeploymentResult(
                success=True,
                release_id=release_id,
                steps=steps,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            return DeploymentResult(
                success=False,
                release_id="rollback",
                steps=steps,
                error=str(e),
                duration_ms=duration_ms,
            )

    # Deployment Steps

    async def _clone_release(
        self,
        source: str,
        branch: str,
        release_path: Path
    ) -> DeploymentStep:
        """Clone repository to release directory"""
        start = datetime.now()
        step = DeploymentStep(
            name="clone",
            description="Clone repository to new release directory"
        )

        try:
            release_path.mkdir(parents=True, exist_ok=True)

            if source.startswith(('http://', 'https://', 'git@')):
                # Git clone
                cmd = [
                    "git", "clone",
                    "--depth=1",
                    f"--branch={branch}",
                    source,
                    str(release_path)
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300
                )

                step.output = result.stdout
                step.error = result.stderr
                step.success = result.returncode == 0

                # Get commit hash
                if step.success:
                    commit_result = subprocess.run(
                        ["git", "rev-parse", "HEAD"],
                        cwd=release_path,
                        capture_output=True,
                        text=True
                    )
                    if commit_result.returncode == 0:
                        step.output += f"\nCommit: {commit_result.stdout.strip()}"

            else:
                # Local path - copy
                shutil.copytree(source, release_path, dirs_exist_ok=True)
                step.success = True
                step.output = f"Copied from {source}"

        except subprocess.TimeoutExpired:
            step.error = "Git clone timed out after 5 minutes"
        except Exception as e:
            step.error = str(e)

        step.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        return step

    async def _link_shared(self, release_path: Path) -> DeploymentStep:
        """Link shared directories and files"""
        start = datetime.now()
        step = DeploymentStep(
            name="link_shared",
            description="Link shared directories and files"
        )

        try:
            shared_links = {
                # Directories
                "storage/app": self.shared_path / "storage" / "app",
                "storage/framework/cache": self.shared_path / "storage" / "framework" / "cache",
                "storage/framework/sessions": self.shared_path / "storage" / "framework" / "sessions",
                "storage/framework/views": self.shared_path / "storage" / "framework" / "views",
                "storage/logs": self.shared_path / "storage" / "logs",
                # Files
                ".env": self.shared_path / ".env",
            }

            linked = []
            for target, source in shared_links.items():
                target_path = release_path / target

                # Remove existing
                if target_path.exists() or target_path.is_symlink():
                    if target_path.is_dir() and not target_path.is_symlink():
                        shutil.rmtree(target_path)
                    else:
                        target_path.unlink()

                # Create parent directory
                target_path.parent.mkdir(parents=True, exist_ok=True)

                # Create symlink
                if source.exists():
                    target_path.symlink_to(source)
                    linked.append(target)

            step.success = True
            step.output = f"Linked: {', '.join(linked)}"

        except Exception as e:
            step.error = str(e)

        step.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        return step

    async def _composer_install(self, release_path: Path) -> DeploymentStep:
        """Install Composer dependencies"""
        start = datetime.now()
        step = DeploymentStep(
            name="composer_install",
            description="Install PHP dependencies via Composer"
        )

        try:
            result = subprocess.run(
                [
                    "composer", "install",
                    "--no-dev",
                    "--optimize-autoloader",
                    "--no-interaction",
                    "--no-progress"
                ],
                cwd=release_path,
                capture_output=True,
                text=True,
                timeout=600,
                env={**os.environ, "COMPOSER_NO_INTERACTION": "1"}
            )

            step.output = result.stdout
            step.error = result.stderr if result.returncode != 0 else ""
            step.success = result.returncode == 0

        except subprocess.TimeoutExpired:
            step.error = "Composer install timed out after 10 minutes"
        except Exception as e:
            step.error = str(e)

        step.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        return step

    async def _npm_build(self, release_path: Path) -> DeploymentStep:
        """Install NPM dependencies and build assets"""
        start = datetime.now()
        step = DeploymentStep(
            name="npm_build",
            description="Build frontend assets with NPM"
        )

        # Check if package.json exists
        if not (release_path / "package.json").exists():
            step.success = True
            step.output = "Skipped (no package.json)"
            return step

        try:
            # Install dependencies
            install_result = subprocess.run(
                ["npm", "ci", "--no-audit"],
                cwd=release_path,
                capture_output=True,
                text=True,
                timeout=300
            )

            if install_result.returncode != 0:
                step.error = install_result.stderr
                step.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
                return step

            # Build assets
            build_result = subprocess.run(
                ["npm", "run", "build"],
                cwd=release_path,
                capture_output=True,
                text=True,
                timeout=300
            )

            step.output = build_result.stdout
            step.error = build_result.stderr if build_result.returncode != 0 else ""
            step.success = build_result.returncode == 0

        except subprocess.TimeoutExpired:
            step.error = "NPM build timed out after 5 minutes"
        except Exception as e:
            step.error = str(e)

        step.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        return step

    async def _run_migrations(self, release_path: Path) -> DeploymentStep:
        """Run database migrations"""
        start = datetime.now()
        step = DeploymentStep(
            name="migrations",
            description="Run database migrations"
        )

        try:
            result = subprocess.run(
                ["php", "artisan", "migrate", "--force", "--no-interaction"],
                cwd=release_path,
                capture_output=True,
                text=True,
                timeout=300
            )

            step.output = result.stdout
            step.error = result.stderr if result.returncode != 0 else ""
            step.success = result.returncode == 0

        except subprocess.TimeoutExpired:
            step.error = "Migrations timed out after 5 minutes"
        except Exception as e:
            step.error = str(e)

        step.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        return step

    async def _optimize_laravel(self, release_path: Path) -> DeploymentStep:
        """Run Laravel optimization commands"""
        start = datetime.now()
        step = DeploymentStep(
            name="optimize",
            description="Run Laravel optimization commands"
        )

        commands = [
            ["php", "artisan", "config:cache"],
            ["php", "artisan", "route:cache"],
            ["php", "artisan", "view:cache"],
            ["php", "artisan", "event:cache"],
        ]

        outputs = []
        try:
            for cmd in commands:
                result = subprocess.run(
                    cmd,
                    cwd=release_path,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                status = "OK" if result.returncode == 0 else "FAILED"
                outputs.append(f"{' '.join(cmd[2:])}: {status}")

            step.output = "\n".join(outputs)
            step.success = True

        except Exception as e:
            step.error = str(e)

        step.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        return step

    async def _health_check(self, release_path: Path) -> DeploymentStep:
        """Run health checks before activating release"""
        start = datetime.now()
        step = DeploymentStep(
            name="health_check",
            description="Verify release is healthy before activation"
        )

        try:
            checks = []

            # Check 1: PHP syntax on critical files
            critical_files = [
                "bootstrap/app.php",
                "config/app.php",
                "routes/web.php",
            ]

            for file in critical_files:
                file_path = release_path / file
                if file_path.exists():
                    result = subprocess.run(
                        ["php", "-l", str(file_path)],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode != 0:
                        step.error = f"Syntax error in {file}: {result.stderr}"
                        step.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
                        return step
                    checks.append(f"Syntax check {file}: OK")

            # Check 2: Artisan about command
            result = subprocess.run(
                ["php", "artisan", "about", "--json"],
                cwd=release_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                step.error = f"Artisan health check failed: {result.stderr}"
                step.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
                return step

            checks.append("Artisan about: OK")

            # Check 3: Custom health check script
            health_script = self.site_path / ".mindset" / "hooks" / "health-check.sh"
            if health_script.exists():
                result = subprocess.run(
                    ["bash", str(health_script)],
                    cwd=release_path,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode != 0:
                    step.error = f"Custom health check failed: {result.stderr}"
                    step.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
                    return step
                checks.append("Custom health check: OK")

            step.output = "\n".join(checks)
            step.success = True

        except subprocess.TimeoutExpired:
            step.error = "Health check timed out"
        except Exception as e:
            step.error = str(e)

        step.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        return step

    async def _activate_release(self, release_path: Path) -> DeploymentStep:
        """Atomically switch to new release"""
        start = datetime.now()
        step = DeploymentStep(
            name="activate",
            description="Activate new release (atomic symlink swap)"
        )

        try:
            # Create temporary symlink
            temp_link = self.site_path / f"current_tmp_{datetime.now().timestamp()}"
            temp_link.symlink_to(release_path)

            # Atomic rename (this is the zero-downtime moment)
            os.rename(str(temp_link), str(self.current_path))

            step.success = True
            step.output = f"Activated release: {release_path.name}"

        except Exception as e:
            step.error = str(e)
            # Cleanup temp link if it exists
            if temp_link.exists():
                temp_link.unlink()

        step.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        return step

    async def _reload_php_fpm(self) -> DeploymentStep:
        """Reload PHP-FPM to clear opcode cache"""
        start = datetime.now()
        step = DeploymentStep(
            name="reload_php",
            description="Reload PHP-FPM to clear caches"
        )

        try:
            php_version = self.site.php_version.replace('.', '')
            result = subprocess.run(
                ["systemctl", "reload", f"lsphp{php_version}"],
                capture_output=True,
                text=True,
                timeout=30
            )

            step.success = result.returncode == 0
            step.output = "PHP-FPM reloaded" if step.success else result.stderr

        except Exception as e:
            step.error = str(e)
            step.success = True  # Non-fatal

        step.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        return step

    async def _cleanup_releases(self) -> DeploymentStep:
        """Remove old releases beyond keep_releases limit"""
        start = datetime.now()
        step = DeploymentStep(
            name="cleanup",
            description="Remove old releases"
        )

        try:
            keep = self.site.keep_releases
            releases = sorted(self.releases_path.iterdir(), reverse=True)

            removed = []
            for release in releases[keep:]:
                if release.is_dir():
                    shutil.rmtree(release)
                    removed.append(release.name)

            step.success = True
            step.output = f"Removed {len(removed)} old releases"

        except Exception as e:
            step.error = str(e)
            step.success = True  # Non-fatal

        step.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        return step

    async def _restart_workers(self) -> DeploymentStep:
        """Restart queue workers gracefully"""
        start = datetime.now()
        step = DeploymentStep(
            name="restart_workers",
            description="Restart queue workers"
        )

        try:
            result = subprocess.run(
                ["php", "artisan", "queue:restart"],
                cwd=self.current_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            step.success = result.returncode == 0
            step.output = result.stdout if step.success else ""
            step.error = result.stderr if not step.success else ""

        except Exception as e:
            step.error = str(e)
            step.success = True  # Non-fatal

        step.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        return step

    async def _rollback_release(self, failed_release: Path):
        """Cleanup failed release"""
        try:
            if failed_release.exists():
                shutil.rmtree(failed_release)
        except Exception:
            pass  # Best effort cleanup

    def _format_log(self, steps: List[DeploymentStep]) -> str:
        """Format deployment steps into a log string"""
        lines = []
        for step in steps:
            status = "✓" if step.success else "✗"
            lines.append(f"[{status}] {step.name} ({step.duration_ms}ms)")
            if step.output:
                for line in step.output.split('\n')[:10]:
                    lines.append(f"    {line}")
            if step.error:
                lines.append(f"    ERROR: {step.error}")
        return "\n".join(lines)


class DeploymentError(Exception):
    """Deployment-specific error"""
    pass
