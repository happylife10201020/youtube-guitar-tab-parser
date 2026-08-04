@echo off
REM ============================================================
REM  Builds GuitarTabParser.exe -- a single, click-to-run app.
REM  You only need this if you want to REBUILD the exe yourself.
REM  Requires Python 3.8+ installed and on PATH.
REM  The person you share the exe with needs NOTHING installed.
REM ============================================================
setlocal
cd /d "%~dp0"

echo Setting up build environment...
python -m venv .venv || goto :err
call ".venv\Scripts\activate.bat" || goto :err
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller || goto :err

REM Build in an ASCII temp folder so non-English paths (e.g. Korean folder
REM names) never trip up PyInstaller, then copy the exe back into dist\.
set "BUILDDIR=%TEMP%\gtp_build"
if exist "%BUILDDIR%" rmdir /s /q "%BUILDDIR%"
mkdir "%BUILDDIR%\src"
copy /y *.py "%BUILDDIR%\src\" >nul

pushd "%BUILDDIR%\src"
python -m PyInstaller --noconfirm --onefile --windowed --name GuitarTabParser ^
  --collect-all yt_dlp ^
  --workpath "%BUILDDIR%\work" --distpath "%BUILDDIR%\dist" --specpath "%BUILDDIR%" app.py || (popd & goto :err)
popd

if not exist "dist" mkdir "dist"
copy /y "%BUILDDIR%\dist\GuitarTabParser.exe" "dist\GuitarTabParser.exe" >nul

echo.
echo ============================================================
echo  Done!  Your app is here:  dist\GuitarTabParser.exe
echo  Share that single .exe file. Nothing else is needed.
echo ============================================================
pause
exit /b 0

:err
echo.
echo Build failed. Make sure Python 3.8+ is installed and on PATH.
pause
exit /b 1
