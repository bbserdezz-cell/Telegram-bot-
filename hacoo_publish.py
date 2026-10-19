"""Interactive local test: source announcement -> MuMu affiliate link -> Telegram."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sqlite3
import webbrowser

import bot
from hacoo_mumu import Adb, AutomationError, convert
from hacoo_requests import parse_request, find_announcements, prepare_affiliate_post, price_lines, PRICE_PATTERN


def scan_channel(channel, pages=30, name=None):
    posts = {}
    before = None
    failed = False
    for _ in range(pages):
        url = f'https://t.me/s/{channel}' + (f'?before={before}' if before else '')
        try:
            html = bot.fetch(url)
            for post in bot.parse_announcements(html):
                posts[post['source']] = post
            if name and len(find_announcements(name, list(posts.values()))) >= 5:
                break
            ids = []
            for node in bot.Document(html).root.walk():
                source = node.attrs.get('data-post', '')
                prefix, _, number = source.partition('/')
                if prefix.casefold() == channel.casefold() and number.isdigit():
                    ids.append(int(number))
            if not ids or min(ids) == before:
                break
            before = min(ids)
        except Exception:
            failed = True
            break
    return list(posts.values()), failed


def search(name):
    print('Recherche dans les 7 sources (jusqu a 30 pages par source, cela peut prendre quelques minutes)...', flush=True)
    posts = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        for channel, (found, failed) in zip(bot.SOURCES, pool.map(lambda c: scan_channel(c, name=name), bot.SOURCES)):
            print(f'@{channel} : {len(found)} annonces accessibles' + (' ; lecture incomplete' if failed else ''), flush=True)
            posts.extend(found)
    matches = find_announcements(name, posts, limit=len(posts))
    # Missing prices must be visible to the user, not silently hide matches.
    matches.sort(key=lambda post: not bool(price_lines(post)))
    return matches[:10]


def history(path):
    db = sqlite3.connect(path)
    db.execute('CREATE TABLE IF NOT EXISTS affiliate_deliveries ('
               'destination TEXT, code TEXT, state TEXT, payload TEXT, result TEXT, '
               'PRIMARY KEY(destination, code))')
    db.commit()
    return db


def ensure_new(db, destination, code):
    row = db.execute('SELECT state FROM affiliate_deliveries WHERE destination=? AND code=?',
                     (destination, code)).fetchone()
    if row:
        raise ValueError('Ce code est deja envoye ou son envoi est incertain. '
                         'Verifie le canal ; aucune nouvelle publication automatique.')


def publish_once(db, telegram, post):
    if not bot.good_announcement(post):
        raise ValueError('Annonce incomplete ou legende trop longue ; aucun envoi.')
    code = post['product_code']
    with db:
        db.execute('BEGIN IMMEDIATE')
        ensure_new(db, telegram.destination, code)
        db.execute('INSERT INTO affiliate_deliveries VALUES (?,?,?,?,?)',
                   (telegram.destination, code, 'pending', json.dumps(post), None))
    try:
        result = telegram.publish(post)
        with db:
            db.execute('UPDATE affiliate_deliveries SET state=?, result=? WHERE destination=? AND code=?',
                       ('sent', json.dumps(result), telegram.destination, code))
    except Exception:
        raise RuntimeError('Envoi non confirme. Verifie le canal avant toute autre tentative ; '
                           'ce code reste bloque pour eviter un doublon.') from None
    return result


def run(adb, telegram, db):
    code, name = parse_request(input('Code, nom du produit (exemple : 40763432, nike pegasus) : '))
    ensure_new(db, telegram.destination, code)
    telegram.check()
    matches = search(name)
    if not matches:
        raise ValueError('Aucune annonce avec ce nom et des photos dans les 30 pages maximum consultees par source. '
                         'Essaie un nom tel qu il apparait dans la source. Rien ne sera publie.')
    for index, post in enumerate(matches, 1):
        print(f"\n{index}. {bot.product_title(post)}\n" + ('\n'.join(price_lines(post)) or 'Prix non indique dans le texte'))
        print(f"   {len(post['photos'])} photo(s) — https://t.me/{post['source']}")
    choice = input('\nNumero de l annonce correspondant au produit (Entree pour annuler) : ').strip()
    if not choice:
        print('Annule, aucune publication.')
        return
    if not choice.isdigit() or not 1 <= int(choice) <= len(matches):
        raise ValueError('Numero invalide ; aucune publication.')
    original = matches[int(choice) - 1]
    source_url = 'https://t.me/' + original['source']
    print('Verifie les photos, la variante et le prix dans cette annonce : ' + source_url)
    try:
        webbrowser.open(source_url)
    except Exception:
        pass
    print('Le nom seul ne garantit pas que cette annonce correspond au code Hacoo.')
    if input('Tape OK si cette annonce correspond au produit, sinon Entree : ').strip().upper() != 'OK':
        print('Annule, aucune publication.')
        return
    if not price_lines(original):
        entered_price = input('Prix absent du texte. Entre le prix verifie sur Hacoo avec sa devise (ex. 29,90 EUR), ou Entree pour annuler : ').strip()
        if not entered_price:
            print('Annule : aucun prix invente, aucune publication.')
            return
        if not PRICE_PATTERN.fullmatch(entered_price):
            raise ValueError('Prix invalide. Indique uniquement le montant et la devise, par exemple 29,90 EUR.')
        original = {**original, 'text': original['text'] + '\n' + entered_price}
    print('Creation du lien dans MuMu. Laisse Hacoo ouvert sans cliquer...', flush=True)
    generated = convert(adb, code)
    post = prepare_affiliate_post(code, original, generated['affiliate_url'])
    if not bot.good_announcement(post):
        raise ValueError('Legende incomplete ou trop longue ; aucun envoi.')
    print('\nAnnonce pour ' + telegram.destination + ' :\n\n' + bot.announcement_text(post))
    print(f"\nAvec les {len(post['photos'])} photo(s) de l annonce choisie.")
    if input('Tape PUBLIER pour envoyer cette annonce, sinon Entree : ').strip().upper() != 'PUBLIER':
        print('Lien cree, publication annulee.')
        return
    publish_once(db, telegram, post)
    print('Annonce publiee : https://t.me/hacoolinks2k26')


def run_auto(request, adb, telegram, db, search_fn=search, report=print):
    code, name = parse_request(request)
    ensure_new(db, telegram.destination, code)
    report('Recherche de l annonce…')
    matches = search_fn(name)
    if not matches:
        raise ValueError('Aucune annonce correspondante avec photo. Essaie le nom exact du modele.')
    original = matches[0]
    report('Creation de ton lien affilie dans Hacoo…')
    generated = convert(adb, code)
    post = prepare_affiliate_post(code, original, generated['affiliate_url'])
    report('Envoi des photos et de la legende sur Telegram…')
    publish_once(db, telegram, post)
    return {'title': bot.product_title(post), 'source': original['source'],
            'channel': 'https://t.me/hacoolinks2k26'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', required=True)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--auto', action='store_true')
    args = parser.parse_args()
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise SystemExit('Jeton Telegram absent. Utilise PUBLIER-LIEN-HACOO.bat.')
    base = Path(os.getenv('LOCALAPPDATA', str(Path.home()))) / 'HacooAffiliate'
    base.mkdir(parents=True, exist_ok=True)
    try:
        with bot.instance_lock(base / 'publish.lock'):
            db = history(base / 'history.sqlite3')
            try:
                telegram = bot.Telegram(token, bot.DESTINATION)
                if args.auto:
                    telegram.check()
                    request = input('Code, nom du modele : ')
                    run_auto(request, Adb(args.adb, args.serial), telegram, db)
                    print('Annonce publiee sur @hacoolinks2k26.')
                else:
                    run(Adb(args.adb, args.serial), telegram, db)
            finally:
                db.close()
    except (ValueError, RuntimeError, AutomationError, OSError, sqlite3.Error, EOFError, KeyboardInterrupt) as error:
        if isinstance(error, (ValueError, RuntimeError)):
            raise SystemExit(str(error)) from None
        raise SystemExit('Test interrompu. Aucun nouvel essai automatique ; verifie le canal si un envoi etait en cours.') from None


if __name__ == '__main__':
    main()
