import os
import sys
import threading
import webbrowser

import uvicorn
import httpx
from local_models import ensure_server

if __name__ == '__main__':
    ensure_server()
    port = int(os.environ.get('POLICYBOT_PORT', '8765'))
    url = f'http://127.0.0.1:{port}'
    try:
        existing = httpx.get(url + '/openapi.json', timeout=2, trust_env=False).json()
        if existing.get('info', {}).get('title') == 'Policybot':
            print(f'Policybot is already running: {url}')
            if os.environ.get('POLICYBOT_NO_BROWSER') != '1':
                webbrowser.open(url)
            sys.exit(0)
    except (httpx.HTTPError, ValueError):
        pass
    print(f'Policybot: {url}\nKeep this window open. Press Ctrl+C to stop.')
    if os.environ.get('POLICYBOT_NO_BROWSER') != '1':
        threading.Timer(2, lambda: webbrowser.open(url)).start()
    uvicorn.run('main:app', host='127.0.0.1', port=port)
