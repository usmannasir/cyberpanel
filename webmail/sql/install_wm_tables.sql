-- CyberPanel Webmail: create wm_* tables when Django migration graph cannot run
-- (e.g. dockerManager depends on loginSystem migrations that do not exist).
-- Safe to run multiple times (CREATE TABLE IF NOT EXISTS).

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS `wm_contacts` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `owner_email` varchar(200) NOT NULL,
  `display_name` varchar(200) NOT NULL DEFAULT '',
  `email_address` varchar(200) NOT NULL,
  `phone` varchar(50) NOT NULL DEFAULT '',
  `organization` varchar(200) NOT NULL DEFAULT '',
  `notes` longtext NOT NULL,
  `is_auto_collected` tinyint(1) NOT NULL DEFAULT 0,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `wm_contacts_owner_email_unique` (`owner_email`,`email_address`),
  KEY `wm_contacts_owner_email_idx` (`owner_email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `wm_contact_groups` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `owner_email` varchar(200) NOT NULL,
  `name` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `wm_contact_groups_owner_email_name_unique` (`owner_email`,`name`),
  KEY `wm_contact_groups_owner_email_idx` (`owner_email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `wm_contact_group_members` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `contact_id` bigint(20) NOT NULL,
  `group_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `wm_cgm_contact_group_unique` (`contact_id`,`group_id`),
  KEY `wm_cgm_contact_fk` (`contact_id`),
  KEY `wm_cgm_group_fk` (`group_id`),
  CONSTRAINT `wm_cgm_contact_fk` FOREIGN KEY (`contact_id`) REFERENCES `wm_contacts` (`id`) ON DELETE CASCADE,
  CONSTRAINT `wm_cgm_group_fk` FOREIGN KEY (`group_id`) REFERENCES `wm_contact_groups` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `wm_sessions` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `session_key` varchar(64) NOT NULL,
  `email_account` varchar(200) NOT NULL,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `last_active` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `wm_sessions_session_key_unique` (`session_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `wm_settings` (
  `email_account` varchar(200) NOT NULL,
  `display_name` varchar(200) NOT NULL DEFAULT '',
  `signature_html` longtext NOT NULL,
  `messages_per_page` int(11) NOT NULL DEFAULT 25,
  `default_reply_behavior` varchar(20) NOT NULL DEFAULT 'reply',
  `theme_preference` varchar(20) NOT NULL DEFAULT 'auto',
  `auto_collect_contacts` tinyint(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`email_account`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `wm_sieve_rules` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `email_account` varchar(200) NOT NULL,
  `name` varchar(200) NOT NULL,
  `priority` int(11) NOT NULL DEFAULT 0,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `condition_field` varchar(50) NOT NULL,
  `condition_type` varchar(50) NOT NULL,
  `condition_value` varchar(500) NOT NULL,
  `action_type` varchar(50) NOT NULL,
  `action_value` varchar(500) NOT NULL DEFAULT '',
  `sieve_script` longtext NOT NULL,
  PRIMARY KEY (`id`),
  KEY `wm_sieve_rules_email_account_idx` (`email_account`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
