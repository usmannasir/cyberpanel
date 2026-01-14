# Backup Architecture - Mindset Platform

## Overview

The Mindset backup system provides comprehensive, encrypted, multi-destination backup capabilities for Laravel applications and server infrastructure.

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BACKUP ARCHITECTURE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      BACKUP SCHEDULER                                │    │
│  │                    (Celery Beat)                                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                │                                             │
│                    ┌───────────┴───────────┐                                │
│                    │                       │                                │
│                    ▼                       ▼                                │
│  ┌──────────────────────┐    ┌──────────────────────┐                      │
│  │   SCHEDULED BACKUPS  │    │   ON-DEMAND BACKUPS  │                      │
│  │                      │    │                      │                      │
│  │  - Daily full        │    │  - Manual trigger    │                      │
│  │  - Hourly incremental│    │  - Pre-deployment    │                      │
│  │  - Weekly archive    │    │  - Pre-migration     │                      │
│  └──────────┬───────────┘    └──────────┬───────────┘                      │
│             │                           │                                   │
│             └───────────┬───────────────┘                                   │
│                         ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      BACKUP ENGINE                                   │   │
│  │                                                                      │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │   │
│  │  │  Database   │  │    Files    │  │    Full     │                  │   │
│  │  │  Backup     │  │   Backup    │  │  Snapshot   │                  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                  │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                         │                                                   │
│                         ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    ENCRYPTION LAYER                                  │   │
│  │                    (AES-256-GCM)                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                         │                                                   │
│  ┌──────────┬───────────┼───────────┬───────────┬───────────┐              │
│  │          │           │           │           │           │              │
│  ▼          ▼           ▼           ▼           ▼           ▼              │
│ ┌────┐   ┌────┐     ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐        │
│ │Local│   │ S3 │     │Backblaze│  │ Google │  │  SFTP  │  │ MinIO  │        │
│ │Disk │   │    │     │   B2   │  │ Drive  │  │        │  │        │        │
│ └────┘   └────┘     └────────┘  └────────┘  └────────┘  └────────┘        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Backup Types

### 2.1 Database Backup

```python
# mindset/backup/database.py

import subprocess
import gzip
from pathlib import Path
from datetime import datetime
from typing import Optional

class DatabaseBackup:
    """MySQL/MariaDB backup handler"""

    def __init__(self, config: dict):
        self.host = config.get('host', 'localhost')
        self.user = config.get('user')
        self.password = config.get('password')
        self.backup_dir = Path(config.get('backup_dir', '/var/lib/mindset/backups'))

    def backup_database(
        self,
        database: str,
        output_dir: Optional[Path] = None,
        compress: bool = True
    ) -> Path:
        """Create full database backup"""
        output_dir = output_dir or self.backup_dir / 'databases'
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"{database}_{timestamp}.sql"

        if compress:
            filename += '.gz'

        output_path = output_dir / filename

        # Build mysqldump command
        cmd = [
            'mysqldump',
            f'--host={self.host}',
            f'--user={self.user}',
            f'--password={self.password}',
            '--single-transaction',
            '--routines',
            '--triggers',
            '--events',
            '--quick',
            database
        ]

        if compress:
            # Pipe through gzip
            with open(output_path, 'wb') as f:
                dump = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                gzip_proc = subprocess.Popen(['gzip', '-9'], stdin=dump.stdout, stdout=f)
                gzip_proc.wait()
        else:
            with open(output_path, 'w') as f:
                subprocess.run(cmd, stdout=f, check=True)

        return output_path

    def backup_all_databases(self, exclude: list = None) -> list[Path]:
        """Backup all databases except system databases"""
        exclude = exclude or ['information_schema', 'performance_schema', 'mysql', 'sys']

        # Get list of databases
        cmd = [
            'mysql',
            f'--host={self.host}',
            f'--user={self.user}',
            f'--password={self.password}',
            '-e', 'SHOW DATABASES'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        databases = [db for db in result.stdout.strip().split('\n')[1:] if db not in exclude]

        backup_files = []
        for database in databases:
            backup_file = self.backup_database(database)
            backup_files.append(backup_file)

        return backup_files

    def incremental_backup(self, database: str, last_backup: datetime) -> Path:
        """Create incremental backup using binary logs"""
        # Get binary log position from last backup
        # Stream changes since then
        # This is a simplified version - production would use mysqlbinlog
        pass


class PostgreSQLBackup:
    """PostgreSQL backup handler"""

    def __init__(self, config: dict):
        self.host = config.get('host', 'localhost')
        self.user = config.get('user')
        self.backup_dir = Path(config.get('backup_dir', '/var/lib/mindset/backups'))

    def backup_database(self, database: str, output_dir: Optional[Path] = None) -> Path:
        """Create full database backup using pg_dump"""
        output_dir = output_dir or self.backup_dir / 'databases'
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        output_path = output_dir / f"{database}_{timestamp}.sql.gz"

        cmd = [
            'pg_dump',
            f'--host={self.host}',
            f'--username={self.user}',
            '--format=custom',
            '--compress=9',
            f'--file={output_path}',
            database
        ]

        subprocess.run(cmd, check=True)
        return output_path
```

