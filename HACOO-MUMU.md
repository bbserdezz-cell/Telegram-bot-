# Conversion des liens via le compte Hacoo dans MuMu

Objectif : recevoir un message `40763432 | pantalon Adidas`, chercher des annonces correspondantes dans les sept sources, generer le lien affilie de ce produit dans Hacoo et publier photos, nom, lien personnel et code Erdezz14.

## Etat actuel

Connecteur preparatoire, pas encore un service actif. `hacoo_mumu.py` valide les codes de 7 ou 8 chiffres commencant par 40, forme `https://hacoo.pl/detail/CODE`, saisit le lien dans un ecran Link Customize reconnu, verifie la saisie avant Create Link, et lit un lien unique dans Promote Link. Aucun endpoint Hacoo prive n'est invente et aucun lien affilie n'est fabrique localement.

`hacoo_requests.py` parse code + nom, cherche des candidats dans les titres et prepare une annonce dont la liste de liens contient uniquement le lien genere. Une correspondance de noms ne prouve pas que les photos representent exactement le produit du code : les variantes doivent etre distinguees.

Les tests utilisent des ecrans Android simules. Ni la vraie interface MuMu, ni la connexion Telegram entrante, ni le parcours complet sur ton PC ne sont encore valides. Le bot existant n'utilise pas ces modules pour ses publications actuelles.

## Prochaine verification sur Windows

1. Telecharger le depot (Code > Download ZIP) et extraire le dossier.
2. Ouvrir MuMu et Hacoo, connecte a ton compte. Afficher Affiliate Program > Promotion > Link Customize, sans la fenetre de resultat.
3. Double-cliquer `DIAGNOSTIC-MUMU.bat`. Il utilise le adb.exe de MuMu, sans installation Python. Si necessaire, activer le debogage ADB dans MuMu et renseigner le port local affiche par l'emulateur.
4. Examiner `diagnostic-mumu/hacoo-ui.xml` avant de le transmettre : il peut contenir les textes visibles de l'ecran. Ne pas faire le diagnostic sur une page affichant un mot de passe ou des donnees sensibles. `local-config.json` contient seulement les chemins locaux et l'identifiant ADB ; garder ce fichier sur le PC.

Le diagnostic lit l'ecran uniquement. Il ne clique pas et ne publie rien. Il permettra de confirmer les libelles, champs, controle de fermeture et possibilites de navigation. Si le WebView n'expose pas ses champs via UIAutomator, un autre mode de pilotage devra etre prepare ; aucun clic aveugle n'est prevu.

## Test de conversion ulterieur

Une fois les selecteurs verifies, avec Python 3.12+ et Link Customize ouvert :

```powershell
python hacoo_mumu.py --adb "CHEMIN\adb.exe" --serial "IDENTIFIANT" convert 40763432
```

La fenetre Promote Link doit etre fermee avant une nouvelle conversion. Le parcours automatique depuis l'accueil et la fermeture automatique du resultat restent a adapter au diagnostic reel. Le PC et MuMu doivent rester actifs : Railway seul ne peut pas piloter un emulateur local sans agent de liaison. Ne jamais exposer le port ADB sur Internet. L'agent Telegram devra limiter les demandes au proprietaire du bot avant d'accepter des actions sur son compte.
