# Complete Mautic Installation Guide for CyberPanel

## Overview

Mautic is an open-source marketing automation platform that provides email marketing, lead management, campaign building, and marketing analytics. CyberPanel offers a one-click installation feature for Mautic that simplifies the deployment process.

## Prerequisites

Before installing Mautic, ensure you have:

1. **CyberPanel installed** and running
2. **A website created** in CyberPanel
3. **Administrator or website owner access**
4. **PHP 8.1 or higher** (CyberPanel will automatically switch to PHP 8.1 during installation)
5. **Sufficient database quota** in your hosting package

## Step-by-Step Installation Process

### Step 1: Access CyberPanel Dashboard

1. **Login to CyberPanel**
   - Navigate to: `https://your-server-ip:8090`
   - Enter your username and password
   - Click "Sign In"

### Step 2: Navigate to Websites Section

1. **From the main dashboard**, look for the left sidebar menu
2. **Click on "Websites"** to expand the menu
3. **Select "List Websites"** from the dropdown

### Step 3: Access Your Website's Management Page

1. **Find your website** in the list of hosted websites
2. **Click on the "Manage" button** next to your website domain
   - Alternatively, click directly on the domain name

### Step 4: Navigate to Application Installer

Once on your website's management page:

1. **Scroll down** to find the **"Applications"** section
2. **Look for the Mautic card** with the Mautic logo
   - It will show "Open source marketing automation" as the description
3. **Click on the Mautic card** or the "Install Now" button

**Direct URL Pattern:**
```
https://your-cyberpanel-domain:8090/websites/your-domain.com/installMautic
```

### Step 5: Configure Mautic Installation

On the Mautic installation page, you'll need to provide:

#### Required Information:

1. **Administrator Username**
   - Default suggestion: `admin`
   - Choose a secure username for the Mautic admin account

2. **Email Address**
   - Enter a valid email address
   - This will be used for the Mautic administrator account
   - Important for password recovery and notifications

3. **Password**
   - Create a strong password
   - Must be secure to protect your marketing platform
   - Recommended: Use a combination of uppercase, lowercase, numbers, and special characters

### Step 6: Start Installation

1. **Review all entered information**
2. **Click the "Install Now" button**
3. The installation will begin with the following automated steps:

### Step 7: Installation Process

The system will automatically:

1. **Change PHP version to 8.1** (if not already set)
   - This ensures compatibility with Mautic 6.x
   
2. **Create a MySQL database**
   - Database name, username, and password are generated automatically
   
3. **Download Mautic 6.0.3** from GitHub
   - Latest stable version is downloaded
   
4. **Extract files** to the specified location
   
5. **Run Mautic installer** with your provided credentials
   
6. **Generate assets** for the Mautic interface
   
7. **Configure web server** settings

#### Installation Progress Indicators:

- Setting up paths (0%)
- Setting up Database (20%)
- Downloading Mautic Core (30%)
- Extracting Mautic Core (50%)
- Running Mautic installer (70%)
- Successfully Installed (100%)

### Step 8: Post-Installation

Once installation is complete:

1. **Access URL will be displayed**
   - Example: `https://your-domain.com` or `https://your-domain.com/mautic`
   
2. **Click on the provided URL** to access Mautic

3. **Complete Mautic Setup Wizard**:
   - The first time you access Mautic, you'll see the setup wizard
   - Configure email settings
   - Set up cron jobs for email sending
   - Configure tracking settings

### Step 9: Initial Mautic Configuration

After accessing Mautic for the first time:

1. **Login** with the credentials you provided during installation

2. **Configure Email Settings**:
   - SMTP settings for sending emails
   - Bounce handling
   - Unsubscribe settings

3. **Set Up Cron Jobs** (Important!):
   ```bash
   # Add these cron jobs for Mautic to function properly
   */5 * * * * /usr/local/lsws/lsphp81/bin/php /home/your-domain/public_html/bin/console mautic:segments:update
   */5 * * * * /usr/local/lsws/lsphp81/bin/php /home/your-domain/public_html/bin/console mautic:campaigns:update
   */5 * * * * /usr/local/lsws/lsphp81/bin/php /home/your-domain/public_html/bin/console mautic:campaigns:trigger
   0 0 * * * /usr/local/lsws/lsphp81/bin/php /home/your-domain/public_html/bin/console mautic:emails:send
   ```

