# -*- coding: utf-8 -*-
import os
import time

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Refresh CyberPanel plugin store cache (hourly scheduler)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Refresh even if cache is not expired.",
        )
        parser.add_argument(
            "--stale-lock-seconds",
            type=int,
            default=900,
            help="Remove the cache-refresh lock if it is older than this many seconds.",
        )

    def handle(self, *args, **options):
        force = bool(options.get("force", False))
        stale_lock_seconds = int(options.get("stale_lock_seconds", 900))

        try:
            from pluginHolder import views as plugin_views
        except Exception as e:
            # Avoid printing secrets; just show a minimal message.
            self.stderr.write("Failed to import pluginHolder views for cache refresh.")
            return 1

        # Only refresh when needed (unless --force is used).
        try:
            cache_expiry_timestamp, _ = plugin_views._get_cache_expiry_time()
            cache_expired = plugin_views._is_cache_expired(cache_expiry_timestamp)
        except Exception:
            cache_expired = True

        if not force and cache_expiry_timestamp and not cache_expired:
            self.stdout.write("Plugin store cache is still fresh; no refresh needed.")
            return 0

        lock_path = plugin_views.PLUGIN_STORE_REFRESH_LOCK_FILE
        try:
            plugin_views._ensure_cache_dir()
        except Exception:
            pass

        # Remove stale lock left behind by a crashed/aborted refresh.
        if os.path.exists(lock_path):
            try:
                age_s = time.time() - os.path.getmtime(lock_path)
                if age_s > stale_lock_seconds:
                    os.remove(lock_path)
                    try:
                        plugin_views.logging.writeToFile(
                            f"Management refresh: removed stale plugin store refresh lock (age: {age_s:.0f}s)"
                        )
                    except Exception:
                        pass
            except Exception:
                pass

        # Acquire lock to avoid stampedes when multiple instances refresh.
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            with os.fdopen(fd, "w") as f:
                f.write(str(os.getpid()))
        except FileExistsError:
            self.stdout.write("Plugin store refresh skipped: lock already exists.")
            return 0
        except Exception:
            self.stderr.write("Plugin store refresh failed: could not acquire refresh lock.")
            return 1

        try:
            plugins = plugin_views._fetch_plugins_from_github()
            if not plugins:
                self.stdout.write("Plugin store refresh fetched 0 plugins; cache not updated.")
                return 0

            plugin_views._save_plugins_cache(plugins)
            self.stdout.write(f"Plugin store cache refreshed successfully. plugins={len(plugins)}")
            return 0
        except Exception as e:
            # Log error summary server-side; don't leak internal exception details to stdout.
            try:
                plugin_views.logging.writeToFile(f"Plugin store cache refresh failed: {str(e)}")
            except Exception:
                pass
            self.stderr.write("Plugin store cache refresh failed. Check error logs.")
            return 1
        finally:
            try:
                if os.path.exists(lock_path):
                    os.remove(lock_path)
            except Exception:
                pass

