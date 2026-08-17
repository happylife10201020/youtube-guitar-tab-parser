@echo off
REM ============================================================
REM  Builds the Windows exe. Requires Python 3.10+ on PATH (sys.stdlib_module_names
REM  needs 3.10+).
REM
REM  Two build modes:
REM    build_windows.bat            -> dev build (GuitarTabParserDev.exe,
REM                                    verbose Details log box)
REM    set RELEASE=1 first          -> release build (GuitarTabParser.exe,
REM                                    no Details box; logs go to a file)
REM
REM  yt-dlp is NOT frozen into the exe: it ships as a wheel data file,
REM  is extracted to %LOCALAPPDATA% on first run, and auto-updates from
REM  PyPI in the background (see ytdlp_runtime.py).
REM ============================================================
setlocal
cd /d "%~dp0"

if defined RELEASE (
  set "NAME=GuitarTabParser"
  set "MODE=release"
) else (
  set "NAME=GuitarTabParserDev"
  set "MODE=dev"
)
echo Building %NAME% (%MODE% mode)...

echo Setting up build environment...
python -m venv .venv || goto :err
call ".venv\Scripts\activate.bat" || goto :err
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller || goto :err

echo Fetching the yt-dlp wheel to ship with the app...
if not exist "build_assets" mkdir "build_assets"
python -m pip download yt-dlp --no-deps --dest build_assets --quiet || goto :err
for %%F in (build_assets\yt_dlp-*.whl) do copy /y "%%F" "build_assets\ytdlp.whl" >nul

REM Baked-in build flavor (see app.py).
if "%MODE%"=="release" (
  echo IS_RELEASE = True> build_config.py
) else (
  echo IS_RELEASE = False> build_config.py
)

REM Build in an ASCII temp folder so non-English paths (e.g. Korean folder
REM names) never trip up PyInstaller, then copy the exe back into dist\.
set "BUILDDIR=%TEMP%\gtp_build"
if exist "%BUILDDIR%" rmdir /s /q "%BUILDDIR%"
mkdir "%BUILDDIR%\src"
copy /y *.py "%BUILDDIR%\src\" >nul
copy /y "build_assets\ytdlp.whl" "%BUILDDIR%\src\ytdlp.whl" >nul

REM The full standard library goes in as hidden imports: the runtime-loaded
REM yt-dlp (any future version) may need stdlib modules the app itself never
REM references, and PyInstaller would otherwise prune them.
for /f "delims=" %%A in ('python -c "import sys; skip={'antigravity','this','idlelib','turtledemo','turtle','test'}; print(' '.join('--hidden-import='+m for m in sys.stdlib_module_names if not m.startswith('_') and m not in skip))"') do set "STDLIB_HIDDEN=%%A"

pushd "%BUILDDIR%\src"
python -m PyInstaller --noconfirm --onefile --windowed --name %NAME% ^
  --exclude-module yt_dlp ^
  --add-data "%BUILDDIR%\src\ytdlp.whl;." ^
  --collect-all certifi ^
  --collect-all requests ^
  --collect-all urllib3 ^
  --collect-all websockets ^
  --collect-all mutagen ^
  --collect-all Cryptodome ^
  --hidden-import brotli ^
  %STDLIB_HIDDEN% ^
  --workpath "%BUILDDIR%\work" --distpath "%BUILDDIR%\dist" --specpath "%BUILDDIR%" app.py || (popd & goto :err)
popd

if not exist "dist" mkdir "dist"
copy /y "%BUILDDIR%\dist\%NAME%.exe" "dist\%NAME%.exe" >nul

echo.
echo ============================================================
echo  Done!  Your app is here:  dist\%NAME%.exe
echo  Share that single .exe file. Nothing else is needed.
echo ============================================================
pause
exit /b 0

:err
echo.
echo Build failed. Make sure Python 3.10+ is installed and on PATH.
pause
exit /b 1
