@echo off
REM ============================================
REM Claude Memory HTTP Server Launcher for Windows
REM ============================================
REM This script starts the Claude Memory HTTP server
REM for use with Claude Code on Windows.
REM
REM Windows has known issues with stdio transport,
REM so HTTP transport is required.
REM ============================================

title Claude Memory Server

REM Change to the script's directory
cd /d "%~dp0"

echo.
echo ============================================
echo Claude Memory Server
echo Port: 9876
echo ============================================
echo.

REM Start the server
python start_server.py --port 9876

REM If the server exits, pause so user can see any errors
if errorlevel 1 (
    echo.
    echo [ERROR] Server exited with an error. Press any key to close.
    pause >nul
)
