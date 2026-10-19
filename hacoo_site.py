"""Local browser interface; MuMu and this server must stay running on the PC."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import threading
import webbrowser

import bot
from hacoo_mumu import Adb, product_code
from hacoo_publish import history, run_auto, scan_channel
from hacoo_requests import find_announcements, parse_request

PAGE = '''<!doctype html><html lang="fr"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Erdezz · Hacoo</title><style>
body{margin:0;background:#10131b;color:#f6f7fb;font:16px system-ui;display:grid;min-height:100vh;place-items:center}
main{width:min(520px,88vw);padding:40px 0}small{color:#a9b3c9;letter-spacing:2px}h1{font-size:38px;margin:14px 0}
p{color:#b8c1d3;line-height:1.6}form{background:#1a2030;padding:26px;border-radius:20px;margin-top:26px}
label{display:block;margin:16px 0 8px}input{box-sizing:border-box;width:100%;padding:15px;border:1px solid #46516b;border-radius:10px;background:#10131b;color:white;font:inherit}
button{width:100%;padding:16px;background:#ff812f;color:#141414;border:0;border-radius:10px;font:700 16px system-ui;margin-top:24px;cursor:pointer}button:disabled{opacity:.45;cursor:wait}
#status{padding:16px 0;white-space:pre-wrap}a{color:#ffa361}.note{font-size:13px}#catalog{font-size:14px}</style>
<main><small>ERDEZZ / HACOO</small><h1>Un produit. Une publication.</h1>
<p>Ton lien affilie, les photos et le nom du produit, directement sur <a href="https://t.me/hacoolinks2k26" target="_blank" rel="noreferrer">ton canal</a>.</p>
<form id="form"><label for="code">Code Hacoo</label><input id="code" pattern="40[0-9]{5,6}" inputmode="numeric" placeholder="40125478" required>
<label for="name">Nom precis du modele</label><input id="name" minlength="3" maxlength="160" placeholder="Saucony Jazz" required>
<button id="send" disabled>Publier sur Telegram</button><div id="status" role="status" aria-live="polite">Chargement…</div></form>
<p id="catalog"></p><p class="note">Selection aleatoire parmi les annonces correspondantes, sans validation supplementaire. Le prix est conserve s'il est ecrit dans l'annonce. Sans prix disponible, aucun prix n'est ajoute.</p>
<p class="note">Garde ce programme et MuMu ouverts sur Link Customize. Le delai depend de Hacoo, des photos et de ta connexion.</p></main>
<script>
const token='__TOKEN__';let sending=false;
async function status(){try{const r=await fetch('/status');const s=await r.json();
document.querySelector('#catalog').textContent=s.catalog;
document.querySelector('#status').textContent=s.message;
document.querySelector('#send').disabled=sending||s.busy||!s.ready;
}catch(e){document.querySelector('#status').textContent='Connexion au programme perdue. Relance OUVRIR-SITE-HACOO.bat.';document.querySelector('#send').disabled=true;}}
document.querySelector('#form').onsubmit=async e=>{e.preventDefault();sending=true;document.querySelector('#send').disabled=true;
try{const r=await fetch('/publish',{method:'POST',headers:{'Content-Type':'application/json','X-Hacoo-Token':token},body:JSON.stringify({code:document.querySelector('#code').value.trim(),name:document.querySelector('#name').value.trim()})});
const s=await r.json();if(!r.ok){document.querySelector('#status').textContent=s.error;return;}await status();
}catch(e){document.querySelector('#status').textContent='Connexion interrompue. Verifie le statut et le canal avant de recommencer.';}finally{sending=false;}};
status();setInterval(status,1500);
</script></html>'''


class Application:
    def __init__(self, adb, telegram, base):
        self.adb, self.telegram, self.base = adb, telegram, base
        self.token = secrets.token_hex(32)
        self.lock = threading.Lock()
        self.posts = []
        self.ready = False
        self.busy = False
        self.message = 'Preparation des annonces… Le premier chargement peut prendre quelques minutes.'
        self.catalog = 'Lecture des sept sources…'
        self.stop = threading.Event()

    def snapshot(self):
        with self.lock:
            return dict(ready=self.ready, busy=self.busy, message=self.message, catalog=self.catalog)

    def report(self, message):
        with self.lock:
            self.message = message

    def refresh(self):
        while not self.stop.is_set():
            posts, failures = [], 0
            try:
                with ThreadPoolExecutor(max_workers=3) as pool:
                    for index, (found, failed) in enumerate(pool.map(scan_channel, bot.SOURCES), 1):
                        posts.extend(found)
                        failures += int(failed)
                        with self.lock:
                            self.catalog = f'Actualisation des annonces : {index}/7 sources consultees…'
                with self.lock:
                    if posts:
                        self.posts = posts
                        self.ready = True
                        if self.message.startswith('Preparation'):
                            self.message = 'Pret. Saisis le code et le modele du produit.'
                    self.catalog = f'{len(self.posts)} annonces en memoire · actualisation toutes les 10 minutes.'
                    if failures:
                        self.catalog += ' Certaines sources sont temporairement inaccessibles.'
                    if not self.ready:
                        self.catalog = 'Aucune annonce accessible. Nouvelle tentative dans une minute.'
            except Exception:
                with self.lock:
                    self.catalog = 'Actualisation impossible. Nouvelle tentative automatique.'
            self.stop.wait(600 if self.ready else 60)

    def search(self, name):
        with self.lock:
            posts = list(self.posts)
        return find_announcements(name, posts, limit=len(posts))

    def submit(self, code, name):
        if not isinstance(code, str) or not isinstance(name, str):
            raise ValueError('Indique le code et le nom du modele.')
        code = product_code(code)
        request = code + ', ' + name
        parse_request(request)
        with self.lock:
            if self.busy:
                raise ValueError('Une publication est deja en cours.')
            if not self.ready:
                raise ValueError('Les annonces sont encore en cours de chargement.')
            self.busy = True
            self.message = 'Publication en cours…'
        threading.Thread(target=self.publish, args=(request,), daemon=True).start()

    def publish(self, request):
        db = None
        try:
            db = history(self.base / 'history.sqlite3')
            result = run_auto(request, self.adb, self.telegram, db, self.search, self.report)
            self.report('Publie sur @hacoolinks2k26 : ' + result['title'])
        except (ValueError, RuntimeError) as error:
            self.report(str(error))
        except Exception:
            self.report('Operation interrompue. Verifie le canal avant de recommencer.')
        finally:
            if db is not None:
                db.close()
            with self.lock:
                self.busy = False


def make_server(app, port=0):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, data, kind='application/json'):
            body = (json.dumps(data, ensure_ascii=False) if kind == 'application/json' else data).encode()
            self.send_response(status)
            self.send_header('Content-Type', kind + '; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)

        def valid_host(self):
            return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'

        def do_GET(self):
            if not self.valid_host():
                return self.reply(403, {'error': 'Acces local uniquement.'})
            if self.path == '/':
                return self.reply(200, PAGE.replace('__TOKEN__', app.token), 'text/html')
            if self.path == '/status':
                return self.reply(200, app.snapshot())
            self.reply(404, {'error': 'Page introuvable.'})

        def do_POST(self):
            origin = f'http://127.0.0.1:{self.server.server_port}'
            if (not self.valid_host() or self.headers.get('Origin') != origin or
                    not secrets.compare_digest(self.headers.get('X-Hacoo-Token', ''), app.token)):
                return self.reply(403, {'error': 'Recharge la page locale pour continuer.'})
            if self.path != '/publish':
                return self.reply(404, {'error': 'Page introuvable.'})
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 4096:
                    raise ValueError('Demande trop longue ou vide.')
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError('Demande invalide.')
                app.submit(data.get('code'), data.get('name'))
            except (ValueError, UnicodeError) as error:
                return self.reply(400, {'error': str(error)})
            self.reply(202, {'accepted': True})

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.timeout = 1
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', required=True)
    parser.add_argument('--serial', required=True)
    args = parser.parse_args()
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise SystemExit('Utilise OUVRIR-SITE-HACOO.bat pour charger le jeton.')
    base = Path(os.getenv('LOCALAPPDATA', str(Path.home()))) / 'HacooAffiliate'
    base.mkdir(parents=True, exist_ok=True)
    telegram = bot.Telegram(token, bot.DESTINATION)
    telegram.check()
    with bot.instance_lock(base / 'publish.lock'):
        app = Application(Adb(args.adb, args.serial), telegram, base)
        server = make_server(app)
        threading.Thread(target=app.refresh, daemon=True).start()
        address = f'http://127.0.0.1:{server.server_port}'
        print('Page ouverte dans ton navigateur. Garde cette fenetre et MuMu ouverts.', flush=True)
        print(address, flush=True)
        webbrowser.open(address)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            app.stop.set()
            server.server_close()


if __name__ == '__main__':
    main()
