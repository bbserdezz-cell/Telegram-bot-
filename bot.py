"""Public Telegram announcement collector and scheduled publisher (Python 3.12+)."""
import argparse
from contextlib import contextmanager
import hashlib
import html
import json
import logging
import os
from pathlib import Path
import random
import re
import sqlite3
import time
import urllib.error
import urllib.request
import urllib.parse
import uuid
from html.parser import HTMLParser

SOURCES = ['haccoyeplinks', 'hacoo_hacco_links_enlaces', 'hacoou', 'HacooT',
           'pdgdehco', 'hacoolinksyyep', 'princedehacoo']
DESTINATION = '@hacoolinks2k26'
INTERVAL = 45 * 60
BATCH_SIZE = 15
LOG = logging.getLogger('reposter')


class Node:
    def __init__(self, tag='', attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def has_class(self, name):
        return name in self.attrs.get('class', '').split()

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.walk()

    def text(self):
        if self.tag == 'br':
            return '\n'
        value = ''.join(c.text() if isinstance(c, Node) else c for c in self.children)
        if self.tag == 'a':
            href = self.attrs.get('href', '')
            if href.startswith(('https://', 'http://')) and href != value.strip():
                value += f' ({href})'
        return value


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
                       'link', 'meta', 'param', 'source', 'track', 'wbr'}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def parse_announcements(html):
    result = []
    for msg in Document(html).root.walk():
        if not msg.has_class('tgme_widget_message') or not msg.attrs.get('data-post'):
            continue
        nodes = list(msg.walk())
        # Video, audio and inaccessible media cannot be faithfully copied by this version.
        if any(n.tag in {'video', 'audio'} or n.has_class('tgme_widget_message_video_player')
               or n.has_class('tgme_widget_message_document_wrap')
               or n.has_class('message_media_not_supported') for n in nodes):
            continue
        text = '\n'.join(n.text().strip() for n in nodes
                         if n.has_class('tgme_widget_message_text')).strip()
        photos = []
        for n in nodes:
            if n.has_class('tgme_widget_message_photo_wrap'):
                match = re.search(r'url\([\'"]?(.*?)[\'"]?\)', n.attrs.get('style', ''))
                if match and match[1].startswith('https://') and match[1] not in photos:
                    photos.append(match[1])
        # Only announcements with an external HTTP(S) link are selected.
        links = sorted(set(re.findall(r'https?://[^\s<>\)]+', text)))
        links = [u for u in links if urllib.parse.urlsplit(u).hostname not in {'t.me', 'telegram.me'}]
        if not text or not links:
            continue
        result.append({'source': msg.attrs['data-post'], 'text': text,
                       'photos': photos, 'links': links})
    return result


PROMO_FOOTER = '-15% : Erdezz14 ‼️'
URL_PATTERN = re.compile(r'https?://[^\s<>\)]+')
PROMO_PATTERN = re.compile(
    r'(?i)\b(?:code(?:\s+(?:promo(?:tionnel)?|de\s+r[ée]duction|de\s+remise))?'
    r'|c[oó]digo|coupon|discount\s+code|codice)\b|[-−]\s*15\s*%')


def product_title(post):
    """Extract a short product name; never reuse source slogans or hashtag lists."""
    for line in post['text'].splitlines():
        if PROMO_PATTERN.search(line) or re.search(r'(?i)bio|\bDM\b|\bMD\b', line):
            continue
        line = URL_PATTERN.sub('', line)
        line = re.sub(r'(?<!\w)#[\w]+|(?<!\w)@[\w]+', '', line)
        line = re.sub(r'^[^\w]+', '', line).strip()
        if len(re.findall(r'[^\W\d_]', line)) < 3:
            continue
        if re.fullmatch(r'(?i)(?:link|lien|enlace|lien de l.article)\s*[:=]?', line):
            continue
        return line[:160].strip()
    return ''


def announcement_text(post):
    """Use the same channel template for every product without source hashtags."""
    title = product_title(post)
    links = list(dict.fromkeys(post['links']))
    return (title + '\n\n'
            + '\n'.join(links) + '\n\n' + PROMO_FOOTER)