### 2.2 File Backup

```python
# mindset/backup/files.py

import tarfile
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, List

class FileBackup:
    """File system backup handler"""

    def __init__(self, config: dict):
        self.backup_dir = Path(config.get('backup_dir', '/var/lib/mindset/backups'))
        self.exclude_patterns = config.get('exclude_patterns', [
            '*.log',
            '*.tmp',
            'node_modules',
            'vendor',
            '.git',
            'storage/logs/*',
        ])

    def backup_site(
        self,
        site_path: Path,
        site_name: str,
        output_dir: Optional[Path] = None,
        incremental: bool = False,
        reference_backup: Optional[Path] = None
    ) -> Path:
        """Backup a website's files"""
        output_dir = output_dir or self.backup_dir / 'files'
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_type = 'inc' if incremental else 'full'
        output_path = output_dir / f"{site_name}_{backup_type}_{timestamp}.tar.gz"

        if incremental and reference_backup:
            # Use rsync for incremental backup
            return self._incremental_backup(site_path, site_name, reference_backup, output_path)
        else:
            return self._full_backup(site_path, output_path)

    def _full_backup(self, source_path: Path, output_path: Path) -> Path:
        """Create full tar.gz backup"""
        exclude_args = []
        for pattern in self.exclude_patterns:
            exclude_args.extend(['--exclude', pattern])

        cmd = [
            'tar',
            '-czf', str(output_path),
            *exclude_args,
            '-C', str(source_path.parent),
            source_path.name
        ]

        subprocess.run(cmd, check=True)
        return output_path

    def _incremental_backup(
        self,
        source_path: Path,
        site_name: str,
        reference_backup: Path,
        output_path: Path
    ) -> Path:
        """Create incremental backup using tar with --newer"""
        # Get reference backup timestamp
        cmd = [
            'tar',
            '-czf', str(output_path),
            f'--newer-mtime={reference_backup}',
            '-C', str(source_path.parent),
            source_path.name
        ]

        subprocess.run(cmd, check=True)
        return output_path

    def backup_laravel_site(
        self,
        site_path: Path,
        site_name: str,
        include_vendor: bool = False
    ) -> Path:
        """Laravel-specific backup with intelligent exclusions"""
        # Laravel-specific excludes
        laravel_excludes = [
            'storage/framework/cache/*',
            'storage/framework/sessions/*',
            'storage/framework/views/*',
            'storage/logs/*',
            'bootstrap/cache/*',
            '.env',  # Backed up separately and encrypted
        ]

        if not include_vendor:
            laravel_excludes.extend(['vendor', 'node_modules'])

        original_excludes = self.exclude_patterns.copy()
        self.exclude_patterns.extend(laravel_excludes)

        try:
            backup_path = self.backup_site(site_path, site_name)
        finally:
            self.exclude_patterns = original_excludes

        return backup_path


class IncrementalBackup:
    """Rsync-based incremental backup handler"""

    def __init__(self, backup_dir: Path):
        self.backup_dir = backup_dir

    def create_snapshot(
        self,
        source: Path,
        name: str,
        link_dest: Optional[Path] = None
    ) -> Path:
        """Create rsync-based incremental snapshot"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        snapshot_path = self.backup_dir / name / timestamp
        snapshot_path.mkdir(parents=True, exist_ok=True)

        cmd = [
            'rsync',
            '-av',
            '--delete',
            '--exclude', '.git',
            '--exclude', 'node_modules',
            '--exclude', 'vendor',
        ]

        if link_dest:
            cmd.extend(['--link-dest', str(link_dest)])

        cmd.extend([f'{source}/', str(snapshot_path)])

        subprocess.run(cmd, check=True)

        # Update 'latest' symlink
        latest_link = self.backup_dir / name / 'latest'
        if latest_link.is_symlink():
            latest_link.unlink()
        latest_link.symlink_to(snapshot_path)

        return snapshot_path
```

