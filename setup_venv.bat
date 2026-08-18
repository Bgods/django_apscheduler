@echo off
REM TaskHive - Setup Python virtual environment and install dependencies
echo Creating Python virtual environment...
python -m venv .venv
echo.
echo Activating virtual environment and installing dependencies...
call .venv\Scripts\activate
pip install -r requirements.txt
echo.
echo Setup complete!
echo.
pause