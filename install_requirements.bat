@echo off
REM TaskHive - install dependencies
echo Activating virtual environment and installing dependencies...
call .venv\Scripts\activate
pip install -r requirements.txt
echo.
echo Setup complete!
echo.
pause