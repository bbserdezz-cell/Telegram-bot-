# Republication Telegram

Python 3.12 ou supérieur, sans dépendance externe. Lecture des pages web publiques des sept canaux configurés dans `bot.py`, puis publication vers `@hacoolinks2k26`.

Pour tester un produit précis avec **ton lien affilié Hacoo**, lancer `PUBLIER-LIEN-HACOO.bat` sur le PC où MuMu est ouvert. Voir [les instructions du test Hacoo](HACOO-MUMU.md). Ce test interactif conserve le nom, les photos et le prix de l'annonce choisie, et remplace son lien. Il est distinct du republicateur périodique décrit ci-dessous.

## Configuration

1. Créer un bot avec @BotFather.
2. Ajouter ce bot comme administrateur de @hacoolinks2k26, avec le droit de publier.
3. Définir `TELEGRAM_BOT_TOKEN` via les paramètres sécurisés de l'hébergement. Ne jamais le mettre dans le code, Git, les journaux ou le chat.
4. Autoriser les connexions HTTPS à `t.me`, `api.telegram.org` et `cdn4.telesco.pe` (images). Les images sont téléchargées puis envoyées comme fichiers : Telegram refusait leur récupération directe par URL avec WEBPAGE_CURL_FAILED.

Variables facultatives : `TELEGRAM_DESTINATION` (défaut : @hacoolinks2k26), `BOT_DATA_DIR` (défaut : dossier `data` à côté de bot.py). Le dossier de données doit être conservé durablement : le supprimer supprime l'historique des annonces et des liens publiés. Une seule instance par historique est autorisée.

## Vérification sans publication

```sh
cd /workspace/Telegram-bot-
python3 -m unittest -v
python3 bot.py --scan
python3 bot.py --check
```

`--scan` lit les pages et stocke les annonces mais ne publie jamais. Il échoue si aucune annonce n'est récupérée. `--check` vérifie le jeton, le canal et les droits sans publier. Ne pas confondre les tests locaux avec ces vérifications réelles.

## Démarrage

```sh
cd /workspace/Telegram-bot-
python3 bot.py
```

Le premier lot est publié au démarrage, puis au plus tôt toutes les 45 minutes. Chaque lot contient jusqu'à 15 annonces inédites tirées au hasard dans l'ensemble des sources. Si moins de 15 sont disponibles, seul le nombre disponible est publié. Les pages sont relues environ chaque minute, sans prétendre récupérer tout l'historique. Le processus doit rester actif sur une machine toujours allumée ; une session de développement cloud n'est pas une garantie d'hébergement permanent. Utiliser un gestionnaire de services sur l'hébergement final pour les redémarrages.

Les annonces retenues comportent de 1 à 10 photos, un nom de produit exploitable et un lien. La légende suit toujours le même modèle : nom du produit en gras, lien(s), puis `-15% : Erdezz14 ‼️`. Les hashtags, mentions et descriptions promotionnelles des sources ne sont pas repris. Les destinations des liens sont conservées, y compris leurs paramètres et fragments. Le nom du produit est extrait sans traduction automatique et limité à 160 caractères. Une légende dépassant 1 024 unités UTF-16 est écartée. Les photos restent celles de la source, sans retouche des textes imprimés dans l'image. Les annonces vidéo/document sont ignorées. Les liens identiques et les textes identiques déjà réservés/publiés sont exclus, y compris entre sources ; des URLs différentes menant au même produit ne sont pas nécessairement reconnues comme doublons.

## Échecs et limites

La lecture web dépend des aperçus publics de Telegram et de leur structure HTML. Certaines annonces, images protégées, sources ou archives peuvent ne pas être accessibles. Il n'y a pas de connexion à un compte personnel ni de contournement des restrictions. Vérifier les droits de republication des contenus sources.

L'historique est dans `data/history.sqlite3`. Avant envoi, une annonce est réservée (`pending`). Après envoi complet, elle passe à `sent`. Si Telegram refuse ou si une connexion coupe pendant l'envoi, l'annonce reste en `pending` et ne sera pas retentée automatiquement : un message peut déjà avoir été accepté. Vérifier le canal avant toute reprise manuelle. Cela privilégie l'absence de répétition, mais peut laisser une annonce manquante ou partielle. Aucun système ne peut garantir un envoi exactement une fois face à tous les incidents réseau.

Le jeton est envoyé uniquement à l'API Telegram en HTTPS. Les exceptions réseau détaillées ne sont pas affichées pour ne pas divulguer le jeton présent dans l'URL de l'API.
