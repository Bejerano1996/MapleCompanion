@echo off
python "%~dp0build_release.py" %*
exit /b %ERRORLEVEL%
