@echo off
echo ==============================================
echo   UP Funds - Office Money Collection System
echo ==============================================
echo.
echo Starting the server...
echo.

:: Open the browser after a 3-second delay in the background
start /B cmd /c "ping 127.0.0.1 -n 4 > nul & start http://127.0.0.2:5001"

:: Start the Python Flask app in the current window
echo Press Ctrl+C to close the server and shut down.
python app.py

pause
