@echo off
REM CyberPanel Windows Installation Script
REM This script installs CyberPanel on Windows systems

echo ==========================================
echo CyberPanel Windows Installation Script
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

REM Check Windows version
for /f "tokens=4-5 delims=. " %%i in ('ver') do set VERSION=%%i.%%j
if "%VERSION%" == "10.0" (
    echo [OK] Windows 10/11 detected
) else if "%VERSION%" == "6.3" (
    echo [OK] Windows 8.1 detected
) else if "%VERSION%" == "6.1" (
    echo [OK] Windows 7 detected
) else (
    echo [WARNING] Unsupported Windows version detected: %VERSION%
    echo CyberPanel may not work properly on this version
    pause
)

echo.
echo Checking system requirements...

REM Check if Python is installed
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo [OK] Python %PYTHON_VERSION% found
)

REM Check if pip is available
pip --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] pip is not available
    echo Please install pip or reinstall Python with pip
    pause
    exit /b 1
) else (
    echo [OK] pip is available
)

REM Check available disk space
for /f "tokens=3" %%i in ('dir /-c %SystemDrive%\ ^| find "bytes free"') do set FREE_SPACE=%%i
if %FREE_SPACE% LSS 10737418240 (
    echo [WARNING] Less than 10GB free space available
    echo CyberPanel requires at least 10GB of free space
    pause
)

echo.
echo ==========================================
echo CyberPanel Installation
echo ==========================================
echo.

REM Create CyberPanel directory
set CYBERPANEL_DIR=C:\usr\local\CyberCP
if not exist "%CYBERPANEL_DIR%" (
    echo Creating CyberPanel directory...
    mkdir "%CYBERPANEL_DIR%" 2>nul
    if %errorLevel% neq 0 (
        echo [ERROR] Failed to create directory %CYBERPANEL_DIR%
        echo Please ensure you have sufficient permissions
        pause
        exit /b 1
    )
    echo [OK] Directory created: %CYBERPANEL_DIR%
) else (
    echo [OK] Directory already exists: %CYBERPANEL_DIR%
)

REM Navigate to CyberPanel directory
cd /d "%CYBERPANEL_DIR%"

REM Create virtual environment
echo Creating Python virtual environment...
python -m venv . --system-site-packages
if %errorLevel% neq 0 (
    echo [ERROR] Failed to create virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment created

REM Activate virtual environment
echo Activating virtual environment...
call Scripts\activate.bat
if %errorLevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment activated

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip setuptools wheel
if %errorLevel% neq 0 (
    echo [WARNING] Failed to upgrade pip, continuing anyway...
)

REM Download CyberPanel source
echo Downloading CyberPanel source code...
if exist "cyberpanel" (
    echo [INFO] CyberPanel source already exists, updating...
    cd cyberpanel
    git pull origin stable
    if %errorLevel% neq 0 (
        echo [WARNING] Failed to update source, using existing version
    )
    cd ..
) else (
    echo Cloning CyberPanel repository...
    git clone https://github.com/usmannasir/cyberpanel.git
    if %errorLevel% neq 0 (
        echo [ERROR] Failed to clone CyberPanel repository
        echo Please check your internet connection
        pause
        exit /b 1
    )
    echo [OK] Source code downloaded
)

REM Navigate to CyberPanel source
cd cyberpanel

REM Install requirements
echo Installing Python requirements...
echo This may take several minutes...
pip install --default-timeout=3600 -r requirments.txt
if %errorLevel% neq 0 (
    echo [ERROR] Failed to install requirements
    echo Please check your internet connection and try again
    pause
    exit /b 1
)
echo [OK] Requirements installed

REM Create necessary directories
echo Creating necessary directories...
if not exist "static" mkdir static
if not exist "logs" mkdir logs
if not exist "static\loginSystem" mkdir static\loginSystem
if not exist "static\userManagment" mkdir static\userManagment
echo [OK] Directories created

REM Set up Django
echo Setting up Django...
python manage.py collectstatic --noinput
if %errorLevel% neq 0 (
    echo [WARNING] Failed to collect static files, continuing...
)

REM Create superuser (optional)
echo.
echo ==========================================
echo User Account Setup
echo ==========================================
echo.
set /p CREATE_ADMIN="Do you want to create an admin user now? (y/n): "
if /i "%CREATE_ADMIN%"=="y" (
    echo Creating admin user...
    python manage.py createsuperuser
    if %errorLevel% neq 0 (
        echo [WARNING] Failed to create superuser
        echo You can create one later with: python manage.py createsuperuser
    ) else (
        echo [OK] Admin user created
    )
) else (
    echo [INFO] Skipping admin user creation
    echo You can create one later with: python manage.py createsuperuser
)

REM Create startup script
echo Creating startup script...
(
echo @echo off
echo cd /d "%CYBERPANEL_DIR%\cyberpanel"
echo call ..\Scripts\activate.bat
echo python manage.py runserver 0.0.0.0:8090
) > start_cyberpanel.bat

REM Create service script
echo Creating Windows service script...
(
echo @echo off
echo REM CyberPanel Windows Service
echo net start CyberPanel
echo if %%errorLevel%% neq 0 ^(
echo     echo Starting CyberPanel service...
echo     sc create CyberPanel binPath= "%CYBERPANEL_DIR%\cyberpanel\start_cyberpanel.bat" start= auto
echo     sc start CyberPanel
echo ^)
) > install_service.bat

echo.
echo ==========================================
echo Installation Complete!
echo ==========================================
echo.
echo CyberPanel has been installed to: %CYBERPANEL_DIR%\cyberpanel
echo.
echo To start CyberPanel:
echo 1. Run: start_cyberpanel.bat
echo 2. Open your browser to: http://localhost:8090
echo.
echo To install as Windows service:
echo 1. Run: install_service.bat as administrator
echo.
echo Default login credentials:
echo Username: admin
echo Password: 123456
echo.
echo IMPORTANT: Change the default password immediately!
echo.
echo For more information, see the documentation at:
echo https://cyberpanel.net/docs/
echo.
pause
