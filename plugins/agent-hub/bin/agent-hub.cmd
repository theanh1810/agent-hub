@echo off
rem agent-hub shim for Windows: run the dispatcher with py -3 when the launcher exists, else python.
where py >nul 2>nul
if errorlevel 1 goto usepython
py -3 "%~dp0agent-hub" %*
exit /b
:usepython
python "%~dp0agent-hub" %*
exit /b