### 2.3 Full Application Snapshot

```python
# mindset/backup/snapshot.py

from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
import json

from .database import DatabaseBackup
from .files import FileBackup
from .encryption import BackupEncryption

@dataclass
class BackupManifest:
    """Backup manifest with metadata"""
    backup_id: str
    site_name: str
    created_at: str
    backup_type: str  # full, incremental, pre-deploy
    components: Dict[str, str]  # component -> file path
    size_bytes: int
    encrypted: bool
    checksum: str
    laravel_version: Optional[str] = None
    php_version: Optional[str] = None

class ApplicationSnapshot:
    """Full application snapshot including database and files"""

    def __init__(
        self,
        db_backup: DatabaseBackup,
        file_backup: FileBackup,
        encryption: BackupEncryption,
        backup_dir: Path
    ):
        self.db_backup = db_backup
        self.file_backup = file_backup
        self.encryption = encryption
        self.backup_dir = backup_dir

    async def create_snapshot(
        self,
        site_name: str,
        site_path: Path,
        database_name: str,
        backup_type: str = 'full',
        encrypt: bool = True
    ) -> BackupManifest:
        """Create complete application snapshot"""
        backup_id = f"{site_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        snapshot_dir = self.backup_dir / backup_id
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        components = {}
        total_size = 0

        # 1. Backup database
        db_file = self.db_backup.backup_database(database_name, snapshot_dir)
        if encrypt:
            db_file = await self.encryption.encrypt_file(db_file)
        components['database'] = str(db_file.relative_to(snapshot_dir))
        total_size += db_file.stat().st_size

        # 2. Backup files
        files_archive = self.file_backup.backup_laravel_site(site_path, site_name)
        if encrypt:
            files_archive = await self.encryption.encrypt_file(files_archive)
        # Move to snapshot dir
        dest_path = snapshot_dir / files_archive.name
        files_archive.rename(dest_path)
        components['files'] = str(dest_path.relative_to(snapshot_dir))
        total_size += dest_path.stat().st_size

        # 3. Backup .env separately (always encrypted)
        env_path = site_path / '.env'
        if env_path.exists():
            env_backup = await self._backup_env(env_path, snapshot_dir)
            components['env'] = str(env_backup.relative_to(snapshot_dir))
            total_size += env_backup.stat().st_size

        # 4. Get Laravel metadata
        laravel_version = await self._get_laravel_version(site_path)
        php_version = await self._get_php_version(site_path)

        # 5. Create manifest
        manifest = BackupManifest(
            backup_id=backup_id,
            site_name=site_name,
            created_at=datetime.utcnow().isoformat(),
            backup_type=backup_type,
            components=components,
            size_bytes=total_size,
            encrypted=encrypt,
            checksum=await self._calculate_checksum(snapshot_dir),
            laravel_version=laravel_version,
            php_version=php_version
        )

        # Save manifest
        manifest_path = snapshot_dir / 'manifest.json'
        manifest_path.write_text(json.dumps(manifest.__dict__, indent=2))

        return manifest

    async def restore_snapshot(
        self,
        backup_id: str,
        target_site_path: Path,
        target_database: str,
        restore_components: List[str] = None
    ) -> bool:
        """Restore from snapshot"""
        restore_components = restore_components or ['database', 'files', 'env']

        snapshot_dir = self.backup_dir / backup_id
        manifest_path = snapshot_dir / 'manifest.json'

        if not manifest_path.exists():
            raise ValueError(f"Backup {backup_id} not found")

        manifest = BackupManifest(**json.loads(manifest_path.read_text()))

        # 1. Restore database
        if 'database' in restore_components and 'database' in manifest.components:
            db_file = snapshot_dir / manifest.components['database']
            if manifest.encrypted:
                db_file = await self.encryption.decrypt_file(db_file)
            await self._restore_database(db_file, target_database)

        # 2. Restore files
        if 'files' in restore_components and 'files' in manifest.components:
            files_archive = snapshot_dir / manifest.components['files']
            if manifest.encrypted:
                files_archive = await self.encryption.decrypt_file(files_archive)
            await self._restore_files(files_archive, target_site_path)

        # 3. Restore .env
        if 'env' in restore_components and 'env' in manifest.components:
            env_backup = snapshot_dir / manifest.components['env']
            await self._restore_env(env_backup, target_site_path)

        return True

    async def _backup_env(self, env_path: Path, output_dir: Path) -> Path:
        """Backup and encrypt .env file"""
        output_path = output_dir / '.env.encrypted'
        await self.encryption.encrypt_file(env_path, output_path)
        return output_path

    async def _get_laravel_version(self, site_path: Path) -> Optional[str]:
        """Extract Laravel version from composer.json"""
        composer_path = site_path / 'composer.json'
        if composer_path.exists():
            import json
            data = json.loads(composer_path.read_text())
            return data.get('require', {}).get('laravel/framework')
        return None
```

