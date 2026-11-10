@echo off
setlocal
cd /d "%~dp0"
set "VENV=.venv312"
set "VP=%VENV%\Scripts\python.exe"
if exist "%VP%" (
    "%VP%" -c "import sys; raise SystemExit(sys.version_info[:2] != (3, 12))"
    if not errorlevel 1 goto install
    echo The existing .venv312 is not a working Python 3.12 environment.
    echo Rename that folder and run this launcher again.
    goto failed
)
where py >nul 2>nul
if not errorlevel 1 (
    py -3.12 -m venv "%VENV%"
    if not errorlevel 1 goto install
)
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m venv "%VENV%"
    if not errorlevel 1 goto install
)
if exist "%ProgramFiles%\Python312\python.exe" (
    "%ProgramFiles%\Python312\python.exe" -m venv "%VENV%"
    if not errorlevel 1 goto install
)
where python >nul 2>nul
if not errorlevel 1 (
    python -c "import sys; raise SystemExit(sys.version_info[:2] != (3, 12))"
    if not errorlevel 1 (
        python -m venv "%VENV%"
        if not errorlevel 1 goto install
    )
)
echo Python 3.12 could not be found. See README.md for the direct-path setup.
goto failed

:install
if exist "%VENV%\ehr_requirements.txt" (
    fc /b requirements.txt "%VENV%\ehr_requirements.txt" >nul
    if not errorlevel 1 (
        "%VP%" -c "import streamlit, shap, sklearn, numpy, pandas, filelock"
        if not errorlevel 1 goto launch
    )
)
echo Installing dashboard dependencies. This step requires internet access.
"%VP%" -m pip install -r requirements.txt
if errorlevel 1 goto failed
copy /y requirements.txt "%VENV%\ehr_requirements.txt" >nul

:launch
"%VP%" -m streamlit run app.py --server.headless true
if errorlevel 1 goto failed
exit /b 0

:failed
echo Setup or launch failed. See the message above and README.md.
pause
exit /b 1
