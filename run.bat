@echo off
rem Start the Gatewell Parts Desk on http://localhost:8000
cd /d "%~dp0"
if not exist .venv (
  python -m venv .venv
  .venv\Scripts\pip install -q -r requirements.txt
)
if exist .env (
  for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env") do if not "%%b"=="" set "%%a=%%b"
)
echo Gatewell Parts Desk: http://localhost:8000
.venv\Scripts\python -m uvicorn app.server:app --port 8000
