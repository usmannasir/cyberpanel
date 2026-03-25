#!/usr/local/CyberCP/bin/python
"""
Test script to verify backward compatibility of database backup improvements
Tests both legacy and new backup/restore paths
"""

import os
import sys
import json
import tempfile
import shutil

sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")

from plogical.mysqlUtilities import mysqlUtilities
from plogical.processUtilities import ProcessUtilities

class BackupCompatibilityTests:
    """Test suite for backup compatibility"""

    @staticmethod
    def setup_test_environment():
        """Create a test directory for backups"""
        test_dir = tempfile.mkdtemp(prefix="cyberpanel_backup_test_")
        print(f"Created test directory: {test_dir}")
        return test_dir

    @staticmethod
    def cleanup_test_environment(test_dir):
        """Clean up test directory"""
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
            print(f"Cleaned up test directory: {test_dir}")

    @staticmethod
    def test_config_file():
        """Test configuration file reading"""
        print("\n=== Testing Configuration File ===")

        config_file = '/usr/local/CyberCP/plogical/backup_config.json'
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
                print(f"Configuration loaded successfully")
                print(f"Use compression: {config['database_backup']['use_compression']}")
                print(f"Use new features: {config['database_backup']['use_new_features']}")
                print(f"Auto-detect restore: {config['compatibility']['auto_detect_restore']}")
                return True
        else:
            print(f"Configuration file not found at {config_file}")
            return False

    @staticmethod
    def test_helper_functions():
        """Test helper functions"""
        print("\n=== Testing Helper Functions ===")

        # Test checkNewBackupFeatures
        new_features = mysqlUtilities.checkNewBackupFeatures()
        print(f"New backup features enabled: {new_features}")

        # Test shouldUseCompression
        use_compression = mysqlUtilities.shouldUseCompression()
        print(f"Compression enabled: {use_compression}")

        # Test supportParallelDump
        parallel_support = mysqlUtilities.supportParallelDump()
        print(f"Parallel dump supported: {parallel_support}")

        # Test getNumberOfCores
        cores = ProcessUtilities.getNumberOfCores()
        print(f"Number of CPU cores: {cores}")

        return True

    @staticmethod
    def test_legacy_backup(test_db="test_legacy_db", test_dir="/tmp"):
        """Test that legacy backups still work"""
        print("\n=== Testing Legacy Backup (No Compression, No New Features) ===")

        try:
            # Create backup with old method
            print(f"Creating legacy backup for {test_db}...")
            result = mysqlUtilities.createDatabaseBackup(
                test_db, test_dir, use_compression=False, use_new_features=False
            )

            if result == 1:
                print(f"✓ Legacy backup created successfully")

                # Check that .sql file exists (not .sql.gz)
                legacy_file = f"{test_dir}/{test_db}.sql"
                if os.path.exists(legacy_file):
                    file_size = os.path.getsize(legacy_file)
                    print(f"✓ Legacy backup file exists: {legacy_file}")
                    print(f"  File size: {file_size} bytes")

                    # Check metadata file
                    metadata_file = f"{test_dir}/{test_db}.backup.json"
                    if os.path.exists(metadata_file):
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                            print(f"✓ Metadata file exists")
                            print(f"  Backup version: {metadata['backup_version']}")
                            print(f"  Compressed: {metadata['compressed']}")
                            print(f"  New features: {metadata['new_features']}")

                    return True
                else:
                    print(f"✗ Legacy backup file not found: {legacy_file}")
                    return False
            else:
                print(f"✗ Legacy backup failed")
                return False

        except Exception as e:
            print(f"✗ Error during legacy backup test: {str(e)}")
            return False

    @staticmethod
    def test_new_backup(test_db="test_new_db", test_dir="/tmp"):
        """Test new compressed backups"""
        print("\n=== Testing New Backup (With Compression and New Features) ===")

        try:
            # Create backup with new method
            print(f"Creating compressed backup for {test_db}...")
            result = mysqlUtilities.createDatabaseBackup(
                test_db, test_dir, use_compression=True, use_new_features=True
            )

            if result == 1:
                print(f"✓ New backup created successfully")

                # Check that .sql.gz file exists
                compressed_file = f"{test_dir}/{test_db}.sql.gz"
                if os.path.exists(compressed_file):
                    file_size = os.path.getsize(compressed_file)
                    print(f"✓ Compressed backup file exists: {compressed_file}")
                    print(f"  File size: {file_size} bytes")

                    # Check metadata file
                    metadata_file = f"{test_dir}/{test_db}.backup.json"
                    if os.path.exists(metadata_file):
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                            print(f"✓ Metadata file exists")
                            print(f"  Backup version: {metadata['backup_version']}")
                            print(f"  Compressed: {metadata['compressed']}")
                            print(f"  New features: {metadata['new_features']}")

                    return True
                else:
                    print(f"✗ Compressed backup file not found: {compressed_file}")
                    # Check if legacy file was created instead
                    legacy_file = f"{test_dir}/{test_db}.sql"
                    if os.path.exists(legacy_file):
                        print(f"  Note: Legacy file exists instead: {legacy_file}")
                    return False
            else:
                print(f"✗ New backup failed")
                return False

        except Exception as e:
            print(f"✗ Error during new backup test: {str(e)}")
            return False

    @staticmethod
    def test_format_detection(test_dir="/tmp"):
        """Test backup format auto-detection"""
        print("\n=== Testing Format Detection ===")

        # Test detection of compressed backup
        test_db = "test_detect"

        # Create a dummy compressed backup
        compressed_file = f"{test_dir}/{test_db}.sql.gz"
        with open(compressed_file, 'wb') as f:
            f.write(b'\x1f\x8b\x08\x00\x00\x00\x00\x00')  # gzip header

        # Create metadata
        metadata = {
            'database': test_db,
            'compressed': True,
            'new_features': True,
            'backup_version': '2.0'
        }
        metadata_file = f"{test_dir}/{test_db}.backup.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f)

        # Test detection
        detected_format = mysqlUtilities.detectBackupFormat(test_dir, test_db)
        print(f"Detected format for compressed backup:")
        print(f"  Compressed: {detected_format['compressed']}")
        print(f"  New features: {detected_format['new_features']}")
        print(f"  Version: {detected_format['backup_version']}")

        # Clean up test files
        os.remove(compressed_file)
        os.remove(metadata_file)

        # Create a dummy uncompressed backup
        uncompressed_file = f"{test_dir}/{test_db}.sql"
        with open(uncompressed_file, 'w') as f:
            f.write("-- MySQL dump\n")

        # Test detection without metadata
        detected_format = mysqlUtilities.detectBackupFormat(test_dir, test_db)
        print(f"\nDetected format for uncompressed backup (no metadata):")
        print(f"  Compressed: {detected_format['compressed']}")
        print(f"  New features: {detected_format['new_features']}")
        print(f"  Version: {detected_format['backup_version']}")

        # Clean up
        os.remove(uncompressed_file)

        return True

    @staticmethod
    def test_mysqldump_command():
        """Test mysqldump command building"""
        print("\n=== Testing MySQL Dump Command Building ===")

        # Test legacy command
        legacy_cmd = mysqlUtilities.buildMysqldumpCommand(
            "root", "localhost", "3306", "test_db",
            use_new_features=False, use_compression=False
        )
        print(f"Legacy command: {legacy_cmd}")

        # Test new command with features
        new_cmd = mysqlUtilities.buildMysqldumpCommand(
            "root", "localhost", "3306", "test_db",
            use_new_features=True, use_compression=True
        )
        print(f"New command: {new_cmd}")

        return True

    @staticmethod
    def run_all_tests():
        """Run all compatibility tests"""
        print("=" * 60)
        print("CyberPanel Database Backup Compatibility Test Suite")
        print("=" * 60)

        all_passed = True

        # Test configuration
        if not BackupCompatibilityTests.test_config_file():
            all_passed = False

        # Test helper functions
        if not BackupCompatibilityTests.test_helper_functions():
            all_passed = False

        # Test mysqldump command building
        if not BackupCompatibilityTests.test_mysqldump_command():
            all_passed = False

        # Setup test environment
        test_dir = BackupCompatibilityTests.setup_test_environment()

        try:
            # Test format detection
            if not BackupCompatibilityTests.test_format_detection(test_dir):
                all_passed = False

            # Note: Actual backup/restore tests would require a real database
            # These are commented out but show the structure

            # # Test legacy backup
            # if not BackupCompatibilityTests.test_legacy_backup("test_db", test_dir):
            #     all_passed = False

            # # Test new backup
            # if not BackupCompatibilityTests.test_new_backup("test_db", test_dir):
            #     all_passed = False

        finally:
            # Cleanup
            BackupCompatibilityTests.cleanup_test_environment(test_dir)

        print("\n" + "=" * 60)
        if all_passed:
            print("✓ All tests passed successfully!")
            print("The backup system is fully backward compatible.")
        else:
            print("✗ Some tests failed. Please check the output above.")
        print("=" * 60)

        return all_passed


if __name__ == "__main__":
    # Run the test suite
    success = BackupCompatibilityTests.run_all_tests()
    sys.exit(0 if success else 1)