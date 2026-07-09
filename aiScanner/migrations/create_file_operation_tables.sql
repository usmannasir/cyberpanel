-- AI Scanner File Operations Audit Tables
-- These tables track file operations performed by the scanner for security and auditing

-- Drop tables if they exist (use with caution in production)
-- DROP TABLE IF EXISTS scanner_file_operations;
-- DROP TABLE IF EXISTS scanner_api_rate_limits;

-- Table: scanner_file_operations
-- Tracks all file operations (backup, read, replace, rename, delete)
CREATE TABLE IF NOT EXISTS scanner_file_operations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    scan_id VARCHAR(255) NOT NULL,
    operation VARCHAR(20) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    backup_path VARCHAR(500) NULL,
    success BOOLEAN NOT NULL DEFAULT FALSE,
    error_message TEXT NULL,
    ip_address VARCHAR(45) NULL,
    user_agent VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_scan_id (scan_id),
    INDEX idx_created_at (created_at),
    INDEX idx_scan_created (scan_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Table: scanner_api_rate_limits
-- Rate limiting for scanner API endpoints
CREATE TABLE IF NOT EXISTS scanner_api_rate_limits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    scan_id VARCHAR(255) NOT NULL,
    endpoint VARCHAR(100) NOT NULL,
    request_count INT NOT NULL DEFAULT 0,
    last_request_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_scan_endpoint (scan_id, endpoint),
    INDEX idx_scan_endpoint (scan_id, endpoint)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Show created tables
SHOW TABLES LIKE 'scanner_%';

-- Show table structures
DESCRIBE scanner_file_operations;
DESCRIBE scanner_api_rate_limits;
