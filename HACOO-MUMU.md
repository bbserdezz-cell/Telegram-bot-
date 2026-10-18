# Conversion des liens via le compte Hacoo dans MuMu

Objectif : saisir `CODE, nom du produit`, chercher des annonces correspondantes dans les sept sources, generer le lien affilie de ce produit dans Hacoo et publier photos, nom, prix, lien personnel et code Erdezz14.

## Test complet avec publication Telegram

1. Extraire le ZIP et ouvrir Hacoo dans MuMu sur Affiliate Program > Promotion > Link Customize.
2. Lancer `PUBLIER-LIEN-HACOO.bat`. Il utilise `py -3` et lance le diagnostic automatiquement si necessaire.
3. Si le jeton n'est pas deja disponible localement, le coller dans la saisie masquee du lanceur. Il est protege par Windows pour ce compte utilisateur, dans `%LOCALAPPDATA%\HacooAffiliate\token.protected`. Ne pas le saisir dans le chat ou dans un fichier du depot. Le jeton de l'ancienne installation locale est reutilise s'il existe.
4. Saisir le vrai code et le nom, separes par une virgule (le separateur `|` fonctionne aussi).
5. Choisir le numero d'une annonce. Son lien source s'ouvre pour verifier les photos, le prix et la variante. Taper `OK` si c'est bien le produit du code fourni.
6. Le connecteur cree le lien dans Hacoo, puis affiche la legende finale. Taper `PUBLIER` pour l'envoyer sur **@hacoolinks2k26**. Entree seule annule.

Si `getMe` echoue, aucun produit n'a encore ete recherche ni publie. Le message distingue maintenant un refus HTTP 401 (jeton invalide/revoque) d'un probleme de connexion. Pour remplacer le jeton local, lancer `CHANGER-JETON-HACOO.bat` et coller uniquement le jeton actuel de BotFather dans la saisie masquee. Ce lanceur remplace le jeton protege et reprend le test ; telecharger un nouveau ZIP seul ne remplace pas le jeton enregistre.

La recherche consulte jusqu'a cinq pages publiques recentes de chacun des sept canaux, pas toutes leurs archives. Elle exige les mots du nom dans le titre, de 1 a 10 photos et un prix ecrit avec une devise reconnue. En l'absence de resultat, elle ne choisit pas un produit au hasard. Le prix est repris avec ses qualificatifs (par exemple « a partir de »), sans recalculer une reduction ni garantir le tarif actuel chez Hacoo. Les photos restent intactes ; les textes ou liens imprimes dans une image ne sont pas modifies. L'ancien lien de la legende est remplace par le seul lien affilie retourne par Hacoo. Les hashtags et anciens codes promotionnels sont exclus de la legende.

L'historique des codes est conserve dans `%LOCALAPPDATA%\HacooAffiliate\history.sqlite3`, meme apres un nouveau telechargement du ZIP. Un code deja envoye ou dont l'envoi est incertain reste bloque : verifier le canal avant toute reprise. Cet historique est distinct de celui du republicateur periodique.

Ce parcours est un test interactif sur le PC : il n'ecoute pas encore les messages prives envoyes au bot. Il ne modifie pas les publications automatiques de l'ancien bot. Les tests automatises couvrent le parcours avec MuMu et Telegram simules ; l'envoi reel de bout en bout doit encore etre verifie sur Windows.

## Etat actuel

Connecteur utilisable par le test interactif, pas encore un service actif. `hacoo_mumu.py` valide les codes de 7 ou 8 chiffres commencant par 40, forme `https://hacoo.pl/detail/CODE`, saisit le lien dans un ecran Link Customize reconnu, verifie la saisie avant Create Link, et lit un lien unique dans Promote Link. Aucun endpoint Hacoo prive n'est invente et aucun lien affilie n'est fabrique localement.

`hacoo_requests.py` parse code + nom, cherche des candidats dans les titres et prepare une annonce dont la liste de liens contient uniquement le lien genere. Une correspondance de noms ne prouve pas que les photos representent exactement le produit du code : les variantes doivent etre distinguees.

Les selecteurs ont ete verifies sur les deux diagnostics Android fournis (formulaire et resultat). Le resultat contient un dialogue et un titre portant tous deux le nom Promote Link ; la lecture est limitee au dialogue. Le connecteur ferme le resultat avec Close et verifie le retour au formulaire. Les tests de pilotage utilisent des ecrans simules : les clics reels, la connexion Telegram entrante et le parcours complet sur le PC ne sont pas encore valides. Le bot existant n'utilise pas ces modules pour ses publications actuelles.

## Prochaine verification sur Windows

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
