@echo off
title BulkBite - Public Cloud Launch
echo ==========================================================
echo   🍔 BulkBite - Zero Delivery Fee Group Ordering
echo   Founder: KEDAR PATIL
echo ==========================================================
echo.
echo [1/2] Starting BulkBite Server...
start "BulkBite Server" python server.py
timeout /t 2 >nul

echo [2/2] Connecting to Cloud Tunnel...
echo ==========================================================
echo  Your Public HTTPS link will appear below.
echo  Share that link with anyone in your hostel!
echo ==========================================================
echo.
ssh -p 443 -o StrictHostKeyChecking=no -R0:localhost:8080 a.pinggy.io
pause
