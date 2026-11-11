#!/usr/bin/env python3
"""Run the sim on this machine and keep a copy of your scene on disk.

    python3 serve.py [port]        # default 8765, reachable from this machine only

It serves sim/ like `python3 -m http.server`, and adds:

    GET /autosave   the last scene the sim saved (scenes/autosave.json); 204 (empty) if there is none yet
    PUT /autosave   the sim sends its scene after every change. It is written in one step
                    (never half a file), and a timed backup goes to scenes/autosave-backups/
                    (one every 10 minutes, the newest 30 kept).
    PUT /autosave?backup=1   the same, plus a backup straight away: the sim sends this just before it
                    switches to another project, so the scene you leave is always kept.

Why: browser storage alone isn't safe. The Claude app's browser pane loses it when the app
restarts, and a scene was lost that way on 2026-11-09. The public site (GitHub Pages) has no
server, so there the sim keeps using browser storage only.
"""
import datetime
import http.server
import json
import os
import shutil
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.join(HERE, 'sim')
SCENES = os.path.join(HERE, 'scenes')
AUTOSAVE = os.path.join(SCENES, 'autosave.json')
BACKUPS = os.path.join(SCENES, 'autosave-backups')
BACKUP_EVERY_S = 600
KEEP_BACKUPS = 30
MAX_BYTES = 8_000_000


def backup_if_due(now=False):
    os.makedirs(BACKUPS, exist_ok=True)
    names = sorted(n for n in os.listdir(BACKUPS) if n.startswith('autosave-') and n.endswith('.json'))
    newest = os.path.getmtime(os.path.join(BACKUPS, names[-1])) if names else 0
    if now or time.time() - newest >= BACKUP_EVERY_S:
        stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        shutil.copyfile(AUTOSAVE, os.path.join(BACKUPS, f'autosave-{stamp}.json'))
        names.append(f'autosave-{stamp}.json')
    for old in names[:-KEEP_BACKUPS]:
        os.remove(os.path.join(BACKUPS, old))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SIM, **kwargs)

    def end_headers(self):
        # Always fetch fresh files, so a reload picks up new code; and tell the sim this server keeps a disk copy.
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-BSPK-Autosave', '1')
        super().end_headers()

    def do_GET(self):
        if self.path.split('?')[0] != '/autosave':
            return super().do_GET()
        if not os.path.exists(AUTOSAVE):   # nothing saved yet: answer quietly (an error would show in the browser console)
            self.send_response(204)
            self.end_headers()
            return
        with open(AUTOSAVE, 'rb') as f:
            body = f.read()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_PUT(self):
        if self.path.split('?')[0] != '/autosave':
            return self.send_error(404)
        n = int(self.headers.get('Content-Length') or 0)
        if n <= 0 or n > MAX_BYTES:
            return self.send_error(413, 'empty or too large')
        body = self.rfile.read(n)
        try:
            data = json.loads(body)
        except ValueError:
            return self.send_error(400, 'not JSON')
        if not isinstance(data, dict) or data.get('format') != 'bspk-studio-scene' or not isinstance(data.get('state'), dict):
            return self.send_error(400, 'not a BSPK Studio scene')
        os.makedirs(SCENES, exist_ok=True)
        tmp = f'{AUTOSAVE}.{threading.get_ident()}.tmp'   # its own temp file, in case two saves overlap
        with open(tmp, 'wb') as f:
            f.write(body)
        os.replace(tmp, AUTOSAVE)   # one step: the file is always a whole scene
        backup_if_due(now='backup=1' in self.path.partition('?')[2].split('&'))
        self.send_response(204)
        self.end_headers()

    def log_message(self, fmt, *args):
        if not (self.command == 'PUT' and len(args) > 1 and str(args[1]).startswith('2')):   # keep the console quiet on routine saves
            super().log_message(fmt, *args)


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    server = http.server.ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print(f'BSPK Studio on http://localhost:{port}/  ·  scene saved to {AUTOSAVE}')
    server.serve_forever()
