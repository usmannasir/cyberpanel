# CyberPanel OpenLiteSpeed Module - Complete Usage Guide

**Version:** 2.2.0
**Last Updated:** December 28, 2025
**Status:** Production Ready

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Header Directives](#1-header-directives)
3. [Request Header Directives](#2-request-header-directives)
4. [Environment Variables](#3-environment-variables)
5. [Access Control](#4-access-control)
6. [Redirect Directives](#5-redirect-directives)
7. [Error Documents](#6-error-documents)
8. [FilesMatch Directives](#7-filesmatch-directives)
9. [Expires Directives](#8-expires-directives)
10. [PHP Directives](#9-php-directives)
11. [Brute Force Protection](#10-brute-force-protection)
12. [CyberPanel Integration](#cyberpanel-integration)
13. [Real-World Examples](#real-world-examples)
14. [Troubleshooting](#troubleshooting)

---

## Getting Started

### What is This Module?

The CyberPanel OpenLiteSpeed Module brings Apache .htaccess compatibility to OpenLiteSpeed servers. It allows you to use familiar Apache directives without switching web servers.

### Quick Start

1. **Module is pre-installed** on CyberPanel servers
2. **Create .htaccess** in your website's public_html directory
3. **Add directives** from this guide
4. **Test** using curl or browser

### Basic .htaccess Example

```apache
# Security headers
Header set X-Frame-Options "SAMEORIGIN"
Header set X-Content-Type-Options "nosniff"

# Enable brute force protection
BruteForceProtection On
```

---

## 1. Header Directives

### What Are HTTP Headers?

HTTP headers are metadata sent with web responses. They control browser behavior, caching, security, and more.

### Supported Operations

| Operation | Purpose | Syntax |
|-----------|---------|--------|
| **set** | Set header (replaces existing) | `Header set Name "Value"` |
| **unset** | Remove header | `Header unset Name` |
| **append** | Append to existing header | `Header append Name "Value"` |
| **merge** | Add if not present | `Header merge Name "Value"` |
| **add** | Always add (allows duplicates) | `Header add Name "Value"` |

### How to Use

#### Basic Security Headers

**What it does:** Protects against clickjacking, XSS, and MIME sniffing.

```apache
# Prevent site from being embedded in iframe (clickjacking protection)
Header set X-Frame-Options "SAMEORIGIN"

# Prevent MIME type sniffing
Header set X-Content-Type-Options "nosniff"

# Enable XSS filter in browsers
Header set X-XSS-Protection "1; mode=block"

# Control referrer information
Header set Referrer-Policy "strict-origin-when-cross-origin"

# Restrict browser features
Header set Permissions-Policy "geolocation=(), microphone=(), camera=()"
```

**Testing:**
```bash
curl -I https://yourdomain.com | grep -E "X-Frame|X-Content|X-XSS"
```

#### Cache Control Headers

**What it does:** Controls how browsers cache your content.

```apache
# Cache for 1 year (static assets)
Header set Cache-Control "max-age=31536000, public, immutable"

# No caching (dynamic content)
Header set Cache-Control "no-cache, no-store, must-revalidate"
Header set Pragma "no-cache"
Header set Expires "0"

# Cache for 1 hour
Header set Cache-Control "max-age=3600, public"
```

**Testing:**
```bash
curl -I https://yourdomain.com/style.css | grep Cache-Control
```

#### CORS Headers

**What it does:** Allows cross-origin requests (needed for APIs, fonts, n8n, etc.).

```apache
# Allow all origins
Header set Access-Control-Allow-Origin "*"

# Allow specific origin
Header set Access-Control-Allow-Origin "https://app.example.com"

# Allow specific methods
Header set Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS"

# Allow specific headers
Header set Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With"

# Allow credentials
Header set Access-Control-Allow-Credentials "true"

# Preflight cache duration
Header set Access-Control-Max-Age "86400"
```

**Testing:**
```bash
curl -I -H "Origin: https://example.com" https://yourdomain.com/api
```

#### Remove Server Identification

**What it does:** Hides server information from attackers.

```apache
Header unset Server
Header unset X-Powered-By
Header unset X-LiteSpeed-Tag
```

**Testing:**
```bash
curl -I https://yourdomain.com | grep -E "Server|X-Powered"
# Should return nothing
```

### CyberPanel Integration

#### Via File Manager

1. Log into **CyberPanel**
2. Go to **File Manager**
3. Navigate to `/home/yourdomain.com/public_html`
4. Create or edit `.htaccess`
5. Add header directives
6. Save and test

#### Via SSH

```bash
# Navigate to website directory
cd /home/yourdomain.com/public_html

# Edit .htaccess
nano .htaccess

# Add your headers
Header set X-Frame-Options "SAMEORIGIN"

# Save (Ctrl+X, Y, Enter)

# Test
curl -I https://yourdomain.com | grep X-Frame
```

### Common Use Cases

#### WordPress Security Headers

```apache
# WordPress-specific security
Header set X-Frame-Options "SAMEORIGIN"
Header set X-Content-Type-Options "nosniff"
Header set X-XSS-Protection "1; mode=block"
Header set Referrer-Policy "strict-origin-when-cross-origin"
Header unset X-Powered-By

# Disable XML-RPC header
Header unset X-Pingback
```

#### n8n CORS Configuration

```apache
# Allow n8n webhooks
Header set Access-Control-Allow-Origin "https://your-n8n-instance.com"
Header set Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS"
Header set Access-Control-Allow-Headers "Content-Type, Authorization"
Header set Access-Control-Allow-Credentials "true"
```

#### API Response Headers

```apache
# JSON API headers
Header set Content-Type "application/json; charset=utf-8"
Header set X-Content-Type-Options "nosniff"
Header set Access-Control-Allow-Origin "*"
Header set Cache-Control "no-cache, no-store, must-revalidate"
```

---

## 2. Request Header Directives

### What Are Request Headers?

Request headers are sent FROM the client TO the server. This feature lets you modify or add headers before they reach your PHP application.

### How It Works

Since OpenLiteSpeed's LSIAPI doesn't support direct request header modification, these are implemented as **environment variables** accessible in PHP via `$_SERVER`.

### Supported Operations

| Operation | Syntax | Result |
|-----------|--------|--------|
| **set** | `RequestHeader set Name "Value"` | `$_SERVER['HTTP_NAME']` |
| **unset** | `RequestHeader unset Name` | Header removed |

### How to Use

#### SSL/HTTPS Detection (Behind Proxy)

**What it does:** Tells your application the request came via HTTPS (when behind Cloudflare, nginx proxy, etc.).

```apache
# Set HTTPS protocol headers
RequestHeader set X-Forwarded-Proto "https"
RequestHeader set X-Forwarded-SSL "on"
RequestHeader set X-Real-IP "%{REMOTE_ADDR}e"
```

**PHP Usage:**
```php
<?php
// Detect HTTPS
$proto = $_SERVER['HTTP_X_FORWARDED_PROTO'] ?? 'http';
$isHttps = ($proto === 'https');

// Get real IP
$realIp = $_SERVER['HTTP_X_REAL_IP'] ?? $_SERVER['REMOTE_ADDR'];

// Force HTTPS redirect
if (!$isHttps && $_SERVER['REQUEST_METHOD'] !== 'OPTIONS') {
    header('Location: https://' . $_SERVER['HTTP_HOST'] . $_SERVER['REQUEST_URI']);
    exit;
}
?>
```

#### Application Environment Identification

**What it does:** Tags requests with environment information.

```apache
# Identify environment
RequestHeader set X-Environment "production"
RequestHeader set X-Server-Location "us-east-1"
RequestHeader set X-Request-Start "%{REQUEST_TIME}e"
```

**PHP Usage:**
```php
<?php
$env = $_SERVER['HTTP_X_ENVIRONMENT'] ?? 'development';
$location = $_SERVER['HTTP_X_SERVER_LOCATION'] ?? 'unknown';

if ($env === 'production') {
    ini_set('display_errors', 0);
    error_reporting(E_ALL & ~E_DEPRECATED);
}
?>
```

#### Custom Backend Headers

**What it does:** Passes custom information to your application.

```apache
# Custom application headers
RequestHeader set X-API-Version "v2"
RequestHeader set X-Feature-Flags "new-ui,beta-features"
RequestHeader set X-Client-Type "web"
```

**PHP Usage:**
```php
<?php
$apiVersion = $_SERVER['HTTP_X_API_VERSION'] ?? 'v1';
$features = explode(',', $_SERVER['HTTP_X_FEATURE_FLAGS'] ?? '');
$clientType = $_SERVER['HTTP_X_CLIENT_TYPE'] ?? 'unknown';

if (in_array('beta-features', $features)) {
    // Enable beta features
}
?>
```

### CyberPanel Integration

#### For WordPress Behind Cloudflare

```apache
# In /home/yourdomain.com/public_html/.htaccess
RequestHeader set X-Forwarded-Proto "https"
RequestHeader set X-Forwarded-SSL "on"

# WordPress will now correctly detect HTTPS
```

**Verify in WordPress:**
```php
// Add to wp-config.php if needed
if ($_SERVER['HTTP_X_FORWARDED_PROTO'] === 'https') {
    $_SERVER['HTTPS'] = 'on';
}
```

### Common Use Cases

#### Cloudflare + WordPress

```apache
RequestHeader set X-Forwarded-Proto "https"
RequestHeader set X-Forwarded-SSL "on"
RequestHeader set X-Real-IP "%{REMOTE_ADDR}e"
```

#### Laravel Behind Load Balancer

```apache
RequestHeader set X-Forwarded-Proto "https"
RequestHeader set X-Forwarded-For "%{REMOTE_ADDR}e"
```

---

## 3. Environment Variables

### What Are Environment Variables?

Environment variables are key-value pairs accessible in your PHP application. They're useful for configuration, feature flags, and conditional logic.

### Supported Directives

| Directive | Purpose | Syntax |
|-----------|---------|--------|
| **SetEnv** | Set static variable | `SetEnv NAME value` |
| **SetEnvIf** | Conditional set (case-sensitive) | `SetEnvIf attribute regex VAR=value` |
| **SetEnvIfNoCase** | Conditional set (case-insensitive) | `SetEnvIfNoCase attribute regex VAR=value` |
| **BrowserMatch** | Detect browser | `BrowserMatch regex VAR=value` |

### How to Use

#### Static Configuration Variables

**What it does:** Sets application configuration accessible in PHP.

```apache
# Application settings
SetEnv APPLICATION_ENV production
SetEnv DB_HOST localhost
SetEnv DB_NAME myapp_db
SetEnv API_ENDPOINT https://api.example.com
SetEnv FEATURE_FLAG_NEW_UI enabled
SetEnv DEBUG_MODE off
```

**PHP Usage:**
```php
<?php
$env = $_SERVER['APPLICATION_ENV'] ?? 'development';
$dbHost = $_SERVER['DB_HOST'] ?? 'localhost';
$apiEndpoint = $_SERVER['API_ENDPOINT'] ?? '';
$newUiEnabled = ($_SERVER['FEATURE_FLAG_NEW_UI'] ?? 'off') === 'enabled';

if ($newUiEnabled) {
    require 'templates/new-ui.php';
} else {
    require 'templates/old-ui.php';
}
?>
```

#### Conditional Variables (SetEnvIf)

**What it does:** Sets variables based on request properties.

##### Supported Conditions

- `Request_URI` - URL path
- `Request_Method` - HTTP method (GET, POST, etc.)
- `User-Agent` - Browser/client identifier
- `Host` - Domain name
- `Referer` - Referrer URL
- `Query_String` - URL parameters
- `Remote_Addr` - Client IP address

**Examples:**

```apache
# Detect API requests
SetEnvIf Request_URI "^/api/" IS_API_REQUEST=1

# Detect POST requests
SetEnvIf Request_Method "POST" IS_POST_REQUEST=1

# Detect specific domain
SetEnvIf Host "^beta\." IS_BETA_SITE=1

# Detect search queries
SetEnvIf Query_String "search=" HAS_SEARCH=1

# Detect local development
SetEnvIf Remote_Addr "^127\.0\.0\.1$" IS_LOCAL=1
```

**PHP Usage:**
```php
<?php
if (!empty($_SERVER['IS_API_REQUEST'])) {
    header('Content-Type: application/json');
    $output = json_encode($data);
} else {
    header('Content-Type: text/html');
    $output = render_html($data);
}

if (!empty($_SERVER['IS_BETA_SITE'])) {
    // Enable experimental features
    define('BETA_FEATURES', true);
}
?>
```

#### Browser Detection

**What it does:** Identifies the user's browser for compatibility handling.

```apache
# Case-insensitive browser detection
SetEnvIfNoCase User-Agent "mobile|android|iphone|ipad" IS_MOBILE=1
SetEnvIfNoCase User-Agent "bot|crawler|spider|scraper" IS_BOT=1
SetEnvIfNoCase User-Agent "MSIE|Trident" IS_IE=1

# Specific browser matching
BrowserMatch "Chrome" IS_CHROME=1
BrowserMatch "Firefox" IS_FIREFOX=1
BrowserMatch "Safari" IS_SAFARI=1
BrowserMatch "Edge" IS_EDGE=1
```

**PHP Usage:**
```php
<?php
if (!empty($_SERVER['IS_MOBILE'])) {
    require 'mobile-layout.php';
} else {
    require 'desktop-layout.php';
}

if (!empty($_SERVER['IS_BOT'])) {
    // Serve cached version to bots
    serve_cached_page();
    exit;
}

if (!empty($_SERVER['IS_IE'])) {
    echo '<div class="browser-warning">Please use a modern browser</div>';
}
?>
```

### CyberPanel Integration

#### Environment-Specific Configuration

```apache
# In /home/yourdomain.com/public_html/.htaccess

# Production settings
SetEnv APPLICATION_ENV production
SetEnv DEBUG_MODE off
SetEnv CACHE_ENABLED on

# Database connection
SetEnv DB_HOST localhost
SetEnv DB_NAME wp_database

# Feature flags
SetEnv ENABLE_CDN on
SetEnv ENABLE_CACHE on
```

**WordPress Usage (wp-config.php):**
```php
<?php
// Use environment variables
define('WP_ENV', $_SERVER['APPLICATION_ENV'] ?? 'production');
define('WP_DEBUG', ($_SERVER['DEBUG_MODE'] ?? 'off') === 'on');

if (WP_DEBUG) {
    define('WP_DEBUG_LOG', true);
    define('WP_DEBUG_DISPLAY', true);
}
?>
```

### Common Use Cases

#### Mobile Detection + Redirect

```apache
# Detect mobile users
SetEnvIfNoCase User-Agent "mobile|android|iphone" IS_MOBILE=1

# Redirect mobile to subdomain (using PHP)
```

**PHP redirect:**
```php
<?php
if (!empty($_SERVER['IS_MOBILE']) && strpos($_SERVER['HTTP_HOST'], 'm.') !== 0) {
    header('Location: https://m.example.com' . $_SERVER['REQUEST_URI']);
    exit;
}
?>
```

#### API Rate Limiting Preparation

```apache
# Tag API requests
SetEnvIf Request_URI "^/api/" IS_API=1
SetEnvIf Request_Method "POST" IS_POST=1
```

**PHP rate limiting:**
```php
<?php
if (!empty($_SERVER['IS_API'])) {
    // Apply API rate limiting
    check_api_rate_limit($_SERVER['REMOTE_ADDR']);
}
?>
```

---

## 4. Access Control

### What is Access Control?

Access control restricts who can access your website based on IP addresses. Perfect for staging sites, admin panels, or development environments.

### Directives

| Directive | Syntax | Description |
|-----------|--------|-------------|
| **Order** | `Order deny,allow` or `Order allow,deny` | Set evaluation order |
| **Allow** | `Allow from IP/CIDR` | Allow specific IP |
| **Deny** | `Deny from IP/CIDR` | Deny specific IP |

### Supported IP Formats

- **Single IP:** `192.168.1.100`
- **CIDR Range:** `192.168.1.0/24` (entire subnet)
- **Large Ranges:** `10.0.0.0/8` (entire class)
- **IPv6:** `2001:db8::/32`
- **Wildcard:** `all` (everyone)

### How Order Works

#### Order deny,allow

1. Check **Deny** list first
2. Then check **Allow** list
3. **Allow overrides Deny**
4. Default: **DENY** if not in either list

```apache
Order deny,allow
Deny from all
Allow from 192.168.1.100
# Result: Only 192.168.1.100 can access
```

#### Order allow,deny

1. Check **Allow** list first
2. Then check **Deny** list
3. **Deny overrides Allow**
4. Default: **ALLOW** if not in either list

```apache
Order allow,deny
Allow from all
Deny from 192.168.1.100
# Result: Everyone except 192.168.1.100 can access
```

### How to Use

#### Block All Except Specific IPs (Recommended for Staging)

```apache
# Only allow office IP and VPN
Order deny,allow
Deny from all
Allow from 203.0.113.50      # Office IP
Allow from 192.168.1.0/24    # Office LAN
Allow from 10.8.0.0/24       # VPN range
```

**Use case:** Development/staging sites, admin areas

**Testing:**
```bash
# From allowed IP
curl https://staging.example.com
# Should work

# From other IP
curl https://staging.example.com
# Should get 403 Forbidden
```

#### Allow All Except Specific IPs

```apache
# Block known attackers
Order allow,deny
Allow from all
Deny from 198.51.100.50      # Banned IP
Deny from 203.0.113.0/24     # Banned subnet
```

**Use case:** Blocking spam IPs, attack sources

#### Protect Admin Directory

```apache
# In /home/yourdomain.com/public_html/admin/.htaccess
Order deny,allow
Deny from all
Allow from 192.168.1.0/24    # Office network
Allow from 203.0.113.100     # Your home IP
```

**Use case:** WordPress wp-admin protection

### CyberPanel Integration

#### Protect Staging Site

1. Create subdomain `staging.yourdomain.com` in CyberPanel
2. Navigate to `/home/staging.yourdomain.com/public_html`
3. Create `.htaccess`:

```apache
# Staging site - Office only
Order deny,allow
Deny from all
Allow from YOUR.OFFICE.IP.HERE
Allow from YOUR.HOME.IP.HERE
```

4. Test:
```bash
# Get your IP
curl ifconfig.me

# Test access
curl -I https://staging.yourdomain.com
# Should see 403 if not allowed
```

#### Protect WordPress Admin

```apache
# In /home/yourdomain.com/public_html/wp-admin/.htaccess
Order deny,allow
Deny from all
Allow from 203.0.113.50   # Your IP
```

**Important:** This creates TWO layers of protection:
1. IP restriction (from .htaccess)
2. Login authentication (from WordPress)

#### Protect CyberPanel Access

```apache
# In /usr/local/CyberCP/public/.htaccess (if web accessible)
Order deny,allow
Deny from all
Allow from 127.0.0.1         # localhost
Allow from 192.168.1.0/24    # Your network
```

### Common Use Cases

#### Development Environment

```apache
# Dev site - developers only
Order deny,allow
Deny from all
Allow from 192.168.1.0/24    # Office LAN
Allow from 10.8.0.0/24       # VPN
Allow from 203.0.113.50      # Lead developer home
```

#### Geographic Restriction

```apache
# Block specific countries (you need to maintain IP list)
Order allow,deny
Allow from all
Deny from 198.51.100.0/24    # Country X subnet
Deny from 203.0.113.0/24     # Country Y subnet
```

#### API Endpoint Protection

```apache
# In /home/yourdomain.com/public_html/api/.htaccess
Order deny,allow
Deny from all
Allow from 10.0.0.0/8        # Internal network
Allow from 172.16.0.0/12     # Private network
```

### Troubleshooting

**Problem:** Getting 403 even from allowed IP

**Solution:**
1. Check your actual IP: `curl ifconfig.me`
2. Verify CIDR: `192.168.1.0/24` covers `192.168.1.1` to `192.168.1.254`
3. Check logs: `tail -f /usr/local/lsws/logs/error.log`

**Problem:** Access control not working

**Solution:**
1. Verify module loaded: `ls -la /usr/local/lsws/modules/cyberpanel_ols.so`
2. Check .htaccess permissions: `chmod 644 .htaccess`
3. Restart OpenLiteSpeed: `/usr/local/lsws/bin/lswsctrl restart`

---

## 5. Redirect Directives

### What Are Redirects?

Redirects tell browsers to go to a different URL. Essential for SEO, site migrations, and URL structure changes.

### Directives

| Directive | Syntax | Use Case |
|-----------|--------|----------|
| **Redirect** | `Redirect [code] /old /new` | Simple path redirects |
| **RedirectMatch** | `RedirectMatch [code] regex target` | Pattern-based redirects |

### Status Codes

| Code | Name | When to Use |
|------|------|-------------|
| **301** | Permanent | SEO-friendly, URL has moved forever |
| **302** | Temporary | URL temporarily moved, may change back |
| **303** | See Other | Redirect after POST (form submission) |
| **410** | Gone | Resource permanently deleted |

### How to Use

#### Simple Redirects

**What it does:** Redirects one path to another.

```apache
# Old page to new page
Redirect 301 /old-page.html /new-page.html

# Old directory to new directory
Redirect 301 /old-blog /blog

# Use keywords instead of codes
Redirect permanent /old-url /new-url
Redirect temp /maintenance /coming-soon
```

**Testing:**
```bash
curl -I https://yourdomain.com/old-page.html
# Should show: HTTP/1.1 301 Moved Permanently
# Location: https://yourdomain.com/new-page.html
```

#### Force HTTPS

**What it does:** Redirects HTTP to HTTPS.

```apache
# Redirect HTTP to HTTPS
Redirect 301 / https://yourdomain.com/
```

**Better Alternative (checks if already HTTPS):**
```apache
SetEnvIf Request_URI ".*" IS_HTTP=1
# Use with PHP to avoid redirect loop
```

**PHP solution:**
```php
<?php
if ($_SERVER['REQUEST_SCHEME'] !== 'https') {
    header('Location: https://' . $_SERVER['HTTP_HOST'] . $_SERVER['REQUEST_URI'], true, 301);
    exit;
}
?>
```

#### Force WWW or Non-WWW

**What it does:** Standardizes domain format for SEO.

```apache
# Force www
Redirect 301 / https://www.yourdomain.com/

# Force non-www (use RedirectMatch)
RedirectMatch 301 ^(.*)$ https://yourdomain.com$1
```

#### Pattern-Based Redirects (RedirectMatch)

**What it does:** Uses regex to match and redirect URLs.

```apache
# Blog restructuring
RedirectMatch 301 ^/blog/(.*)$ /news/$1
# /blog/post-1 → /news/post-1

# Product ID migration
RedirectMatch 301 ^/product-([0-9]+)$ /item/$1
# /product-123 → /item/123

# Year/month/title to title
RedirectMatch 301 ^/blog/([0-9]{4})/([0-9]{2})/(.*)$ /articles/$3
# /blog/2024/12/my-post → /articles/my-post

# Category reorganization
RedirectMatch 301 ^/category/(.*)$ /topics/$1
```

**Testing:**
```bash
curl -I https://yourdomain.com/blog/my-post
# Should redirect to /news/my-post
```

### CyberPanel Integration

#### Site Migration (Old Domain to New)

```apache
# In old site's .htaccess
Redirect 301 / https://new-domain.com/
```

**Steps:**
1. Keep old domain active in CyberPanel
2. Add redirect to `/home/old-domain.com/public_html/.htaccess`
3. Monitor traffic migration
4. After 6 months, can delete old domain

#### WordPress Permalink Change

**Scenario:** Changed permalinks from `/?p=123` to `/blog/post-title`

```apache
# WordPress handles this automatically, but for custom:
RedirectMatch 301 ^/\?p=([0-9]+)$ /blog/post-$1
```

#### E-commerce URL Update

```apache
# Old: /products/view/123
# New: /shop/product-123

RedirectMatch 301 ^/products/view/([0-9]+)$ /shop/product-$1
```

### Common Use Cases

#### Complete Site Redesign

```apache
# Redirect old structure to new
RedirectMatch 301 ^/about-us$ /about
RedirectMatch 301 ^/contact-us$ /contact
RedirectMatch 301 ^/services/(.*)$ /solutions/$1
RedirectMatch 301 ^/blog/(.*)$ /news/$1
```

#### Affiliate Link Management

```apache
# Short URLs for affiliate links
Redirect 302 /go/amazon https://amazon.com/your-affiliate-link
Redirect 302 /go/product https://example.com/long-url-here
```

#### Seasonal Campaigns

```apache
# Temporary campaign redirect
Redirect 302 /sale /christmas-sale-2025
Redirect 302 /promo /black-friday
```

#### Remove .html Extensions (SEO)

```apache
# Old: /page.html
# New: /page

RedirectMatch 301 ^/(.*)/index\.html$ /$1/
RedirectMatch 301 ^/(.*)[^/]\.html$ /$1
```

### Troubleshooting

**Problem:** Redirect loop

**Solution:** Check for conflicting rules:
```apache
# BAD - Creates loop
Redirect 301 / https://example.com/
Redirect 301 / https://www.example.com/

# GOOD - Use one or the other
Redirect 301 / https://www.example.com/
```

**Problem:** Redirect not working

**Solution:**
1. Clear browser cache (redirects are cached!)
2. Test with curl: `curl -I https://yoursite.com/old-page`
3. Check .htaccess syntax
4. Restart OpenLiteSpeed

---

## 6. Error Documents

### What Are Error Documents?

Custom error pages shown when errors occur (404 Not Found, 500 Internal Server Error, etc.).

### Supported Error Codes

| Code | Error | When It Happens |
|------|-------|-----------------|
| **400** | Bad Request | Malformed request |
| **401** | Unauthorized | Authentication required |
| **403** | Forbidden | Access denied |
| **404** | Not Found | Page doesn't exist |
| **500** | Internal Server Error | Server-side error |
| **502** | Bad Gateway | Proxy/backend error |
| **503** | Service Unavailable | Server overloaded/maintenance |

### Syntax

```apache
ErrorDocument <code> <document>
```

### How to Use

#### HTML Error Pages

**What it does:** Shows custom-designed error pages.

```apache
# Custom error pages
ErrorDocument 404 /errors/404.html
ErrorDocument 500 /errors/500.html
ErrorDocument 403 /errors/403.html
ErrorDocument 503 /errors/maintenance.html
```

**Create error pages:**

```bash
mkdir -p /home/yourdomain.com/public_html/errors
```

**404.html example:**
```html
<!DOCTYPE html>
<html>
<head>
    <title>Page Not Found</title>
    <style>
        body { font-family: Arial; text-align: center; padding: 50px; }
        h1 { color: #e74c3c; }
    </style>
</head>
<body>
    <h1>404 - Page Not Found</h1>
    <p>The page you're looking for doesn't exist.</p>
    <a href="/">Go to Homepage</a>
</body>
</html>
```

**Testing:**
```bash
curl https://yourdomain.com/nonexistent-page
# Should show your custom 404 page
```

#### Inline Messages

**What it does:** Shows simple text message.

```apache
ErrorDocument 403 "Access Denied - Contact Administrator"
ErrorDocument 404 "Page Not Found - Please check the URL"
```

#### WordPress-Friendly Error Pages

**What it does:** Routes errors through WordPress.

```apache
# Let WordPress handle 404s
ErrorDocument 404 /index.php?error=404
```

**WordPress theme (404.php):**
```php
<?php
// Custom 404 page design
get_header();
?>
<h1>Page Not Found</h1>
<p>Sorry, this page doesn't exist.</p>
<?php
get_footer();
?>
```

### CyberPanel Integration

#### Setup Custom Error Pages

**Step 1:** Create error directory
```bash
cd /home/yourdomain.com/public_html
mkdir errors
cd errors
```

**Step 2:** Create error page files
```bash
nano 404.html
# Add custom HTML
# Save (Ctrl+X, Y, Enter)

nano 500.html
# Add custom HTML
# Save
```

**Step 3:** Configure .htaccess
```apache
# In /home/yourdomain.com/public_html/.htaccess
ErrorDocument 404 /errors/404.html
ErrorDocument 500 /errors/500.html
ErrorDocument 403 /errors/403.html
```

**Step 4:** Test
```bash
curl https://yourdomain.com/test-404
```

#### Maintenance Page

```apache
# During maintenance
ErrorDocument 503 /maintenance.html
```

**maintenance.html:**
```html
<!DOCTYPE html>
<html>
<head>
    <title>Maintenance</title>
    <meta http-equiv="refresh" content="30">
    <style>
        body { font-family: Arial; text-align: center; padding: 100px; }
        h1 { color: #3498db; }
    </style>
</head>
<body>
    <h1>We'll be right back!</h1>
    <p>Our site is undergoing maintenance.</p>
    <p>Expected completion: 2 hours</p>
</body>
</html>
```

**Trigger maintenance mode:**
```bash
# Temporarily disable PHP
mv index.php index.php.bak
# Site will show 503
```

### Common Use Cases

#### Professional 404 Page with Search

**404.html:**
```html
<!DOCTYPE html>
<html>
<head>
    <title>Page Not Found</title>
</head>
<body>
    <h1>404 - Page Not Found</h1>
    <p>Try searching:</p>
    <form action="/search" method="get">
        <input type="text" name="q" placeholder="Search...">
        <button>Search</button>
    </form>
    <p><a href="/">Return to Homepage</a></p>
</body>
</html>
```

#### Branded Error Pages

```apache
ErrorDocument 400 /errors/400.html
ErrorDocument 401 /errors/401.html
ErrorDocument 403 /errors/403.html
ErrorDocument 404 /errors/404.html
ErrorDocument 500 /errors/500.html
ErrorDocument 502 /errors/502.html
ErrorDocument 503 /errors/503.html
```

Each page styled with your brand colors, logo, navigation.

---

## 7. FilesMatch Directives

### What is FilesMatch?

FilesMatch applies directives only to files matching a regex pattern. Perfect for caching strategies, security headers per file type.

### Syntax

```apache
<FilesMatch "regex">
    # Directives here apply only to matching files
    Header set Name "Value"
</FilesMatch>
```

### Common File Patterns

| Pattern | Matches |
|---------|---------|
| `\.(jpg\|png\|gif)$` | Images |
| `\.(css\|js)$` | Stylesheets and JavaScript |
| `\.(woff2?\|ttf\|eot)$` | Fonts |
| `\.(pdf\|doc\|docx)$` | Documents |
| `\.(html\|php)$` | Dynamic pages |
| `\.json$` | JSON files |

### How to Use

#### Cache Static Assets (Performance Boost)

**What it does:** Tells browsers to cache images/fonts for a long time.

```apache
# Images - Cache for 1 year
<FilesMatch "\.(jpg|jpeg|png|gif|webp|svg|ico)$">
    Header set Cache-Control "max-age=31536000, public, immutable"
    Header unset ETag
    Header unset Last-Modified
</FilesMatch>

# Fonts - Cache for 1 year
<FilesMatch "\.(woff2?|ttf|eot|otf)$">
    Header set Cache-Control "max-age=31536000, public, immutable"
    Header set Access-Control-Allow-Origin "*"
</FilesMatch>

# CSS/JS - Cache for 1 week (you update these more often)
<FilesMatch "\.(css|js)$">
    Header set Cache-Control "max-age=604800, public"
</FilesMatch>
```

**Testing:**
```bash
curl -I https://yourdomain.com/logo.png | grep Cache-Control
# Should show: Cache-Control: max-age=31536000, public, immutable
```

**Performance Impact:**
- First visit: Downloads all files
- Return visits: Loads from browser cache (instant!)
- Page load time: -50% to -80%

#### Security Headers for HTML/PHP

**What it does:** Applies security headers only to pages (not images).

```apache
<FilesMatch "\.(html|htm|php)$">
    Header set X-Frame-Options "SAMEORIGIN"
    Header set X-Content-Type-Options "nosniff"
    Header set X-XSS-Protection "1; mode=block"
    Header set Referrer-Policy "strict-origin-when-cross-origin"
</FilesMatch>
```

#### Prevent Caching of Dynamic Content

**What it does:** Ensures dynamic pages are never cached.

```apache
<FilesMatch "\.(html|php|json|xml)$">
    Header set Cache-Control "no-cache, no-store, must-revalidate"
    Header set Pragma "no-cache"
    Header set Expires "0"
</FilesMatch>
```

#### CORS for Fonts (Fix Font Loading)

**What it does:** Allows fonts to load from CDN or different domain.

```apache
<FilesMatch "\.(woff2?|ttf|eot|otf)$">
    Header set Access-Control-Allow-Origin "*"
</FilesMatch>
```

**Use case:** Fixes "Font from origin has been blocked by CORS policy" errors.

#### Download Headers for Files

**What it does:** Forces download instead of displaying in browser.

```apache
<FilesMatch "\.(pdf|zip|tar|gz|doc|docx|xls|xlsx)$">
    Header set Content-Disposition "attachment"
    Header set X-Content-Type-Options "nosniff"
</FilesMatch>
```

### CyberPanel Integration

#### WordPress Performance Optimization

```apache
# In /home/yourdomain.com/public_html/.htaccess

# Cache WordPress static assets
<FilesMatch "\.(jpg|jpeg|png|gif|webp|svg|ico)$">
    Header set Cache-Control "max-age=31536000, public, immutable"
</FilesMatch>

# Cache CSS/JS (with version strings in WordPress)
<FilesMatch "\.(css|js)$">
    Header set Cache-Control "max-age=2592000, public"
</FilesMatch>

# Don't cache WordPress admin
<FilesMatch "(wp-login|wp-admin|wp-cron)\.php$">
    Header set Cache-Control "no-cache, no-store, must-revalidate"
</FilesMatch>
```

**Result:** PageSpeed score +20-30 points

#### WooCommerce Security

```apache
# Protect sensitive files
<FilesMatch "(\.log|\.sql|\.md|readme\.txt|license\.txt)$">
    Order deny,allow
    Deny from all
</FilesMatch>

# JSON API security
<FilesMatch "\.json$">
    Header set X-Content-Type-Options "nosniff"
    Header set Content-Type "application/json; charset=utf-8"
</FilesMatch>
```

### Common Use Cases

#### Complete Caching Strategy

```apache
# Aggressive caching for static assets (1 year)
<FilesMatch "\.(jpg|jpeg|png|gif|webp|svg|ico|woff2?|ttf|eot|otf)$">
    Header set Cache-Control "max-age=31536000, public, immutable"
    Header unset ETag
</FilesMatch>

# Moderate caching for CSS/JS (1 month)
<FilesMatch "\.(css|js)$">
    Header set Cache-Control "max-age=2592000, public"
</FilesMatch>

# Short caching for HTML (1 hour)
<FilesMatch "\.html$">
    Header set Cache-Control "max-age=3600, public"
</FilesMatch>

# No caching for dynamic content
<FilesMatch "\.(php|json)$">
    Header set Cache-Control "no-cache, must-revalidate"
</FilesMatch>
```

#### Media Library Protection

```apache
# Prevent hotlinking (bandwidth theft)
<FilesMatch "\.(jpg|jpeg|png|gif)$">
    SetEnvIf Referer "^https://yourdomain\.com" local_ref
    SetEnvIf Referer "^$" local_ref
    Order deny,allow
    Deny from all
    Allow from env=local_ref
</FilesMatch>
```

---

## 8. Expires Directives

### What is mod_expires?

Alternative syntax for setting cache expiration. More concise than Cache-Control headers.

### Directives

```apache
ExpiresActive On
ExpiresByType mime-type base+seconds
```

### Time Bases

- **A** = Access time (when user requests file)
- **M** = Modification time (when file was last modified)

### Common Durations

| Duration | Seconds | Example |
|----------|---------|---------|
| 1 minute | 60 | `A60` |
| 1 hour | 3600 | `A3600` |
| 1 day | 86400 | `A86400` |
| 1 week | 604800 | `A604800` |
| 1 month | 2592000 | `A2592000` |
| 1 year | 31557600 | `A31557600` |

### How to Use

#### Complete Expiration Strategy

```apache
# Enable module
ExpiresActive On

# Images - 1 year
ExpiresByType image/jpeg A31557600
ExpiresByType image/png A31557600
ExpiresByType image/gif A31557600
ExpiresByType image/webp A31557600
ExpiresByType image/svg+xml A31557600
ExpiresByType image/x-icon A31557600

# CSS and JavaScript - 1 month
ExpiresByType text/css A2592000
ExpiresByType application/javascript A2592000
ExpiresByType application/x-javascript A2592000
ExpiresByType text/javascript A2592000

# Fonts - 1 year
ExpiresByType font/ttf A31557600
ExpiresByType font/woff A31557600
ExpiresByType font/woff2 A31557600
ExpiresByType application/font-woff A31557600
ExpiresByType application/font-woff2 A31557600

# HTML - no cache
ExpiresByType text/html A0

# PDF - 1 month
ExpiresByType application/pdf A2592000

# JSON/XML - 1 hour
ExpiresByType application/json A3600
ExpiresByType application/xml A3600
```

**Testing:**
```bash
curl -I https://yourdomain.com/image.jpg | grep -E "Expires|Cache-Control"
```

### CyberPanel Integration

#### WordPress Caching

```apache
# In /home/yourdomain.com/public_html/.htaccess

ExpiresActive On

# WordPress uploads (images in wp-content/uploads)
ExpiresByType image/jpeg A31557600
ExpiresByType image/png A31557600
ExpiresByType image/gif A31557600

# WordPress theme assets
ExpiresByType text/css A2592000
ExpiresByType application/javascript A2592000

# WordPress HTML (dynamic, don't cache)
ExpiresByType text/html A0
```

### FilesMatch vs Expires

**Use FilesMatch when:**
- Need multiple headers per file type
- Need complex regex patterns
- Want more control

**Use Expires when:**
- Only setting cache expiration
- Want concise syntax
- Working with MIME types

**Both together:**
```apache
ExpiresActive On

<FilesMatch "\.(jpg|png|gif)$">
    ExpiresByType image/jpeg A31557600
    Header set Cache-Control "public, immutable"
    Header unset ETag
</FilesMatch>
```

---

## 9. PHP Directives

### What Are PHP Directives?

Change PHP configuration per-directory without editing php.ini.

### Directives

| Directive | Syntax | Purpose |
|-----------|--------|---------|
| **php_value** | `php_value name value` | Set numeric/string values |
| **php_flag** | `php_flag name on/off` | Set boolean (on/off) values |

### Requirements

- Must use **LSPHP** (not PHP-FPM)
- Must be **PHP_INI_ALL** or **PHP_INI_PERDIR** directive
- CyberPanel uses LSPHP by default ✅

### How to Use

#### Memory and Execution Limits

**What it does:** Allows scripts to use more memory/time.

```apache
# Increase memory (default 128M)
php_value memory_limit 256M

# Increase execution time (default 30s)
php_value max_execution_time 300

# Increase input time (default 60s)
php_value max_input_time 300

# Increase max input variables (default 1000)
php_value max_input_vars 5000
```

**Use case:** WordPress imports, WooCommerce bulk operations, data processing.

**Testing:**
```php
<?php
echo 'Memory Limit: ' . ini_get('memory_limit') . "\n";
echo 'Max Execution Time: ' . ini_get('max_execution_time') . "\n";
?>
```

#### Upload Limits

**What it does:** Allows larger file uploads.

```apache
# Allow 100MB uploads (default 2M)
php_value upload_max_filesize 100M
php_value post_max_size 100M

# Increase max file uploads (default 20)
php_value max_file_uploads 50
```

**Use case:** Media uploads, plugin/theme installation, backup uploads.

**Testing:**
```php
<?php
phpinfo();
// Search for upload_max_filesize and post_max_size
?>
```

#### Error Handling

**What it does:** Controls error display and logging.

```apache
# Production (hide errors)
php_flag display_errors off
php_flag log_errors on
php_value error_log /home/yourdomain.com/logs/php_errors.log

# Development (show errors)
php_flag display_errors on
php_value error_reporting 32767
```

**Use case:** Debugging vs production security.

#### Session Configuration

**What it does:** Configures PHP sessions.

```apache
# Session lifetime (1 hour)
php_value session.gc_maxlifetime 3600

# Session cookie (close browser = logout)
php_value session.cookie_lifetime 0

# Session security
php_flag session.cookie_httponly on
php_flag session.cookie_secure on
php_value session.cookie_samesite Strict
```

**Use case:** Login session duration, security.

#### Timezone

**What it does:** Sets server timezone.

```apache
php_value date.timezone "America/New_York"
php_value date.timezone "Europe/London"
php_value date.timezone "Asia/Tokyo"
```

**Use case:** Correct timestamps in logs, posts, events.

**Testing:**
```php
<?php
echo date_default_timezone_get();
?>
```

### CyberPanel Integration

#### WordPress Performance Tuning

```apache
# In /home/yourdomain.com/public_html/.htaccess

# WordPress recommended settings
php_value memory_limit 256M
php_value max_execution_time 300
php_value max_input_time 300
php_value max_input_vars 5000
php_value upload_max_filesize 64M
php_value post_max_size 64M

# Production error handling
php_flag display_errors off
php_flag log_errors on
php_value error_log /home/yourdomain.com/logs/php_errors.log

# Session security
php_flag session.cookie_httponly on
php_flag session.cookie_secure on
```

#### WooCommerce Optimization

```apache
# WooCommerce needs more resources
php_value memory_limit 512M
php_value max_execution_time 600
php_value max_input_vars 10000
php_value upload_max_filesize 128M
php_value post_max_size 128M
```

#### Development vs Production

**Development .htaccess:**
```apache
php_flag display_errors on
php_value error_reporting 32767
php_flag display_startup_errors on
php_value memory_limit 512M
```

**Production .htaccess:**
```apache
php_flag display_errors off
php_flag log_errors on
php_value error_log /home/yourdomain.com/logs/php_errors.log
php_value memory_limit 256M
```

### Common Use Cases

#### Fix "Memory Exhausted" Error

```apache
php_value memory_limit 512M
```

#### Fix "Maximum Execution Time Exceeded"

```apache
php_value max_execution_time 300
```

#### Fix "Upload Failed" (File Too Large)

```apache
php_value upload_max_filesize 100M
php_value post_max_size 100M
```

#### Fix "Maximum Input Vars Exceeded" (WordPress Theme Options)

```apache
php_value max_input_vars 10000
```

### Supported Directives

Most PHP ini settings can be changed:

**✅ Supported:**
- memory_limit
- max_execution_time
- max_input_time
- max_input_vars
- upload_max_filesize
- post_max_size
- display_errors
- log_errors
- error_log
- error_reporting
- session.* (all session directives)
- date.timezone
- default_charset
- output_buffering

**❌ Not Supported:**
- enable_dl (PHP_INI_SYSTEM only)
- safe_mode (deprecated)
- open_basedir (security setting)

---

## 10. Brute Force Protection

### What is Brute Force Protection?

Built-in WordPress login protection. Limits POST requests to wp-login.php and xmlrpc.php to stop password guessing attacks.

### Quick Start

```apache
BruteForceProtection On
```

That's it! Default settings: 10 attempts per 5 minutes.

### How It Works

1. Tracks POST requests to `/wp-login.php` and `/xmlrpc.php`
2. Counts requests per IP address
3. Uses time-window quota system (e.g., 10 requests per 300 seconds)
4. When quota exhausted, applies action (block, log, or throttle)
5. Quota resets after time window expires

### Phase 1 Directives (Basic)

| Directive | Values | Default | Description |
|-----------|--------|---------|-------------|
| **BruteForceProtection** | On/Off | Off | Enable protection |
| **BruteForceAllowedAttempts** | 1-1000 | 10 | Max POST requests per window |
| **BruteForceWindow** | 60-86400 | 300 | Time window (seconds) |
| **BruteForceAction** | block/log/throttle | block | Action when limit exceeded |

### Phase 2 Directives (Advanced)

| Directive | Values | Default | Description |
|-----------|--------|---------|-------------|
| **BruteForceXForwardedFor** | On/Off | Off | Use X-Forwarded-For for real IP |
| **BruteForceWhitelist** | IP list | (empty) | Bypass protection for these IPs |
| **BruteForceProtectPath** | path | (none) | Additional paths to protect |

### Actions Explained

#### block (Recommended)

**What it does:** Immediately returns 403 Forbidden.

```apache
BruteForceAction block
```

**Response:**
```
HTTP/1.1 403 Forbidden
Content-Type: text/html

<html>
<head><title>403 Forbidden</title></head>
<body>
<h1>Access Denied</h1>
<p>Too many login attempts. Please try again later.</p>
</body>
</html>
```

**Use case:** Production sites, maximum security.

#### log (Monitoring)

**What it does:** Allows request but logs to error.log.

```apache
BruteForceAction log
```

**Use case:** Testing, monitoring before enabling blocking.

**Check logs:**
```bash
grep BruteForce /usr/local/lsws/logs/error.log
```

#### throttle (New in v2.2.0)

**What it does:** Applies progressive delays before responding.

```apache
BruteForceAction throttle
```

**Throttle levels:**

| Over-Limit Attempts | Level | Delay | HTTP Response |
|---------------------|-------|-------|---------------|
| 1-2 | Soft | 2 seconds | 429 Too Many Requests |
| 3-5 | Medium | 5 seconds | 429 Too Many Requests |
| 6+ | Hard | 15 seconds | 429 Too Many Requests |

**Response includes:**
```
HTTP/1.1 429 Too Many Requests
Retry-After: 15
```

**Use case:** Slows down attackers while allowing legitimate users who forgot password.

### How to Use

#### Basic Protection (Small Site)

```apache
# Simple protection
BruteForceProtection On
```

**Result:** Default 10 attempts per 5 minutes, then block.

#### Strict Protection (High Security)

```apache
# Only 3 attempts per 15 minutes
BruteForceProtection On
BruteForceAllowedAttempts 3
BruteForceWindow 900
BruteForceAction block
```

**Result:** Very strict, good for high-value targets.

#### Moderate Protection with Throttle (Recommended)

```apache
# 5 attempts per 5 minutes, then progressive throttle
BruteForceProtection On
BruteForceAllowedAttempts 5
BruteForceWindow 300
BruteForceAction throttle
```

**Result:** Legitimate users can still login (slowly), attackers waste time.

#### Behind Cloudflare/Proxy

**Problem:** All requests appear to come from proxy IP.

**Solution:** Use X-Forwarded-For to get real client IP.

```apache
BruteForceProtection On
BruteForceAllowedAttempts 5
BruteForceWindow 300
BruteForceAction throttle
BruteForceXForwardedFor On
```

**Important:** Only enable if behind trusted proxy (Cloudflare, nginx).

#### With IP Whitelist

**What it does:** Allows unlimited attempts from trusted IPs.

```apache
BruteForceProtection On
BruteForceAllowedAttempts 3
BruteForceWindow 900
BruteForceAction block
BruteForceWhitelist 203.0.113.50, 192.168.1.0/24, 10.0.0.0/8
```

**Use case:** Whitelist office IP, admin home IP, VPN range.

#### Protect Custom Login Pages

```apache
# Protect custom endpoints
BruteForceProtection On
BruteForceProtectPath /admin/login
BruteForceProtectPath /api/auth
BruteForceProtectPath /members/signin
```

**Default protected:** `/wp-login.php` and `/xmlrpc.php`

### CyberPanel Integration

#### WordPress Security Setup

**Step 1:** Navigate to website .htaccess
```bash
cd /home/yourdomain.com/public_html
nano .htaccess
```

**Step 2:** Add protection
```apache
# At top of .htaccess
BruteForceProtection On
BruteForceAllowedAttempts 5
BruteForceWindow 300
BruteForceAction throttle
```

**Step 3:** Save and test
```bash
# Try multiple wrong passwords
# After 5 attempts, should get throttled
```

**Step 4:** Monitor logs
```bash
tail -f /usr/local/lsws/logs/error.log | grep BruteForce
```

#### WooCommerce + WordPress

```apache
# Protect both WordPress and WooCommerce login
BruteForceProtection On
BruteForceAllowedAttempts 5
BruteForceWindow 300
BruteForceAction block
BruteForceProtectPath /my-account/
BruteForceProtectPath /checkout/
```

#### Multi-Site WordPress

```apache
# Apply to all subsites
BruteForceProtection On
BruteForceAllowedAttempts 5
BruteForceWindow 300
BruteForceAction throttle
BruteForceXForwardedFor On
```

### Shared Memory Storage

**Location:** `/dev/shm/ols/`

```bash
ls -la /dev/shm/ols/
# BFProt.shm  - Stores IP quota data
# BFProt.lock - Synchronization lock
```

**Persistence:** Data survives OpenLiteSpeed restarts (stored in tmpfs).

**Reset/Clear:**
```bash
# Clear all quota data
rm -f /dev/shm/ols/BFProt.*
/usr/local/lsws/bin/lswsctrl restart
```

**Use case:** Accidentally locked out, need to reset.

### Monitoring and Logs

#### View Brute Force Events

```bash
grep BruteForce /usr/local/lsws/logs/error.log
```

**Sample log entries:**

```
[INFO] [BruteForce] Initialized: 10 attempts per 300s window, action: throttle
[WARN] [BruteForce] Warning: 192.168.1.50 has 2 attempts remaining for /wp-login.php
[NOTICE] [BruteForce] Blocked 192.168.1.50 - quota exhausted for /wp-login.php (10 attempts in 300s)
[NOTICE] [BruteForce] Throttling 192.168.1.50 (medium level, 5000ms delay) for /wp-login.php
```

#### Real-Time Monitoring

```bash
# Watch in real-time
tail -f /usr/local/lsws/logs/error.log | grep BruteForce

# Count blocked IPs today
grep "BruteForce.*Blocked" /usr/local/lsws/logs/error.log | grep "$(date +%Y-%m-%d)" | wc -l
```

#### Check Specific IP

```bash
grep "BruteForce.*192.168.1.50" /usr/local/lsws/logs/error.log
```

### Testing Brute Force Protection

#### Manual Test

```bash
# Try multiple wrong passwords
for i in {1..15}; do
    curl -X POST https://yourdomain.com/wp-login.php \
         -d "log=admin&pwd=wrong$i&wp-submit=Log+In" \
         -I | grep "HTTP"
    sleep 1
done

# After BruteForceAllowedAttempts, should see:
# HTTP/1.1 403 Forbidden (if action=block)
# HTTP/1.1 429 Too Many Requests (if action=throttle)
```

#### Check Logs

```bash
grep BruteForce /usr/local/lsws/logs/error.log | tail -20
```

### Common Use Cases

#### Production WordPress

```apache
BruteForceProtection On
BruteForceAllowedAttempts 5
BruteForceWindow 300
BruteForceAction block
```

#### Behind Cloudflare

```apache
BruteForceProtection On
BruteForceAllowedAttempts 5
BruteForceWindow 300
BruteForceAction throttle
BruteForceXForwardedFor On
```

#### Enterprise with Whitelist

```apache
BruteForceProtection On
BruteForceAllowedAttempts 3
BruteForceWindow 900
BruteForceAction block
BruteForceXForwardedFor On
BruteForceWhitelist 10.0.0.0/8, 192.168.1.0/24, 203.0.113.100
BruteForceProtectPath /admin/
BruteForceProtectPath /api/login
```

### Troubleshooting

**Problem:** Legitimate users getting blocked

**Solution:**
```apache
# Increase allowed attempts
BruteForceAllowedAttempts 10

# Or use throttle instead of block
BruteForceAction throttle

# Or whitelist their IP
BruteForceWhitelist 203.0.113.50
```

**Problem:** Protection not working

**Solution:**
```bash
# Check module loaded
ls -la /usr/local/lsws/modules/cyberpanel_ols.so

# Check .htaccess syntax
cat /home/yourdomain.com/public_html/.htaccess | grep BruteForce

# Check logs
grep BruteForce /usr/local/lsws/logs/error.log

# Restart OpenLiteSpeed
/usr/local/lsws/bin/lswsctrl restart
```

**Problem:** Shared memory errors

**Solution:**
```bash
# Create directory if missing
mkdir -p /dev/shm/ols

# Set permissions
chmod 755 /dev/shm/ols

# Restart
/usr/local/lsws/bin/lswsctrl restart
```

---

## CyberPanel Integration

### Accessing Website Files

#### Via CyberPanel File Manager

1. Log into **CyberPanel** (https://yourserver:8090)
2. Click **File Manager**
3. Navigate to `/home/yourdomain.com/public_html`
4. Create or edit `.htaccess`
5. Add directives from this guide
6. Click **Save**

#### Via SSH

```bash
# Log in via SSH
ssh root@yourserver

# Navigate to website
cd /home/yourdomain.com/public_html

# Edit .htaccess
nano .htaccess

# Add directives
# Save: Ctrl+X, Y, Enter
```

#### Via FTP (FileZilla)

1. Connect via FTP
2. Navigate to `/home/yourdomain.com/public_html`
3. Download `.htaccess`
4. Edit locally
5. Upload back

### Creating New Website

1. **Create Website** in CyberPanel
2. **Navigate to directory:**
   ```bash
   cd /home/newsite.com/public_html
   ```
3. **Create .htaccess:**
   ```bash
   nano .htaccess
   ```
4. **Add base configuration:**
   ```apache
   # Security headers
   Header set X-Frame-Options "SAMEORIGIN"
   Header set X-Content-Type-Options "nosniff"

   # Brute force protection
   BruteForceProtection On

   # Cache static assets
   <FilesMatch "\.(jpg|png|gif|css|js)$">
       Header set Cache-Control "max-age=31536000, public"
   </FilesMatch>
   ```

### WordPress on CyberPanel

#### Complete WordPress .htaccess

```apache
# Security Headers
Header set X-Frame-Options "SAMEORIGIN"
Header set X-Content-Type-Options "nosniff"
Header set X-XSS-Protection "1; mode=block"
Header unset X-Powered-By

# Brute Force Protection
BruteForceProtection On
BruteForceAllowedAttempts 5
BruteForceWindow 300
BruteForceAction throttle

# Performance - Cache Static Assets
<FilesMatch "\.(jpg|jpeg|png|gif|webp|svg|ico)$">
    Header set Cache-Control "max-age=31536000, public, immutable"
</FilesMatch>

<FilesMatch "\.(css|js)$">
    Header set Cache-Control "max-age=2592000, public"
</FilesMatch>

# PHP Configuration
php_value memory_limit 256M
php_value upload_max_filesize 64M
php_value post_max_size 64M
php_value max_execution_time 300
php_flag display_errors off

# WordPress Rewrite Rules (leave as-is)
# BEGIN WordPress
<IfModule mod_rewrite.c>
RewriteEngine On
RewriteBase /
RewriteRule ^index\.php$ - [L]
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule . /index.php [L]
</IfModule>
# END WordPress
```

### Staging Environment

```apache
# Staging site - restrict access
Order deny,allow
Deny from all
Allow from YOUR.OFFICE.IP
Allow from YOUR.HOME.IP

# No search engine indexing
Header set X-Robots-Tag "noindex, nofollow"

# Show errors (development)
php_flag display_errors on
php_value error_reporting 32767
```

### Testing After Configuration

```bash
# Test headers
curl -I https://yourdomain.com | grep -E "X-Frame|Cache-Control|X-Content"

# Test specific file
curl -I https://yourdomain.com/wp-content/uploads/2024/12/image.jpg | grep Cache

# Test PHP settings
echo '<?php phpinfo(); ?>' > /home/yourdomain.com/public_html/info.php
curl https://yourdomain.com/info.php | grep memory_limit

# Clean up
rm /home/yourdomain.com/public_html/info.php
```

---

## Real-World Examples

### Example 1: High-Performance WordPress

```apache
# Security
Header set X-Frame-Options "SAMEORIGIN"
Header set X-Content-Type-Options "nosniff"
Header set X-XSS-Protection "1; mode=block"
Header set Referrer-Policy "strict-origin-when-cross-origin"
Header unset Server
Header unset X-Powered-By

# Brute Force Protection
BruteForceProtection On
BruteForceAllowedAttempts 5
BruteForceWindow 300
BruteForceAction throttle
BruteForceXForwardedFor On

# Aggressive Caching
<FilesMatch "\.(jpg|jpeg|png|gif|webp|svg|ico)$">
    Header set Cache-Control "max-age=31536000, public, immutable"
    Header unset ETag
</FilesMatch>

<FilesMatch "\.(woff2?|ttf|eot)$">
    Header set Cache-Control "max-age=31536000, public, immutable"
    Header set Access-Control-Allow-Origin "*"
</FilesMatch>

<FilesMatch "\.(css|js)$">
    Header set Cache-Control "max-age=2592000, public"
</FilesMatch>

# PHP Optimization
php_value memory_limit 256M
php_value max_execution_time 300
php_value upload_max_filesize 64M
php_value post_max_size 64M
php_flag display_errors off
php_flag log_errors on
```

### Example 2: WooCommerce E-commerce

```apache
# Security Headers
Header set X-Frame-Options "SAMEORIGIN"
Header set X-Content-Type-Options "nosniff"
Header set X-XSS-Protection "1; mode=block"

# Strict Brute Force Protection
BruteForceProtection On
BruteForceAllowedAttempts 3
BruteForceWindow 900
BruteForceAction block
BruteForceProtectPath /my-account/
BruteForceProtectPath /checkout/

# Product Image Caching
<FilesMatch "\.(jpg|jpeg|png|webp)$">
    Header set Cache-Control "max-age=31536000, public, immutable"
</FilesMatch>

# Don't Cache Checkout/Cart
<FilesMatch "(cart|checkout|my-account)">
    Header set Cache-Control "no-cache, no-store, must-revalidate"
</FilesMatch>

# PHP for WooCommerce
php_value memory_limit 512M
php_value max_execution_time 600
php_value max_input_vars 10000
php_value upload_max_filesize 128M
php_value post_max_size 128M
```

### Example 3: API Server

```apache
# CORS for API
Header set Access-Control-Allow-Origin "*"
Header set Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS"
Header set Access-Control-Allow-Headers "Content-Type, Authorization, X-API-Key"
Header set Access-Control-Max-Age "86400"

# JSON Response Headers
<FilesMatch "\.json$">
    Header set Content-Type "application/json; charset=utf-8"
    Header set X-Content-Type-Options "nosniff"
    Header set Cache-Control "no-cache, must-revalidate"
</FilesMatch>

# API Rate Limiting
BruteForceProtection On
BruteForceAllowedAttempts 100
BruteForceWindow 60
BruteForceAction throttle
BruteForceProtectPath /api/

# Environment
SetEnv API_VERSION v2
SetEnv API_ENVIRONMENT production
```

### Example 4: Static Site with CDN

```apache
# Aggressive Caching
ExpiresActive On
ExpiresByType image/jpeg A31557600
ExpiresByType image/png A31557600
ExpiresByType image/gif A31557600
ExpiresByType text/css A31557600
ExpiresByType application/javascript A31557600
ExpiresByType text/html A3600

# CORS for CDN
Header set Access-Control-Allow-Origin "*"

# Security Headers
Header set X-Frame-Options "SAMEORIGIN"
Header set X-Content-Type-Options "nosniff"
Header set Content-Security-Policy "default-src 'self' https://cdn.example.com"

# Remove Server Info
Header unset Server
Header unset X-Powered-By
```

### Example 5: Multi-Environment Setup

**Production (.htaccess):**
```apache
SetEnv APPLICATION_ENV production
php_flag display_errors off
php_flag log_errors on
BruteForceProtection On
BruteForceAction block
Header set X-Robots-Tag "index, follow"
```

**Staging (staging.example.com/.htaccess):**
```apache
SetEnv APPLICATION_ENV staging
php_flag display_errors on
BruteForceProtection On
BruteForceAction log
Header set X-Robots-Tag "noindex, nofollow"

# IP Restriction
Order deny,allow
Deny from all
Allow from 203.0.113.50
```

**Development (dev.example.com/.htaccess):**
```apache
SetEnv APPLICATION_ENV development
php_flag display_errors on
php_value error_reporting 32767
BruteForceProtection Off
Header set X-Robots-Tag "noindex, nofollow"
```

---

## Troubleshooting

### Common Issues

#### 1. Directives Not Working

**Symptoms:** Headers not appearing, PHP settings not applied.

**Solutions:**

```bash
# Check module is installed
ls -la /usr/local/lsws/modules/cyberpanel_ols.so
# Should show 147KB file

# Check module is loaded in config
grep cyberpanel_ols /usr/local/lsws/conf/httpd_config.conf
# Should show: module cyberpanel_ols {

# Restart OpenLiteSpeed
/usr/local/lsws/bin/lswsctrl restart

# Check logs for errors
tail -50 /usr/local/lsws/logs/error.log
```

#### 2. .htaccess File Permissions

**Symptoms:** 500 Internal Server Error

**Solutions:**

```bash
# Set correct permissions
chmod 644 /home/yourdomain.com/public_html/.htaccess

# Set correct ownership
chown nobody:nogroup /home/yourdomain.com/public_html/.htaccess

# Verify
ls -la /home/yourdomain.com/public_html/.htaccess
# Should show: -rw-r--r-- nobody nogroup
```

#### 3. Headers Not Showing

**Symptoms:** `curl -I` doesn't show custom headers

**Solutions:**

```bash
# Clear browser cache
# Some headers are cached aggressively

# Test with curl (bypasses cache)
curl -I https://yourdomain.com

# Test specific file
curl -I https://yourdomain.com/test.jpg

# Check if file exists
ls -la /home/yourdomain.com/public_html/test.jpg

# Verify .htaccess syntax
cat /home/yourdomain.com/public_html/.htaccess
```

#### 4. PHP Directives Not Applied

**Symptoms:** `phpinfo()` shows old values

**Solutions:**

```bash
# Verify using LSPHP (not PHP-FPM)
# CyberPanel uses LSPHP by default

# Check if directive is allowed
# Some directives are PHP_INI_SYSTEM only

# Create test file
echo '<?php phpinfo(); ?>' > /home/yourdomain.com/public_html/info.php

# Check value
curl https://yourdomain.com/info.php | grep memory_limit

# Delete test file
rm /home/yourdomain.com/public_html/info.php
```

#### 5. Brute Force Protection Not Triggering

**Symptoms:** Can submit unlimited login attempts

**Solutions:**

```bash
# Check shared memory directory
ls -la /dev/shm/ols/
# Should show BFProt.shm and BFProt.lock

# Create if missing
mkdir -p /dev/shm/ols
chmod 755 /dev/shm/ols

# Check .htaccess syntax
grep BruteForce /home/yourdomain.com/public_html/.htaccess

# Must be POST request to protected path
curl -X POST https://yourdomain.com/wp-login.php -d "log=test&pwd=test"

# Check logs
grep BruteForce /usr/local/lsws/logs/error.log

# Restart
/usr/local/lsws/bin/lswsctrl restart
```

#### 6. Access Control Allowing All

**Symptoms:** IP restrictions not working

**Solutions:**

```bash
# Verify your actual IP
curl ifconfig.me

# Check CIDR syntax
# 192.168.1.0/24 = 192.168.1.1 to 192.168.1.254
# 10.0.0.0/8 = 10.0.0.0 to 10.255.255.255

# Check logs for access decisions
grep "cyberpanel_access" /usr/local/lsws/logs/error.log

# Test with curl from different IP
curl -I https://yourdomain.com
# Should get 403 if not allowed
```

#### 7. Redirect Loop

**Symptoms:** ERR_TOO_MANY_REDIRECTS

**Solutions:**

```bash
# Check for conflicting redirects
grep Redirect /home/yourdomain.com/public_html/.htaccess

# Common mistake:
# BAD: Both redirects active
# Redirect 301 / https://example.com/
# Redirect 301 / https://www.example.com/

# GOOD: Only one
Redirect 301 / https://www.example.com/

# Check WordPress settings
# wp-admin > Settings > General
# WordPress Address and Site Address must match
```

### Getting Help

#### Enable Debug Logging

```bash
# Edit OpenLiteSpeed config
nano /usr/local/lsws/conf/httpd_config.conf

# Change Log Level to DEBUG
# Restart
/usr/local/lsws/bin/lswsctrl restart

# Monitor logs
tail -f /usr/local/lsws/logs/error.log
```

#### Collect Information

```bash
# Module version
ls -lh /usr/local/lsws/modules/cyberpanel_ols.so

# OpenLiteSpeed version
/usr/local/lsws/bin/openlitespeed -v

# Check .htaccess
cat /home/yourdomain.com/public_html/.htaccess

# Recent logs
tail -100 /usr/local/lsws/logs/error.log

# Test headers
curl -I https://yourdomain.com
```

#### Report Issue

When reporting issues, include:

1. **What you're trying to do** (which feature)
2. **.htaccess content** (sanitized)
3. **Expected behavior** vs **actual behavior**
4. **Error logs** (last 50 lines)
5. **Test results** (curl output)
6. **Module version** and **OpenLiteSpeed version**

---

## Performance Optimization

### Best Practices

1. **Minimize .htaccess size** - Only include necessary directives
2. **Use FilesMatch carefully** - Each pattern adds regex overhead
3. **Prefer block over throttle** - Throttle holds connections longer
4. **Whitelist known IPs** - Skips brute force checks entirely
5. **Set long cache times** - Reduce server load

### Benchmarks

| Metric | Value |
|--------|-------|
| Overhead per request | < 1ms |
| Memory per cached .htaccess | ~2KB |
| Memory per tracked IP (brute force) | ~64 bytes |
| Cache invalidation | mtime-based (instant) |

### Optimization Examples

**Before (Slow):**
```apache
# Every request checks all patterns
Header set X-Custom "Value"
Header set X-Another "Value"
Header set X-More "Value"

<FilesMatch ".*">
    Header set Cache-Control "max-age=3600"
</FilesMatch>
```

**After (Fast):**
```apache
# Only static assets checked
<FilesMatch "\.(jpg|png|css|js)$">
    Header set Cache-Control "max-age=31536000, public, immutable"
</FilesMatch>
```

---

## Appendix

### Quick Reference

#### Headers
```apache
Header set Name "Value"
Header unset Name
Header append Name "Value"
```

#### Access Control
```apache
Order deny,allow
Deny from all
Allow from 192.168.1.0/24
```

#### Redirects
```apache
Redirect 301 /old /new
RedirectMatch 301 ^/blog/(.*)$ /news/$1
```

#### PHP
```apache
php_value memory_limit 256M
php_flag display_errors off
```

#### Brute Force
```apache
BruteForceProtection On
BruteForceAllowedAttempts 5
BruteForceWindow 300
BruteForceAction throttle
```

### Common MIME Types

```
image/jpeg, image/png, image/gif, image/webp, image/svg+xml
text/css, text/html, text/javascript, text/plain
application/javascript, application/json, application/xml, application/pdf
font/ttf, font/woff, font/woff2
```

### Time Duration Reference

```
1 minute  = 60
5 minutes = 300
15 minutes = 900
1 hour    = 3600
1 day     = 86400
1 week    = 604800
1 month   = 2592000
1 year    = 31557600
```

### IP CIDR Cheat Sheet

```
/32 = 1 IP (255.255.255.255)
/24 = 256 IPs (255.255.255.0)
/16 = 65,536 IPs (255.255.0.0)
/8  = 16,777,216 IPs (255.0.0.0)
```

---

## Support

- **GitHub:** [github.com/usmannasir/cyberpanel_ols](https://github.com/usmannasir/cyberpanel_ols)
- **Community:** [community.cyberpanel.net](https://community.cyberpanel.net)

---

**Document Version:** 1.0
**Module Version:** 2.2.0
**Last Updated:** December 28, 2025

---

*Thank you for using the CyberPanel OpenLiteSpeed Module!*
