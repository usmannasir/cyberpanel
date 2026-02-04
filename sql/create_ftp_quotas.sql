-- Create ftp_quotas table for FTP Quota Management (websiteFunctions.models.FTPQuota)
-- Run once per CyberPanel database. Safe to run: uses IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS `ftp_quotas` (
    `id` INT AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `user_id` INT NOT NULL,
    `ftp_user` VARCHAR(255) NOT NULL,
    `domain_id` INT NULL,
    `quota_size_mb` INT NOT NULL DEFAULT 0,
    `quota_used_mb` INT NOT NULL DEFAULT 0,
    `quota_files` INT NOT NULL DEFAULT 0,
    `quota_files_used` INT NOT NULL DEFAULT 0,
    `is_active` TINYINT(1) NOT NULL DEFAULT 1,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    UNIQUE KEY `ftp_quotas_ftp_user_unique` (`ftp_user`),
    KEY `ftp_quotas_user_id` (`user_id`),
    KEY `ftp_quotas_domain_id` (`domain_id`),
    CONSTRAINT `ftp_quotas_user_id_fk` FOREIGN KEY (`user_id`) REFERENCES `loginSystem_administrator` (`id`) ON DELETE CASCADE,
    CONSTRAINT `ftp_quotas_domain_id_fk` FOREIGN KEY (`domain_id`) REFERENCES `websiteFunctions_websites` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