---

## 3. Encryption Layer

```python
# mindset/backup/encryption.py

from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os
import base64

class BackupEncryption:
    """AES-256-GCM encryption for backups"""

    def __init__(self, master_key: bytes = None, password: str = None):
        if master_key:
            self.key = master_key
        elif password:
            self.key = self._derive_key(password)
        else:
            raise ValueError("Must provide master_key or password")

    def _derive_key(self, password: str, salt: bytes = None) -> bytes:
        """Derive encryption key from password"""
        salt = salt or os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        return kdf.derive(password.encode())

    async def encrypt_file(
        self,
        input_path: Path,
        output_path: Path = None
    ) -> Path:
        """Encrypt a file using AES-256-GCM"""
        output_path = output_path or input_path.with_suffix(input_path.suffix + '.enc')

        # Generate random nonce
        nonce = os.urandom(12)

        # Read and encrypt
        aesgcm = AESGCM(self.key)
        plaintext = input_path.read_bytes()
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        # Write nonce + ciphertext
        with open(output_path, 'wb') as f:
            f.write(nonce)
            f.write(ciphertext)

        # Set secure permissions
        os.chmod(output_path, 0o600)

        return output_path

    async def decrypt_file(
        self,
        input_path: Path,
        output_path: Path = None
    ) -> Path:
        """Decrypt a file"""
        if output_path is None:
            # Remove .enc suffix
            output_path = Path(str(input_path).replace('.enc', ''))

        with open(input_path, 'rb') as f:
            nonce = f.read(12)
            ciphertext = f.read()

        aesgcm = AESGCM(self.key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)

        output_path.write_bytes(plaintext)
        os.chmod(output_path, 0o600)

        return output_path

    async def encrypt_stream(self, input_stream, output_stream, chunk_size: int = 64 * 1024):
        """Stream encryption for large files"""
        nonce = os.urandom(12)
        output_stream.write(nonce)

        aesgcm = AESGCM(self.key)

        while True:
            chunk = input_stream.read(chunk_size)
            if not chunk:
                break

            # For streaming, we need to handle chunks differently
            # This is simplified - production would use chunked AEAD
            encrypted_chunk = aesgcm.encrypt(nonce, chunk, None)
            output_stream.write(len(encrypted_chunk).to_bytes(4, 'big'))
            output_stream.write(encrypted_chunk)
```

---

## 4. Backup Destinations

### 4.1 Storage Provider Interface

