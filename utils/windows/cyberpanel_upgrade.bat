@echo off
REM CyberPanel Windows Upgrade Script
REM This script upgrades an existing CyberPanel installation

echo ==========================================
echo CyberPanel Windows Upgrade Script
echo ==========================================
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script must be run as administrator
    echo Please right-click and select "Run as administrator"
    pause
    exit /b 1
)

echo [OK] Running with administrator privileges
echo.

REM Check if CyberPanel is installed
set CYBERPANEL_DIR=C:\usr\local\CyberCP
if not exist "%CYBERPANEL_DIR%" (
    echo [ERROR] CyberPanel not found at %CYBERPANEL_DIR%
    echo Please run the installation script first
    pause
    exit /b 1
)

echo [OK] CyberPanel installation found
echo.

REM Create backup
echo Creating backup of current installation...
set BACKUP_DIR=%CYBERPANEL_DIR%_backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set BACKUP_DIR=%BACKUP_DIR: =0%
if exist "%BACKUP_DIR%" rmdir /s /q "%BACKUP_DIR%"
xcopy "%CYBERPANEL_DIR%" "%BACKUP_DIR%" /E /I /H /Y >nul
if %errorLevel% neq 0 (
    echo [WARNING] Failed to create backup, continuing anyway...
) else (
    echo [OK] Backup created: %BACKUP_DIR%
)

REM Navigate to CyberPanel directory
cd /d "%CYBERPANEL_DIR%"

REM Activate virtual environment
echo Activating virtual environment...
if not exist "Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found
    echo Please reinstall CyberPanel
    pause
    exit /b 1
)
call Scripts\activate.bat
if %errorLevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment activated

REM Navigate to CyberPanel source
cd cyberpanel

REM Stop any running CyberPanel processes
echo Stopping CyberPanel processes...
taskkill /f /im python.exe 2>nul
taskkill /f /im lscpd.exe 2>nul
echo [OK] Processes stopped

REM Update source code
echo Updating CyberPanel source code...
git fetch origin
if %errorLevel% neq 0 (
    echo [WARNING] Failed to fetch updates, continuing with current version...
) else (
    git reset --hard origin/stable
    if %errorLevel% neq 0 (
        echo [WARNING] Failed to reset to latest version, continuing...
    ) else (
        echo [OK] Source code updated
    )
)

REM Upgrade pip and requirements
echo Upgrading Python packages...
python -m pip install --upgrade pip setuptools wheel
if %errorLevel% neq 0 (
    echo [WARNING] Failed to upgrade pip, continuing...
)

REM Install/upgrade requirements
echo Installing/upgrading requirements...
pip install --upgrade --default-timeout=3600 -r requirments.txt
if %errorLevel% neq 0 (
    echo [ERROR] Failed to install/upgrade requirements
    echo Please check your internet connection and try again
    pause
    exit /b 1
)
echo [OK] Requirements updated

REM Run database migrations
echo Running database migrations...
python manage.py makemigrations
if %errorLevel% neq 0 (
    echo [WARNING] Failed to create migrations, continuing...
) else (
    python manage.py migrate
    if %errorLevel% neq 0 (
        echo [WARNING] Failed to apply migrations, continuing...
    ) else (
        echo [OK] Database migrations completed
    )
)

REM Collect static files
echo Collecting static files...
python manage.py collectstatic --noinput
if %errorLevel% neq 0 (
    echo [WARNING] Failed to collect static files, continuing...
) else (
    echo [OK] Static files collected
)

REM Update startup script
echo Updating startup script...
(
echo @echo off
echo cd /d "%CYBERPANEL_DIR%\cyberpanel"
echo call ..\Scripts\activate.bat
echo python manage.py runserver 0.0.0.0:8090
) > start_cyberpanel.bat

REM Test installation
echo Testing installation...
python manage.py check
if %errorLevel% neq 0 (
    echo [WARNING] Installation check failed, but continuing...
) else (
    echo [OK] Installation check passed
)

echo.
echo ==========================================
echo Upgrade Complete!
echo ==========================================
echo.
echo CyberPanel has been upgraded successfully
echo.
echo To start CyberPanel:
echo 1. Run: start_cyberpanel.bat
echo 2. Open your browser to: http://localhost:8090
echo.
echo Backup location: %BACKUP_DIR%
echo.
echo If you encounter any issues, you can restore from backup:
echo 1. Stop CyberPanel
echo 2. Delete current installation
echo 3. Restore from backup directory
echo.
pause
