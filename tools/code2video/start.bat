@echo off
chcp 65001 >nul
rem Chay Code2Video Studio bang Git Bash (goi start.sh). Double-click de mo.
setlocal
cd /d "%~dp0"

set "GITBASH="
if exist "%ProgramFiles%\Git\bin\bash.exe" set "GITBASH=%ProgramFiles%\Git\bin\bash.exe"
if not defined GITBASH if exist "%ProgramFiles(x86)%\Git\bin\bash.exe" set "GITBASH=%ProgramFiles(x86)%\Git\bin\bash.exe"
if not defined GITBASH if exist "%LocalAppData%\Programs\Git\bin\bash.exe" set "GITBASH=%LocalAppData%\Programs\Git\bin\bash.exe"
if not defined GITBASH for /f "delims=" %%G in ('where git 2^>nul') do if not defined GITBASH if exist "%%~dpG..\bin\bash.exe" set "GITBASH=%%~dpG..\bin\bash.exe"

if not defined GITBASH (
  echo Khong tim thay Git Bash. Cai Git for Windows: https://git-scm.com/download/win
  pause
  exit /b 1
)

"%GITBASH%" "%~dp0start.sh" %*
if errorlevel 1 pause
endlocal
