@echo off
REM Setup script for Virtuoso development environment on Windows

REM Ensure script is run from project root
if not exist "setup.py" (
    echo Error: This script must be run from the project root directory
    exit /b 1
)

REM Create virtual environment
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
) else (
    echo Virtual environment already exists.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing development dependencies...
pip install --upgrade pip
pip install -e .
pip install -r config/ci/requirements-test.txt

REM Install pre-commit hooks
echo Setting up pre-commit hooks...
pip install pre-commit
pre-commit install

REM Create .env file if it doesn't exist
if not exist ".env" (
    echo Creating .env file from template...
    copy config\.env.example .env
    echo Please update .env with your configuration values.
)

REM Display success message
echo.
echo === Virtuoso Development Environment Setup Complete ===
echo To activate the virtual environment, run:
echo   venv\Scripts\activate.bat
echo.
echo To run tests:
echo   pytest -c config/ci/pytest.ini
echo. 