## Technical Details

### System Requirements Met by Installation

- **PHP Version**: 8.1 (automatically configured)
- **Required PHP Extensions** (installed automatically):
  - bcmath
  - imap
  - curl
  - gd
  - json
  - mbstring
  - mysql
  - xml
  - zip

### Database Configuration

- **Database Type**: MySQL/MariaDB
- **Host**: localhost
- **Port**: 3306
- **Character Set**: UTF-8
- **Collation**: utf8mb4_unicode_ci

### File Permissions

The installation automatically sets appropriate permissions:
- Files: 644
- Directories: 755
- Configuration files are secured

### Web Server Configuration

- **LiteSpeed/OpenLiteSpeed**: Configured automatically
- **Apache**: If using Apache, additional modules are installed
- **.htaccess**: Properly configured for URL rewriting

## Features Available After Installation

Once Mautic is installed, you can:

1. **Email Marketing**
   - Create and send email campaigns
   - Design responsive email templates
   - A/B testing for emails

2. **Lead Management**
   - Track visitor behavior
   - Score and segment leads
   - Progressive profiling

3. **Marketing Campaigns**
   - Visual campaign builder
   - Multi-channel campaigns
   - Automated workflows

4. **Analytics & Reporting**
   - Real-time analytics
   - Campaign performance metrics
   - ROI tracking

## Troubleshooting

### Common Issues and Solutions

1. **Installation Fails at Database Creation**
   - **Issue**: Maximum database limit reached
   - **Solution**: Upgrade your hosting package or delete unused databases

2. **PHP Version Error**
   - **Issue**: PHP 8.1 not available
   - **Solution**: The installer will automatically install PHP 8.1 if missing

3. **Permission Errors**
   - **Issue**: Cannot write to directory
   - **Solution**: Ensure the website user has proper permissions

4. **Blank Page After Installation**
   - **Issue**: Missing PHP extensions
   - **Solution**: Check error logs and install missing extensions

5. **Emails Not Sending**
   - **Issue**: Cron jobs not configured
   - **Solution**: Set up the required cron jobs as shown above

### Checking Installation Logs

To debug issues:

1. **Check CyberPanel logs**:
   ```bash
   tail -f /home/cyberpanel/error-logs.txt
   ```

## Maintenance Tasks

### Regular Maintenance

1. **Clear Cache**:
   ```bash
   php bin/console cache:clear
   ```

2. **Update Database Schema**:
   ```bash
   php bin/console doctrine:schema:update --force
   ```

3. **Maintenance Mode** (during updates):
   ```bash
   php bin/console mautic:maintenance:enable
   php bin/console mautic:maintenance:disable
   ```

## Updating Mautic

To update Mautic to a newer version:

1. **Backup your installation** first
2. **Enable maintenance mode**
3. **Run update command**:
   ```bash
   php bin/console mautic:update:find
   php bin/console mautic:update:apply
   ```
4. **Clear cache**
5. **Disable maintenance mode**

## Getting Help

### Resources

1. **Mautic Documentation**: https://docs.mautic.org/
2. **Mautic Community**: https://community.mautic.org/
3. **CyberPanel Forums**: https://community.cyberpanel.net/
4. **GitHub Issues**: https://github.com/mautic/mautic/issues

### Support Channels

- **CyberPanel Support**: For installation issues
- **Mautic Community**: For Mautic-specific questions
- **Professional Support**: Available from Mautic partners

## Conclusion

The CyberPanel Mautic installer streamlines the deployment of this powerful marketing automation platform. With automatic PHP configuration, database setup, and web server optimization, you can have Mautic running in minutes. Remember to complete the post-installation configuration, especially setting up cron jobs, to ensure all features work correctly.

For optimal performance, regularly maintain your Mautic installation and keep both CyberPanel and Mautic updated to their latest versions.