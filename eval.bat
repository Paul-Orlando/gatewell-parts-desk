@echo off
rem Run the assistant evaluation (tests\eval\run_eval.py) with the key from .env, the same way run.bat starts the app.
rem Arguments pass through, e.g.  eval.bat --limit 3 --runs 1   or   eval.bat --group restricted
rem Nothing from .env is ever printed: echo stays off, and the variables only live inside this script (setlocal).
setlocal
cd /d "%~dp0"
if exist .env (
  for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env") do if not "%%b"=="" set "%%a=%%b"
)
if not defined OPENROUTER_API_KEY (
  echo OPENROUTER_API_KEY is not set in .env
  exit /b 2
)
if not exist .venv\Scripts\python.exe (
  echo The virtual environment is missing. Run run.bat once to create it.
  exit /b 2
)
.venv\Scripts\python tests\eval\run_eval.py %*
exit /b %errorlevel%