```python
# mindset/backup/storage/base.py

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class StorageFile:
    name: str
    path: str
    size: int
    modified: str

class StorageProvider(ABC):
    """Abstract base class for backup storage providers"""

    @abstractmethod
    async def upload(self, local_path: Path, remote_path: str) -> bool:
        """Upload file to storage"""
        pass

    @abstractmethod
    async def download(self, remote_path: str, local_path: Path) -> bool:
        """Download file from storage"""
        pass

    @abstractmethod
    async def delete(self, remote_path: str) -> bool:
        """Delete file from storage"""
        pass

    @abstractmethod
    async def list(self, prefix: str = '') -> List[StorageFile]:
        """List files in storage"""
        pass

    @abstractmethod
    async def exists(self, remote_path: str) -> bool:
        """Check if file exists"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check storage connectivity"""
        pass
```

### 4.2 S3-Compatible Storage

```python
# mindset/backup/storage/s3.py

import boto3
from botocore.config import Config
from pathlib import Path
from typing import List
from .base import StorageProvider, StorageFile

class S3Storage(StorageProvider):
    """S3-compatible storage (AWS S3, MinIO, Wasabi, etc.)"""

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        bucket: str,
        endpoint_url: str = None,  # For S3-compatible services
        region: str = 'us-east-1'
    ):
        self.bucket = bucket

        config = Config(
            retries={'max_attempts': 3, 'mode': 'adaptive'}
        )

        self.client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            endpoint_url=endpoint_url,
            region_name=region,
            config=config
        )

    async def upload(self, local_path: Path, remote_path: str) -> bool:
        """Upload file to S3"""
        try:
            # Use multipart upload for large files
            file_size = local_path.stat().st_size

            if file_size > 100 * 1024 * 1024:  # > 100MB
                self._multipart_upload(local_path, remote_path)
            else:
                self.client.upload_file(str(local_path), self.bucket, remote_path)

            return True
        except Exception as e:
            raise StorageError(f"S3 upload failed: {e}")

    def _multipart_upload(self, local_path: Path, remote_path: str):
        """Multipart upload for large files"""
        from boto3.s3.transfer import TransferConfig

        config = TransferConfig(
            multipart_threshold=100 * 1024 * 1024,
            max_concurrency=10,
            multipart_chunksize=100 * 1024 * 1024,
        )

        self.client.upload_file(
            str(local_path),
            self.bucket,
            remote_path,
            Config=config
        )

    async def download(self, remote_path: str, local_path: Path) -> bool:
        """Download file from S3"""
        try:
            self.client.download_file(self.bucket, remote_path, str(local_path))
            return True
        except Exception as e:
            raise StorageError(f"S3 download failed: {e}")

    async def delete(self, remote_path: str) -> bool:
        """Delete file from S3"""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=remote_path)
            return True
        except Exception as e:
            raise StorageError(f"S3 delete failed: {e}")

    async def list(self, prefix: str = '') -> List[StorageFile]:
        """List files in S3 bucket"""
        files = []
        paginator = self.client.get_paginator('list_objects_v2')

        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get('Contents', []):
                files.append(StorageFile(
                    name=obj['Key'].split('/')[-1],
                    path=obj['Key'],
                    size=obj['Size'],
                    modified=obj['LastModified'].isoformat()
                ))

        return files

    async def exists(self, remote_path: str) -> bool:
        """Check if file exists in S3"""
        try:
            self.client.head_object(Bucket=self.bucket, Key=remote_path)
            return True
        except:
            return False

    async def health_check(self) -> bool:
        """Check S3 connectivity"""
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return True
        except:
            return False
```

### 4.3 Backblaze B2

