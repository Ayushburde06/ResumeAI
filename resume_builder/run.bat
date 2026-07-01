@echo off
:: ─────────────────────────────────────────────────────────────────
::  Agentic Resume Builder — one-command runner
::  Edit resume_data.json, then run this file to get resume.docx
::
::  Usage:
::    run.bat               — standard generate + verify
::    run.bat --stress-test — run all 3 stress tests (A/B/C)
::    run.bat --max-iter 8  — allow more self-correction iterations
:: ─────────────────────────────────────────────────────────────────

cd /d "%~dp0"

:: Use Python 3.13 (system install with all required packages)
set PYTHON=C:\Users\Ayush123\AppData\Local\Programs\Python\Python313\python.exe
if not exist %PYTHON% set PYTHON=python

:: First-run setup: install any missing packages
%PYTHON% -c "import docx, pypdfium2, PIL, playwright, jsonschema" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Installing required packages...
    %PYTHON% -m pip install -r requirements.txt --quiet
    echo Installing Playwright Chromium...
    %PYTHON% -m playwright install chromium
)

:: Run the pipeline
%PYTHON% generate.py %*

:: Open the output folder in Explorer
if exist output\resume.docx (
    echo.
    echo Opening output folder...
    explorer output
)
