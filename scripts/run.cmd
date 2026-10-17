@echo off
rem Windows equivalent of `make run` (scripts/run.sh)
setlocal
cd /d "%~dp0.."
for %%d in (artifacts data model-cache qdrant auth) do if not exist runtime\%%d mkdir runtime\%%d
if "%STEPWISE_AUTH_DIR%"=="" set "STEPWISE_AUTH_DIR=%CD%\runtime\auth"

docker compose up --build -d || exit /b 1
call gcloud.cmd auth print-access-token > "%STEPWISE_AUTH_DIR%\token" || exit /b 1

python scripts\verify.py
set RESULT=%ERRORLEVEL%
docker compose logs --no-color > runtime\artifacts\pipeline.log
docker compose ps -a --format json > runtime\artifacts\containers.jsonl
echo Stepwise is ready: http://localhost:8080 ^| API: http://localhost:8000/docs
exit /b %RESULT%