```python
# mindset/backup/storage/backblaze.py

from b2sdk.v2 import InMemoryAccountInfo, B2Api
from pathlib import Path
from typing import List
from .base import StorageProvider, StorageFile

class BackblazeB2Storage(StorageProvider):
    """Backblaze B2 storage provider"""

    def __init__(
        self,
        application_key_id: str,
        application_key: str,
        bucket_name: str
    ):
        info = InMemoryAccountInfo()
        self.b2_api = B2Api(info)
        self.b2_api.authorize_account("production", application_key_id, application_key)
        self.bucket = self.b2_api.get_bucket_by_name(bucket_name)

    async def upload(self, local_path: Path, remote_path: str) -> bool:
        """Upload file to B2"""
        try:
            self.bucket.upload_local_file(
                local_file=str(local_path),
                file_name=remote_path
            )
            return True
        except Exception as e:
            raise StorageError(f"B2 upload failed: {e}")

    async def download(self, remote_path: str, local_path: Path) -> bool:
        """Download file from B2"""
        try:
            downloaded_file = self.bucket.download_file_by_name(remote_path)
            downloaded_file.save_to(str(local_path))
            return True
        except Exception as e:
            raise StorageError(f"B2 download failed: {e}")

    async def delete(self, remote_path: str) -> bool:
        """Delete file from B2"""
        try:
            file_version = self.bucket.get_file_info_by_name(remote_path)
            self.bucket.delete_file_version(file_version.id_, file_version.file_name)
            return True
        except Exception as e:
            raise StorageError(f"B2 delete failed: {e}")

    async def list(self, prefix: str = '') -> List[StorageFile]:
        """List files in B2 bucket"""
        files = []
        for file_version, folder_name in self.bucket.ls(folder_to_list=prefix):
            files.append(StorageFile(
                name=file_version.file_name.split('/')[-1],
                path=file_version.file_name,
                size=file_version.size,
                modified=file_version.upload_timestamp
            ))
        return files

    async def exists(self, remote_path: str) -> bool:
        """Check if file exists in B2"""
        try:
            self.bucket.get_file_info_by_name(remote_path)
            return True
        except:
            return False

    async def health_check(self) -> bool:
        """Check B2 connectivity"""
        try:
            self.bucket.ls(folder_to_list='', max_entries=1)
            return True
        except:
            return False
```

### 4.4 Local Storage

```python
# mindset/backup/storage/local.py

import shutil
from pathlib import Path
from typing import List
from .base import StorageProvider, StorageFile

class LocalStorage(StorageProvider):
    """Local filesystem storage provider"""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def upload(self, local_path: Path, remote_path: str) -> bool:
        """Copy file to local backup directory"""
        dest_path = self.base_path / remote_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_path, dest_path)
        return True

    async def download(self, remote_path: str, local_path: Path) -> bool:
        """Copy file from local backup directory"""
        src_path = self.base_path / remote_path
        shutil.copy2(src_path, local_path)
        return True

    async def delete(self, remote_path: str) -> bool:
        """Delete file from local backup directory"""
        file_path = self.base_path / remote_path
        file_path.unlink(missing_ok=True)
        return True

    async def list(self, prefix: str = '') -> List[StorageFile]:
        """List files in local backup directory"""
        files = []
        search_path = self.base_path / prefix if prefix else self.base_path

        for file_path in search_path.rglob('*'):
            if file_path.is_file():
                stat = file_path.stat()
                files.append(StorageFile(
                    name=file_path.name,
                    path=str(file_path.relative_to(self.base_path)),
                    size=stat.st_size,
                    modified=stat.st_mtime
                ))

        return files

    async def exists(self, remote_path: str) -> bool:
        """Check if file exists"""
        return (self.base_path / remote_path).exists()

    async def health_check(self) -> bool:
        """Check local storage is accessible"""
        return self.base_path.exists() and os.access(self.base_path, os.W_OK)
```

---

## 5. Retention Policies

