"""Refresh a short-lived gcloud token in memory-backed storage. Never prints tokens."""
import os
import subprocess
import time
from pathlib import Path

folder=Path(os.getenv('STEPWISE_AUTH_DIR','/dev/shm/stepwise-auth'))
folder.mkdir(mode=0o700,parents=True,exist_ok=True)
os.chmod(folder,0o700)
while True:
    result=subprocess.run(['gcloud','auth','print-access-token','--quiet'],capture_output=True,text=True)
    if result.returncode==0 and result.stdout.strip():
        temporary=folder/'token.tmp'
        descriptor=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(descriptor,'w') as handle: handle.write(result.stdout.strip())
        temporary.replace(folder/'token')
        print('Stepwise runtime Google authorization refreshed.',flush=True)
    else: print('Stepwise runtime authorization refresh failed; inspect gcloud sign-in.',flush=True)
    time.sleep(1200)
