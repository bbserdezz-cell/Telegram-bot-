# Railway

Le bot est un processus permanent, pas un site web. Le Dockerfile contient Python 3.12 et le programme, sans dependance externe. Aucun port ni domaine web n'est requis.

1. Publier le code du depot sur GitHub, sans jeton, fichiers `.env`, donnees SQLite ou journaux.
2. Dans Railway, creer un projet depuis ce depot GitHub. Préparer les variables et le volume avant de laisser le premier deploiement demarrer ; un demarrage avec un jeton valide peut publier immediatement.
3. Variable secrete : `TELEGRAM_BOT_TOKEN`, avec le jeton actuel du bot.
4. Variable `BOT_DATA_DIR` : `/data` (deja valeur par defaut de l'image).
5. Attacher un volume persistant au service, chemin `/data`, et ne conserver qu'une replique.
6. Desactiver la mise en veille/serverless si cette option est active. Ne pas configurer de cron : le processus gere lui-meme les 45 minutes.
7. Avant de demarrer, arreter les instances cloud/Windows du bot et transferer leur historique SQLite dans `/data/history.sqlite3` via l'acces au volume fourni par Railway. Ne pas demarrer avec un historique vide si l'on veut exclure les annonces deja publiees avant cette migration. Le depot public n'inclut pas cet historique.
8. Deployer puis verifier les journaux et une publication complete sur Telegram. L'image ne genere aucun serveur HTTP : ne pas ajouter de healthcheck HTTP.

Railway depend du solde, de l'offre et des conditions du compte. Un essai ne garantit pas un mois gratuit ; consulter la facturation avant d'activer une offre payante. Un volume persistant peut aussi etre facture. Le code a ete teste localement ; cela n'etablit pas que le deploiement Railway a ete effectue.