```python
# mindset/backup/retention.py

from datetime import datetime, timedelta
from typing import List, Dict
from pathlib import Path
from dataclasses import dataclass

@dataclass
class RetentionPolicy:
    """Backup retention policy configuration"""
    daily_keep: int = 7       # Keep daily backups for 7 days
    weekly_keep: int = 4      # Keep weekly backups for 4 weeks
    monthly_keep: int = 12    # Keep monthly backups for 12 months
    yearly_keep: int = -1     # Keep yearly backups forever (-1)

class RetentionManager:
    """Manage backup retention and cleanup"""

    def __init__(self, storage: StorageProvider, policy: RetentionPolicy):
        self.storage = storage
        self.policy = policy

    async def apply_retention(self, site_name: str) -> Dict[str, int]:
        """Apply retention policy to site backups"""
        backups = await self.storage.list(f"backups/{site_name}/")

        # Group backups by age
        now = datetime.utcnow()
        to_delete = []
        stats = {'kept': 0, 'deleted': 0}

        # Sort by date descending
        backups.sort(key=lambda x: x.modified, reverse=True)

        daily_count = 0
        weekly_count = 0
        monthly_count = 0
        yearly_count = 0

        for backup in backups:
            backup_date = datetime.fromisoformat(backup.modified)
            age_days = (now - backup_date).days

            keep = False

            # Daily backups (last N days)
            if age_days < self.policy.daily_keep:
                if daily_count < self.policy.daily_keep:
                    keep = True
                    daily_count += 1

            # Weekly backups (keep Sundays for N weeks)
            elif age_days < self.policy.weekly_keep * 7:
                if backup_date.weekday() == 6 and weekly_count < self.policy.weekly_keep:
                    keep = True
                    weekly_count += 1

            # Monthly backups (keep 1st of month for N months)
            elif age_days < self.policy.monthly_keep * 30:
                if backup_date.day == 1 and monthly_count < self.policy.monthly_keep:
                    keep = True
                    monthly_count += 1

            # Yearly backups (keep Jan 1st forever)
            else:
                if self.policy.yearly_keep == -1 or yearly_count < self.policy.yearly_keep:
                    if backup_date.month == 1 and backup_date.day == 1:
                        keep = True
                        yearly_count += 1

            if keep:
                stats['kept'] += 1
            else:
                to_delete.append(backup.path)
                stats['deleted'] += 1

        # Delete old backups
        for path in to_delete:
            await self.storage.delete(path)

        return stats
```

---

## 6. Backup Scheduling

```python
# mindset/backup/scheduler.py

from celery import Celery
from celery.schedules import crontab
from datetime import datetime

app = Celery('mindset_backup')

@app.task
def scheduled_backup(site_id: int, backup_type: str = 'full'):
    """Celery task for scheduled backups"""
    from .snapshot import ApplicationSnapshot

    # Get site configuration
    site = get_site_by_id(site_id)

    # Create snapshot
    snapshot = ApplicationSnapshot(...)
    manifest = snapshot.create_snapshot(
        site_name=site.name,
        site_path=site.path,
        database_name=site.database,
        backup_type=backup_type
    )

    # Upload to configured destinations
    for destination in site.backup_destinations:
        upload_backup(manifest, destination)

    # Apply retention policy
    retention = RetentionManager(...)
    retention.apply_retention(site.name)

    return manifest.backup_id

@app.task
def incremental_backup(site_id: int):
    """Hourly incremental backup"""
    # Implementation
    pass

# Celery Beat schedule
app.conf.beat_schedule = {
    'daily-full-backup': {
        'task': 'mindset.backup.scheduler.scheduled_backup',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
        'args': ('all', 'full')
    },
    'hourly-incremental': {
        'task': 'mindset.backup.scheduler.incremental_backup',
        'schedule': crontab(minute=0),  # Every hour
        'args': ('all',)
    },
}
```

---

## 7. Backup UI Integration

```python
# mindset/backup/api.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api/v1/backups", tags=["Backups"])

class BackupRequest(BaseModel):
    site_id: int
    backup_type: str = "full"
    include_database: bool = True
    include_files: bool = True
    encrypt: bool = True
    destinations: List[str] = ["local"]

class RestoreRequest(BaseModel):
    backup_id: str
    site_id: int
    restore_database: bool = True
    restore_files: bool = True

@router.post("/create")
async def create_backup(request: BackupRequest):
    """Create a new backup"""
    # Validate site access
    # Create backup
    # Return backup ID
    pass

@router.get("/list/{site_id}")
async def list_backups(site_id: int):
    """List all backups for a site"""
    pass

@router.post("/restore")
async def restore_backup(request: RestoreRequest):
    """Restore from a backup"""
    pass

@router.delete("/{backup_id}")
async def delete_backup(backup_id: str):
    """Delete a backup"""
    pass

@router.get("/destinations")
async def list_destinations():
    """List configured backup destinations"""
    pass
```

---

*Document Version: 1.0*
*Last Updated: 2024-01-15*
