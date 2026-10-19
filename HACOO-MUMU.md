# Conversion des liens via le compte Hacoo dans MuMu

Objectif : saisir `CODE, nom du produit`, chercher des annonces correspondantes dans les trois sources, generer le lien affilie de ce produit dans Hacoo et publier photos, nom, prix, lien personnel et code Erdezz14.

## Page simple et publication automatique

1. Extraire le ZIP. Garder le PC allume, connecte et sans mise en veille, avec MuMu et Hacoo ouverts sur Affiliate Program > Promotion > Link Customize.
2. Lancer `OUVRIR-SITE-HACOO.bat`. Le navigateur ouvre une page locale avec deux champs : code et nom du modele. Le lanceur reutilise le jeton protege et la connexion MuMu deja enregistres.
3. Attendre le premier chargement des annonces (jusqu'a quelques minutes). Elles restent ensuite en memoire et sont actualisees toutes les dix minutes.
4. Saisir le code et le nom precis du modele, puis cliquer **Publier sur Telegram**. La premiere annonce correspondante dans le cache est choisie, son lien est remplace par le lien affilie cree dans Hacoo, puis les photos et la legende sont envoyees directement sur **@hacoolinks2k26**. Il n'y a plus de choix numerote ni de validation supplementaire.

### Importer une liste

Dans la page, utiliser **Importer une liste (.txt ou .csv)**, choisir le fichier puis cliquer **Importer et publier la liste**. Chaque ligne contient `code, nom du modele` ; les separateurs point-virgule, barre verticale et tabulation sont aussi acceptes. Enregistrer en UTF-8. Une premiere ligne `code,nom` est facultative. Limites : 100 produits uniques et 100 Ko. Les lignes vides et doublons identiques sont ignores ; une ligne invalide ou deux noms differents pour le meme code bloquent tout le fichier avant publication.

Les produits passent un par un dans l'ordre du fichier, sans confirmation. La page affiche le resultat de chaque ligne. Un produit deja envoye ou sans correspondance est ignore. Une erreur de conversion ou un envoi incertain interrompt le lot ; les lignes restantes sont indiquees comme non traitees. Apres verification du canal, on peut reimporter le fichier : l'historique empeche de republier les codes deja envoyes ou incertains. La liste en attente n'est pas reprise automatiquement apres fermeture du programme. Garder le programme et MuMu ouverts jusqu'a la fin.

La recherche s'arrete a la premiere correspondance dans l'ordre des annonces en cache (sources configurees, puis ordre de collecte). Elle ne parcourt plus toutes les correspondances pour les classer ou les tirer au hasard. Le temps de conversion Hacoo et de transfert des photos reste variable.

Le nom ne prouve pas la correspondance avec le code produit. Saisir « Saucony Jazz » plutot que « Saucony » pour reduire les erreurs de modele. Le prix ecrit dans la source est conserve, sans recalcul ; s'il manque, aucun prix n'est ajoute. Aucun prix ne doit etre invente.

La page fonctionne sur ce PC uniquement ; elle n'est pas un site public heberge. Elle reste disponible tant que le programme tourne. On peut quitter ChatGPT, mais pas eteindre/mettre en veille le PC ou fermer le programme/MuMu. Le premier chargement, les clics Hacoo et l'envoi des photos peuvent depasser 30 secondes ; aucun delai fixe n'est garanti. Le cache accelere surtout les publications apres chargement. Les sources restent limitees a 30 pages accessibles par canal.

Une seule publication est traitee a la fois. Le meme historique protege contre les doublons et les envois incertains. Le serveur ecoute uniquement sur 127.0.0.1 ; le jeton Telegram n'est jamais envoye au navigateur. Les requetes de publication exigent l'origine locale et une cle de session. Ne pas exposer ce serveur ou ADB sur Internet.

`PUBLIER-LIEN-HACOO.bat` reste disponible pour saisir `CODE, nom` en console et publier automatiquement. Le mode manuel historique reste accessible par la commande `py -3 hacoo_publish.py --adb CHEMIN --serial IDENTIFIANT` sans `--auto`.

Les tests du serveur HTTP et du parcours automatique utilisent un MuMu et un Telegram simules. Le parcours manuel a fonctionne sur le PC de l'utilisateur ; la nouvelle page et son lanceur Windows restent a verifier sur ce PC.

Si `getMe` echoue, aucun produit n'a encore ete recherche ni publie. Le message distingue maintenant un refus HTTP 401 (jeton invalide/revoque) d'un probleme de connexion. Pour remplacer le jeton local, lancer `CHANGER-JETON-HACOO.bat` et coller uniquement le jeton actuel de BotFather dans la saisie masquee. Ce lanceur remplace le jeton protege et reprend le test ; telecharger un nouveau ZIP seul ne remplace pas le jeton enregistre.

La recherche consulte jusqu'a 30 pages publiques de chacun des trois canaux, pas toutes leurs archives, et peut s'arreter plus tot apres cinq correspondances dans une source. Elle recherche les mots du nom dans le titre ou une ligne descriptive, avec de 1 a 10 photos. En mode manuel uniquement, les annonces sans prix sont affichees et demandent une saisie du prix verifie. En mode automatique et sur la page, elles sont publiees sans prix si celui-ci manque. Aucun prix n'est invente. En l'absence de resultat, elle ne choisit pas un produit au hasard. Le prix est repris avec ses qualificatifs (par exemple « a partir de »), sans recalculer une reduction ni garantir le tarif actuel chez Hacoo. Les photos restent intactes ; les textes ou liens imprimes dans une image ne sont pas modifies. L'ancien lien de la legende est remplace par le seul lien affilie retourne par Hacoo. Les hashtags et anciens codes promotionnels sont exclus de la legende.

L'historique des codes est conserve dans `%LOCALAPPDATA%\HacooAffiliate\history.sqlite3`, meme apres un nouveau telechargement du ZIP. Un code deja envoye ou dont l'envoi est incertain reste bloque : verifier le canal avant toute reprise. Cet historique est distinct de celui du republicateur periodique.

Ce parcours fonctionne sur le PC : il n'ecoute pas encore les messages prives envoyes au bot. Il ne modifie pas les publications automatiques de l'ancien bot. Les tests automatises couvrent le parcours avec MuMu et Telegram simules.

## Etat actuel

Connecteur utilisable par le test interactif, pas encore un service actif. `hacoo_mumu.py` valide les codes de 7 ou 8 chiffres commencant par 40, forme `https://hacoo.pl/detail/CODE`, saisit le lien dans un ecran Link Customize reconnu, verifie la saisie avant Create Link, et lit un lien unique dans Promote Link. Aucun endpoint Hacoo prive n'est invente et aucun lien affilie n'est fabrique localement.

`hacoo_requests.py` parse code + nom, cherche des candidats dans les titres et prepare une annonce dont la liste de liens contient uniquement le lien genere. Une correspondance de noms ne prouve pas que les photos representent exactement le produit du code : les variantes doivent etre distinguees.

Les selecteurs ont ete verifies sur les deux diagnostics Android fournis (formulaire et resultat). Le resultat contient un dialogue et un titre portant tous deux le nom Promote Link ; la lecture est limitee au dialogue. Le connecteur ferme le resultat avec Close et verifie le retour au formulaire. Les tests de pilotage utilisent des ecrans simules : les clics reels, la connexion Telegram entrante et le parcours complet sur le PC ne sont pas encore valides. Le bot existant n'utilise pas ces modules pour ses publications actuelles.

## Prochaine verification sur Windows

Le diagnostic tente automatiquement de connecter ADB aux ports en ecoute appartenant aux processus MuMu (connexion a 127.0.0.1 uniquement, 16 ports maximum, quatre secondes maximum par tentative). Il ne change ni le reglage ADB ni le pare-feu. Garder la connexion locale active dans MuMu. Si la detection echoue, le message permet d'arreter sans inventer de port et de transmettre une capture du diagnostic.

Apres un diagnostic reussi, les chemins et l'identifiant ADB sont aussi conserves dans `%LOCALAPPDATA%\HacooAffiliate\mumu-config.json`. Le lanceur les reutilise meme apres suppression du dossier extrait. Il tente de reconnecter l'adresse locale enregistree, puis relance la detection si l'appareil n'est plus disponible. Cette detection PowerShell reste a verifier sur le PC Windows ; elle n'a pas ete executee dans l'environnement Linux de developpement.

1. Telecharger le depot (Code > Download ZIP) et extraire le dossier.
2. Ouvrir MuMu et Hacoo, connecte a ton compte. Afficher Affiliate Program > Promotion > Link Customize, sans la fenetre de resultat.
3. Double-cliquer `DIAGNOSTIC-MUMU.bat`. Il utilise le adb.exe de MuMu, sans installation Python. Si necessaire, activer le debogage ADB dans MuMu et renseigner le port local affiche par l'emulateur.
4. Examiner `diagnostic-mumu/hacoo-ui.xml` avant de le transmettre : il peut contenir les textes visibles de l'ecran. Ne pas faire le diagnostic sur une page affichant un mot de passe ou des donnees sensibles. `local-config.json` contient seulement les chemins locaux et l'identifiant ADB ; garder ce fichier sur le PC.

Le diagnostic lit l'ecran uniquement. Il ne clique pas et ne publie rien. Il permettra de confirmer les libelles, champs, controle de fermeture et possibilites de navigation. Si le WebView n'expose pas ses champs via UIAutomator, un autre mode de pilotage devra etre prepare ; aucun clic aveugle n'est prevu.

## Test de conversion ulterieur

Avec Python 3.12+ et Link Customize ouvert, lancer `TESTER-LIEN-HACOO.bat`, puis entrer le code produit. Ce lanceur reutilise `diagnostic-mumu/local-config.json` ou lance automatiquement le diagnostic si la configuration manque ou si adb.exe est introuvable. Aucun dossier a copier. Il cree un lien sur le compte Hacoo sans rien publier sur Telegram. La fenetre reste ouverte pour lire le resultat ; la fermer avec X. Le lanceur PowerShell reste a verifier sur Windows.

Commande equivalente :

```powershell
py -3 hacoo_mumu.py --adb "CHEMIN\adb.exe" --serial "IDENTIFIANT" convert 40763432
```

Une ancienne fenetre Promote Link est fermee avant la saisie ; son lien n'est jamais reutilise pour le nouveau code. Le parcours automatique depuis l'accueil reste a implementer. Le PC et MuMu doivent rester actifs : Railway seul ne peut pas piloter un emulateur local sans agent de liaison. Ne jamais exposer le port ADB sur Internet. L'agent Telegram devra limiter les demandes au proprietaire du bot avant d'accepter des actions sur son compte.
