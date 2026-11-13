@echo off
title BulkBite - Zero Delivery Fee Group Ordering
echo ========================================================
echo   🍔 Starting BulkBite Server
echo   Founder: KEDAR PATIL
echo ========================================================
echo   URL: http://localhost:8080
echo.
echo   Demo Logins (Password: hostel123):
echo     * Rahul Sharma: 9876543210 (Room 304)
echo     * Aman Verma:   9811223344 (Room 210)
echo     * Priya Nair:   9822334455 (Room 102)
echo ========================================================
cd /d "%~dp0"
python server.py
pause
