"""Local MuMu/ADB adapter. Run on the Windows computer hosting MuMu."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import time
import uuid
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET


class AutomationError(RuntimeError):
    pass


def product_code(value):
    value = str(value).strip()
    if not re.fullmatch(r'40[0-9]{5,6}', value):
        raise ValueError('Le code doit comporter 7 ou 8 chiffres et commencer par 40.')
    return value


def product_url(value):
    return 'https://hacoo.pl/detail/' + product_code(value)


def affiliate_url(value):
    value = value.strip()
    parts = urlsplit(value)
    if (parts.scheme != 'https' or parts.netloc != 'c.onlyaff.app'
            or not re.fullmatch(r'/[A-Za-z0-9_-]+', parts.path)
            or parts.query or parts.fragment):
        raise AutomationError('Le lien retourné ne correspond pas au format affilié observé.')
    return value


def nodes(xml):
    try:
        root = ET.fromstring(xml)
        result = list(root.iter('node'))
        if root.tag != 'hierarchy' or not result:
            raise AutomationError('Le diagnostic ne contient pas de structure Android.')
        return result
    except ET.ParseError:
        raise AutomationError('Écran Android illisible.') from None


def label(node):
    return (node.get('text') or node.get('content-desc') or '').strip()


def bounds_center(node):
    match = re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', node.get('bounds', ''))
    if not match:
        raise AutomationError('Position du contrôle introuvable.')
    x1, y1, x2, y2 = map(int, match.groups())
    if x2 <= x1 or y2 <= y1:
        raise AutomationError('Contrôle invisible.')
    return (x1 + x2) // 2, (y1 + y2) // 2


def unique_label(xml, expected):
    matches = [n for n in nodes(xml) if label(n).casefold() == expected.casefold()
               and n.get('enabled', 'true') == 'true']
    if len(matches) != 1:
        raise AutomationError(f'Contrôle « {expected} » absent ou ambigu. Ouvre Link Customize dans Hacoo.')
    return matches[0]


def input_field(xml):
    candidates = [n for n in nodes(xml) if n.get('class', '').endswith('EditText')
                  and n.get('enabled', 'true') == 'true']
    if len(candidates) != 1:
        raise AutomationError('Champ de saisie absent ou ambigu ; diagnostic de cet écran nécessaire.')
    return candidates[0]


def generated_link(xml):
    # Require the result dialog, so a link elsewhere on the page is never accepted.
    unique_label(xml, 'Promote Link')
    links = set()
    for node in nodes(xml):
        for value in re.findall(r"https://c\.onlyaff\.app/[^\s<>\"']+", label(node)):
            links.add(affiliate_url(value))
    if len(links) != 1:
        raise AutomationError('Aucun lien affilié unique lisible dans la fenêtre de résultat.')
    return links.pop()


class Adb:
    def __init__(self, executable, serial):
        self.executable = str(Path(executable).resolve())
        self.serial = serial

    def run(self, *args, check=True):
        try:
            result = subprocess.run([self.executable, '-s', self.serial, *args],
                                    capture_output=True, timeout=30, check=check)
            return result.stdout.decode('utf-8', errors='replace')
        except (OSError, subprocess.SubprocessError):
            raise AutomationError('Commande ADB impossible. Vérifie MuMu et sa connexion ADB.') from None

    def screen(self):
        remote = '/sdcard/hacoo-automation-' + uuid.uuid4().hex + '.xml'
        try:
            self.run('shell', 'uiautomator', 'dump', remote, check=False)
            xml = self.run('shell', 'cat', remote, check=False)
            nodes(xml)  # Validate fresh output, not the unreliable dump exit code.
            return xml
        finally:
            try:
                self.run('shell', 'rm', '-f', remote, check=False)
            except AutomationError:
                pass

    def tap(self, node):
        x, y = bounds_center(node)
        self.run('shell', 'input', 'tap', str(x), str(y))


def convert(adb, code):
    """Requires Hacoo already logged in with Link Customize open; no blind taps."""
    url = product_url(code)
    screen = adb.screen()
    unique_label(screen, 'Link Customize')
    if any(label(n).casefold() == 'promote link' for n in nodes(screen)):
        raise AutomationError('Ferme la précédente fenêtre Promote Link avant de créer un nouveau lien.')
    field = input_field(screen)
    previous = field.get('text', '')
    if len(previous) > 512:
        raise AutomationError('Le champ contient un texte inattendu.')
    adb.tap(field)
    adb.run('shell', 'input', 'keyevent', 'KEYCODE_MOVE_END')
    if previous:
        adb.run('shell', 'input', 'keyevent', *(['KEYCODE_DEL'] * len(previous)))
    adb.run('shell', 'input', 'text', url)
    screen = adb.screen()
    if input_field(screen).get('text', '').strip() != url:
        raise AutomationError('La saisie exacte du lien produit ne peut pas être confirmée ; création arrêtée.')
    adb.tap(unique_label(screen, 'Create Link'))
    for _ in range(10):
        time.sleep(1)
        screen = adb.screen()
        if any(label(n).casefold() == 'promote link' for n in nodes(screen)):
            return {'product_code': product_code(code), 'product_url': url,
                    'affiliate_url': generated_link(screen)}
    raise AutomationError('Hacoo n’a pas affiché de résultat lisible. Aucun lien utilisable confirmé.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', required=True, help='Chemin du adb.exe fourni par MuMu')
    parser.add_argument('--serial', required=True, help='Identifiant exact dans adb devices')
    sub = parser.add_subparsers(dest='command', required=True)
    diagnostic = sub.add_parser('inspect')
    diagnostic.add_argument('--output', default='hacoo-ui.xml')
    conversion = sub.add_parser('convert')
    conversion.add_argument('code')
    args = parser.parse_args()
    adb = Adb(args.adb, args.serial)
    try:
        if args.command == 'inspect':
            Path(args.output).write_text(adb.screen(), encoding='utf-8')
            print('Diagnostic enregistré. Il peut contenir le texte visible de ton écran.')
        else:
            print(json.dumps(convert(adb, args.code), ensure_ascii=False))
    except (AutomationError, ValueError) as error:
        raise SystemExit(str(error))


if __name__ == '__main__':
    main()
