"""Run a separate loopback Ollama server with models stored inside this project."""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ADDRESS = '127.0.0.1:11435'
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def environment():
    env = os.environ.copy()
    env['OLLAMA_HOST'] = ADDRESS
    env['OLLAMA_MODELS'] = str(ROOT / 'models')
    env['OLLAMA_NO_CLOUD'] = '1'
    temporary = ROOT / 'data' / 'tmp'
    temporary.mkdir(parents=True, exist_ok=True)
    env['TEMP'] = env['TMP'] = env['TMPDIR'] = str(temporary)
    return env


def online():
    try:
        with OPENER.open('http://' + ADDRESS + '/api/tags', timeout=2) as response:
            json.load(response)
        return True
    except (OSError, ValueError, urllib.error.URLError):
        return False


def ensure_server():
    if online():
        return
    executable = shutil.which('ollama')
    if not executable:
        raise SystemExit('Install Ollama from https://ollama.com/download/windows, then run setup.bat.')
    (ROOT / 'models').mkdir(exist_ok=True)
    (ROOT / 'data').mkdir(exist_ok=True)
    with (ROOT / 'data' / 'ollama.log').open('ab') as log:
        subprocess.Popen([executable, 'serve'], env=environment(), stdout=log, stderr=log,
                         creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    for _ in range(60):
        if online():
            return
        time.sleep(0.5)
    raise SystemExit('Local models could not start. Check data/ollama.log. Port 11435 must be available.')


if __name__ == '__main__':
    ensure_server()
    if '--pull' in sys.argv:
        for model in ('qwen2.5:3b', 'nomic-embed-text'):
            subprocess.run(['ollama', 'pull', model], env=environment(), check=True)
