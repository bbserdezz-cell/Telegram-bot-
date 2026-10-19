"""Local browser interface; MuMu and this server must stay running on the PC."""
import argparse
import csv
import io
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import threading
import webbrowser

import bot
from hacoo_mumu import Adb, product_code
from hacoo_publish import history, run_auto, search_first
from hacoo_requests import parse_request


def parse_batch(text):
    if not isinstance(text, str) or len(text.encode('utf-8')) > 100000:
        raise ValueError('Fichier trop volumineux : maximum 100 Ko.')
    requests, seen = [], {}
    for number, line in enumerate(text.lstrip('\ufeff').splitlines(), 1):
        if not line.strip():
            continue
        separator = next((s for s in [',', ';', '|', '\t'] if s in line), ',')
        try:
            fields = next(csv.reader(io.StringIO(line), delimiter=separator, strict=True))
            if not requests and len(fields) == 2 and fields[0].strip().lower() == 'code' and fields[1].strip().lower() in ('nom', 'article', 'name'):
                continue
            if len(fields) != 2:
                raise ValueError('Il faut deux colonnes : code et nom.')
            code = product_code(fields[0])
            code, name = parse_request(code + ', ' + fields[1])
        except (ValueError, csv.Error):
            raise ValueError(f'Ligne {number} invalide. Format attendu : 40125478, Saucony Jazz') from None
        if code in seen:
            if seen[code] != name:
                raise ValueError(f'Ligne {number} : le meme code a deux noms differents.')
            continue
        seen[code] = name
        requests.append(code + ', ' + name)
        if len(requests) > 100:
            raise ValueError('Maximum 100 produits par fichier.')
    if not requests:
        raise ValueError('Le fichier ne contient aucun produit.')
    return requests

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
<button id="send" disabled>Publier sur Telegram</button></form>
<form id="batch"><label for="file">Ou importer une liste (.txt ou .csv)</label>
<input id="file" type="file" accept=".txt,.csv,text/plain,text/csv" required>
<p class="note">Une ligne par produit : code, nom du modele. Maximum 100 produits. Ils seront publies un par un, dans l'ordre du fichier.</p>
<button id="sendfile" disabled>Importer et publier la liste</button></form>
<div id="status" role="status" aria-live="polite">Chargement…</div><ol id="results"></ol>
<p id="catalog"></p><p class="note">La recherche commence a l'envoi du produit. La premiere annonce correspondante trouvee est utilisee, sans validation supplementaire. Le prix est conserve s'il est ecrit dans l'annonce. Sans prix disponible, aucun prix n'est ajoute.</p>
<p class="note">Garde ce programme et MuMu ouverts sur Link Customize. Le delai depend de Hacoo, des photos et de ta connexion.</p></main>
<script>
const token='__TOKEN__';let sending=false,clientError='';
function disable(value){document.querySelector('#send').disabled=value;document.querySelector('#sendfile').disabled=value;}
async function status(){try{const r=await fetch('/status');const s=await r.json();
document.querySelector('#catalog').textContent=s.catalog;
document.querySelector('#status').textContent=clientError||s.message;
disable(sending||s.busy||!s.ready);
const list=document.querySelector('#results');list.replaceChildren();
for(const row of s.results||[]){const item=document.createElement('li');item.textContent=row.product+' — '+row.state;list.appendChild(item);}
}catch(e){document.querySelector('#status').textContent='Connexion au programme perdue. Relance OUVRIR-SITE-HACOO.bat.';disable(true);}}
async function send(path,data){sending=true;clientError='';disable(true);
try{const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Hacoo-Token':token},body:JSON.stringify(data)});
const s=await r.json();if(!r.ok)clientError=s.error;
}catch(e){clientError='Connexion interrompue. Verifie le statut et le canal avant de recommencer.';}
finally{sending=false;await status();}}
document.querySelector('#form').onsubmit=e=>{e.preventDefault();send('/publish',{code:document.querySelector('#code').value.trim(),name:document.querySelector('#name').value.trim()});};
document.querySelector('#batch').onsubmit=async e=>{e.preventDefault();const file=document.querySelector('#file').files[0];
if(!file||file.size>100000){clientError='Choisis un fichier texte de moins de 100 Ko.';await status();return;}
try{const text=await file.text();await send('/batch',{text});}catch(e){clientError='Impossible de lire ce fichier. Enregistre-le en texte UTF-8.';await status();}};
status();setInterval(status,1500);
</script></html>'''


class Application:
    def __init__(self, adb, telegram, base):
        self.adb, self.telegram, self.base = adb, telegram, base
        self.token = secrets.token_hex(32)
        self.lock = threading.Lock()
        self.ready = True
        self.busy = False
        self.message = 'Pret. Saisis un produit ou importe ton fichier.'
        self.catalog = f'Recherche a la demande dans {len(bot.SOURCES)} canaux.'
        self.results = []

    def snapshot(self):
        with self.lock:
            return dict(ready=self.ready, busy=self.busy, message=self.message, catalog=self.catalog,
                        results=[dict(row) for row in self.results])

    def report(self, message):
        with self.lock:
            self.message = message

    def search(self, name):
        return search_first(name)

    def submit(self, code, name):
        if not isinstance(code, str) or not isinstance(name, str):
            raise ValueError('Indique le code et le nom du modele.')
        code = product_code(code)
        request = code + ', ' + name
        parse_request(request)
        self.start_requests([request])

    def submit_batch(self, text):
        self.start_requests(parse_batch(text))

    def start_requests(self, requests):
        with self.lock:
            if self.busy:
                raise ValueError('Une publication est deja en cours.')
            if not self.ready:
                raise ValueError('Les annonces sont encore en cours de chargement.')
            self.busy = True
            self.message = 'Publication en cours…'
            self.results = [dict(product=request, state='En attente') for request in requests]
        threading.Thread(target=self.publish_batch, args=(requests,), daemon=True).start()

    def publish(self, request):
        self.publish_batch([request])

    def publish_batch(self, requests):
        db = None
        try:
            db = history(self.base / 'history.sqlite3')
            for index, request in enumerate(requests):
                with self.lock:
                    if index < len(self.results):
                        self.results[index]['state'] = 'En cours'
                try:
                    run_auto(request, self.adb, self.telegram, db, self.search,
                             lambda message: self.report(f'{index + 1}/{len(requests)} — {message}'))
                    state = 'Publie'
                except ValueError as error:
                    state = 'Ignore : ' + str(error)
                with self.lock:
                    if index < len(self.results):
                        self.results[index]['state'] = state
            self.report('Traitement termine. Consulte le resultat de chaque produit ci-dessous.')
        except RuntimeError as error:
            self.report('Traitement arrete : ' + str(error))
        except Exception:
            self.report('Operation interrompue. Verifie le canal avant de recommencer.')
        finally:
            if db is not None:
                db.close()
            with self.lock:
                for row in self.results:
                    if row['state'] == 'En cours':
                        row['state'] = 'Erreur — verifier le message et le canal'
                    elif row['state'] == 'En attente':
                        row['state'] = 'Non traite — lot interrompu'
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
            if self.path not in ('/publish', '/batch'):
                return self.reply(404, {'error': 'Page introuvable.'})
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= (200000 if self.path == '/batch' else 4096):
                    raise ValueError('Demande trop longue ou vide.')
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError('Demande invalide.')
                if self.path == '/batch':
                    app.submit_batch(data.get('text'))
                else:
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
        address = f'http://127.0.0.1:{server.server_port}'
        print('Page ouverte dans ton navigateur. Garde cette fenetre et MuMu ouverts.', flush=True)
        print(address, flush=True)
        webbrowser.open(address)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()


if __name__ == '__main__':
    main()