def caption(post):
    text = announcement_text(post)
    title, separator, rest = text.partition('\n')
    return '<b>' + html.escape(title) + '</b>' + (separator + html.escape(rest) if separator else '')


def good_announcement(post):
    text = announcement_text(post)
    return (1 <= len(post['photos']) <= 10 and bool(post['links'])
            and bool(product_title(post))
            and len(text.encode('utf-16-le')) // 2 <= 1024)


def connect(path):
    db = sqlite3.connect(path)
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
        CREATE TABLE IF NOT EXISTS posts (
            source TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, payload TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'new');
        CREATE TABLE IF NOT EXISTS used_links (url TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS deliveries (source TEXT NOT NULL, message_id INTEGER NOT NULL, PRIMARY KEY(source,message_id));
    ''')
    return db


def ingest(db, posts):
    with db:
        for post in posts:
            fingerprint = hashlib.sha256(re.sub(r'\s+', ' ', post['text']).strip().encode()).hexdigest()
            db.execute('INSERT OR IGNORE INTO posts(source,fingerprint,payload) VALUES (?,?,?)',
                       (post['source'], fingerprint, json.dumps(post, ensure_ascii=False)))


def choose(db, limit=BATCH_SIZE):
    used = {row[0] for row in db.execute('SELECT url FROM used_links')}
    fingerprints = {row[0] for row in db.execute("SELECT fingerprint FROM posts WHERE state != 'new'")}
    rows = list(db.execute("SELECT source,fingerprint,payload FROM posts WHERE state='new'"))
    random.SystemRandom().shuffle(rows)
    selected = []
    for source, fingerprint, payload in rows:
        post = json.loads(payload)
        if not good_announcement(post) or fingerprint in fingerprints or used.intersection(post['links']):
            continue
        selected.append((source, post))
        fingerprints.add(fingerprint)
        used.update(post['links'])
        if len(selected) == limit:
            break
    return selected


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read().decode('utf-8')


def collect(db):
    succeeded = 0
    for channel in SOURCES:
        try:
            posts = parse_announcements(fetch(f'https://t.me/s/{channel}'))
            ingest(db, posts)
            LOG.info('@%s: %d annonces accessibles', channel, len(posts))
            succeeded += bool(posts)
        except Exception as error:
            # Do not log request URLs/exceptions: API URLs can contain credentials.
            LOG.error('@%s: lecture impossible (%s)', channel, type(error).__name__)
        time.sleep(1)
    return succeeded


def download_image(url):
    host = urllib.parse.urlsplit(url).hostname or ''
    if not url.startswith('https://') or not (host.endswith('.telesco.pe') or host.endswith('.cdn-telegram.org')):
        raise RuntimeError('Hôte image non reconnu')
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://t.me/'})
    with urllib.request.urlopen(request, timeout=45) as response:
        data = response.read(10 * 1024 * 1024 + 1)
        content_type = response.headers.get_content_type()
    if len(data) > 10 * 1024 * 1024 or not content_type.startswith('image/'):
        raise RuntimeError('Image trop volumineuse ou type non reconnu')
    return data, content_type


def multipart(payload, files):
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in payload.items():
        value = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
        parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n').encode())
    for name, (data, content_type) in files.items():
        parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="photo.jpg"\r\nContent-Type: {content_type}\r\n\r\n').encode())
        parts.extend([data, b'\r\n'])
    parts.append(f'--{boundary}--\r\n'.encode())
    return b''.join(parts), f'multipart/form-data; boundary={boundary}'


class Telegram:
    def __init__(self, token, destination):
        self.token, self.destination = token, destination

    def call(self, method, **payload):
        files = payload.pop('_files', None)
        data, content_type = multipart(payload, files) if files else (json.dumps(payload).encode(), 'application/json')
        request = urllib.request.Request(
            f'https://api.telegram.org/bot{self.token}/{method}',
            data=data, headers={'Content-Type': content_type})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.load(response)
        except Exception:
            raise RuntimeError(f'Telegram: échec de {method}; vérifier accès, droits et jeton') from None
        if not data.get('ok'):
            raise RuntimeError(f'Telegram: {method} refusé')
        return data['result']

    def check(self):
        me = self.call('getMe')
        chat = self.call('getChat', chat_id=self.destination)
        member = self.call('getChatMember', chat_id=self.destination, user_id=me['id'])
        if chat['type'] != 'channel' or not (member['status'] == 'creator' or (
                member['status'] == 'administrator' and member.get('can_post_messages'))):
            raise RuntimeError('Le bot doit être administrateur du canal avec le droit de publier')

    def publish(self, post):
        if not good_announcement(post):
            raise ValueError('Annonce sans photo, description exploitable ou légende trop longue')
        images = [download_image(url) for url in post['photos']]
        text = caption(post)
        if len(images) == 1:
            return self.call('sendPhoto', chat_id=self.destination, photo='attach://photo0',
                      caption=text, parse_mode='HTML', _files={'photo0': images[0]})
        else:
            media = [{'type': 'photo', 'media': f'attach://photo{j}'} for j in range(len(images))]
            media[0].update(caption=text, parse_mode='HTML')
            return self.call('sendMediaGroup', chat_id=self.destination, media=media,
                      _files={f'photo{j}': image for j, image in enumerate(images)})


def run_batch(db, telegram, now=None):
    now = time.time() if now is None else now
    row = db.execute("SELECT value FROM settings WHERE key='last_batch'").fetchone()
    if row and now < float(row[0]) + INTERVAL:
        return 0
    selected = choose(db)
    if not selected:
        return 0
    # Save the schedule before sending: restarting must not trigger another immediate batch.
    with db:
        db.execute("INSERT OR REPLACE INTO settings VALUES ('last_batch',?)", (str(now),))
    sent = 0
    for source, post in selected:
        # Reserve before sending. An ambiguous timeout/crash is held for manual inspection,
        # rather than automatically repeating something Telegram may already have accepted.
        with db:
            db.execute("UPDATE posts SET state='pending' WHERE source=?", (source,))
            db.executemany('INSERT OR IGNORE INTO used_links VALUES (?)', [(u,) for u in post['links']])
        try:
            result = telegram.publish(post)
        except Exception:
            LOG.error('Envoi incertain pour %s : conservé en pending, vérifier avant toute reprise', source)
            break
        with db:
            db.execute("UPDATE posts SET state='sent' WHERE source=?", (source,))
            if result:
                messages = result if isinstance(result, list) else [result]
                db.executemany('INSERT OR IGNORE INTO deliveries VALUES (?,?)',
                               [(source, message['message_id']) for message in messages])
        sent += 1
        LOG.info('Annonce complète publiée : %s', source)
        time.sleep(3)
    LOG.info('%d/%d annonces publiées', sent, len(selected))
    return sent


@contextmanager
def instance_lock(path):
    with Path(path).open('a+b') as lock:
        if os.name == 'nt':
            import msvcrt
            if lock.seek(0, 2) == 0:
                lock.write(b'0')
                lock.flush()
            lock.seek(0)
            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                raise SystemExit('Une instance utilise déjà cet historique') from None
            try:
                yield
            finally:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise SystemExit('Une instance utilise déjà cet historique') from None
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scan', action='store_true', help='Collecter sans aucune publication')
    parser.add_argument('--check', action='store_true', help='Vérifier le jeton et les droits sans publier')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    data_dir = Path(os.getenv('BOT_DATA_DIR', str(Path(__file__).parent / 'data')))
    data_dir.mkdir(parents=True, exist_ok=True)
    with instance_lock(data_dir / 'bot.lock'):
        db = connect(data_dir / 'history.sqlite3')
        if args.scan:
            if not collect(db):
                raise SystemExit('Aucune annonce récupérée : vérifier le réseau et les pages sources')
            LOG.info('%d annonces inédites sélectionnables', len(choose(db)))
            return
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            raise SystemExit('Renseigner TELEGRAM_BOT_TOKEN dans les paramètres sécurisés')
        telegram = Telegram(token, os.getenv('TELEGRAM_DESTINATION', DESTINATION))
        telegram.check()
        if args.check:
            LOG.info('Authentification et droits de publication vérifiés, aucun message envoyé')
            return
        while True:
            collect(db)
            run_batch(db, telegram)
            time.sleep(60)


if __name__ == '__main__':
    main()
