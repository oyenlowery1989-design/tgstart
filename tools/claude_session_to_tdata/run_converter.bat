@echo off
REM ============================================================================
REM Telethon to Telegram Desktop Converter - Windows Launcher
REM ============================================================================

echo.
echo ========================================================================
echo    TELETHON SESSION TO TELEGRAM DESKTOP CONVERTER
echo ========================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo.
    echo Please install Python from https://python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [OK] Python is installed
python --version
echo.

REM Check if the script exists
if not exist "session_to_tdata_converter.py" (
    echo [ERROR] Script file not found: session_to_tdata_converter.py
    echo.
    echo Please ensure the script is in the same folder as this batch file.
    echo.
    pause
    exit /b 1
)

echo [OK] Script file found
echo.

REM Check if required packages are installed
echo Checking dependencies...
python -c "import telethon" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Telethon is not installed
    echo.
    echo Installing required packages...
    echo This may take a few minutes...
    echo.
    
    REM Try to install with tgcrypto-pyrofork first
    pip install telethon opentele tgcrypto-pyrofork
    
    if errorlevel 1 (
        echo [WARNING] Installation with tgcrypto-pyrofork failed
        echo Trying alternative installation...
        pip install telethon opentele
    )
    
    echo.
    echo Installation complete!
    echo.
) else (
    echo [OK] Dependencies are installed
    echo.
)

REM Run the converter script
echo ========================================================================
echo    STARTING CONVERSION
echo ========================================================================
echo.
echo Press Ctrl+C to stop the keep-alive loop at any time.
echo All progress will be saved and logged to session_converter.log
echo.

python session_to_tdata_converter.py

echo.
echo ========================================================================
echo    SCRIPT COMPLETED
echo ========================================================================
echo.
echo Check session_converter.log for detailed information.
echo.
pause
