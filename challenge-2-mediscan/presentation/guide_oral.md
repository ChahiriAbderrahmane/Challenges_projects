# Guide oral — Mediscan / Challenge 2

Présentation : 14 diapositives principales + 1 annexe. Durée visée : environ 11 à 12 minutes, démonstration comprise.

À personnaliser avant le cours : remplacer `[votre nom]` sur la première diapositive.

## 01. Introduction — 30 s

Présentez l’objectif en une phrase : partir de la photo d’une boîte et identifier une référence uniquement si les informations visibles le permettent. Le cas Doliprane illustré a été réellement testé avec le moteur OCR et l’API. Précisez que le projet porte sur le Challenge 2 ; le chatbot du Challenge 1 reste séparé. Remplacez [votre nom] avant de présenter.

## 02. Du texte à l’identification — 40 s

Insistez sur la différence entre OCR et reconnaissance de produit. Doliprane seul ne distingue pas une force ou une présentation. Le système sépare donc lecture, extraction de champs et rapprochement. Les quatre issues sont normales : une photo valide ne doit pas systématiquement produire un médicament. La force décrit le produit ; le nombre de sachets décrit le conditionnement, pas un conseil de prise.

## 03. Interface et parcours utilisateur — 45 s

Montrez le dépôt de fichier, l’aperçu, les quatre champs extraits et les panneaux OCR/JSON. Cette capture provient du test dans Chrome avec la vraie image fournie : ce n’est pas une maquette. L’interface est en HTML, CSS et JavaScript, servie par FastAPI sur le même port. Elle n’a pas de compilation ni de serveur frontend séparé. Les candidats ambigus restent explicitement non confirmés.

## 04. Architecture — 50 s

Décrivez les six étapes de gauche à droite. Le projet reste monolithique au sens déploiement : une application FastAPI et un worker local pour pouvoir interrompre réellement le calcul natif. Le catalogue est un fichier JSON, pas un serveur de base de données. Les modèles sont réutilisés par processus. Les dépendances du chatbot ne sont ni importées ni modifiées. L’injection permet de tester la logique indépendamment de l’OCR, complétée par des tests avec le moteur réel.

## 05. Pourquoi Tesseract ? — 45 s

Expliquez le choix par l’environnement Fedora/Python 3.12, le CPU et la simplicité. Tesserocr donne accès au moteur Tesseract natif, aux boîtes et aux confiances de mots. Les documentations officielles confirment les langues, mais cela ne prouve pas leur précision sur notre jeu. EasyOCR et PaddleOCR ont été étudiés documentairement, pas comparés par des chiffres inventés. Un modèle français best plus lourd a été essayé sur le cas difficile sans résoudre le problème ; il n’a pas été ajouté au chemin de production.

## 06. Le cas Doliprane — 55 s

Racontez le diagnostic : trois problèmes différents, pas seulement un mauvais OCR. Le catalogue ne contenait pas ce produit, l’extracteur ignorait les sachets et l’OCR global ratait la force. Le repli lit au maximum deux nombres ; il confirme tous leurs chiffres dans une région locale puis cherche une unité voisine. Aucune coordonnée propre à Doliprane n’est codée en dur et aucune force n’est déduite de la marque. Les passages bruts et les contradictions sont conservés. Le résultat est confirmé par un test API réel sur cette image, qui reste un seul cas de développement, pas une preuve de robustesse générale.

## 07. Score et abstention — 55 s

Le nom sert à générer des candidats avec un seuil de 0,65, puis les autres champs départagent les références. Un champ en conflit est pénalisé et interdit l’acceptation. Une orthographe proche ne peut pas effacer un conflit clair de force. Les seuils ont été choisis sur les données de développement synthétiques, avec un objectif de zéro fausse acceptation observée et un départage conservateur. Ils ne sont pas une calibration probabiliste et ne garantissent pas le même comportement dans la population réelle. Les tests couvrent aussi B12 contre B6, les unités g/mg/mcg et les alias arabes explicites.

## 08. Provenance du catalogue — 40 s

La référence réelle a été vérifiée dans les fichiers officiels français CIS et CIP. Le numéro CIS est 61681702. La mise à jour de la spécialité est datée du 29 septembre 2026, celle de la présentation du 27 octobre 2026. La licence autorise la réutilisation avec attribution et dates, sans caution officielle. Les faits d’identité ne donnent pas une licence sur le graphisme de l’emballage. Les 15 autres références sont explicitement inventées. N’affirmez pas que ce produit ou ce catalogue décrit le marché marocain.

## 09. Données et séparation — 50 s

Distinguez trois types de données : les rendus indépendants, leurs dégradations artificielles et le packshot utilisateur. Le manifeste fournit identifiants, familles, empreintes, labels et provenance. Les dégradations ne traversent pas les splits. Les 54 images test comprennent 50 images de produits connus et quatre négatifs ; vingt sont dégradées, donc les observations ne sont pas toutes indépendantes. La photo utilisateur n’est pas ajoutée rétroactivement au test : c’est un cas de développement, sans transcription exhaustive et avec des droits d’illustration non établis. La cible de 60 photos réelles n’est donc pas atteinte.

## 10. Interpréter les résultats globaux — 60 s

Commencez par l’exactitude de bout en bout : 21 sur 50, soit 42 %, et non 100 %. Les 100 % observés concernent uniquement les 21 résultats que le système a accepté de donner. Le taux d’acceptation sur toutes les images est de 38,89 %, donc il s’abstient souvent. Quatre négatifs seulement ne permettent pas de conclure à un risque nul. Le top 3 est utile pour comprendre la génération de candidats mais ne remplace pas une identification correcte. Les temps sont ceux du service préchauffé, avec décodage et OCR, sans réseau ni chargement initial.

## 11. La limite arabe — 55 s

Les 25 images positives françaises incluent 21 acceptations correctes. Pour les 25 images positives arabes, aucune identification n’a été acceptée. Les alias arabes peuvent être lus, mais les chiffres de force ou de quantité sont fréquemment omis ou confondus. Les CER et WER affichés concernent le passage OCR primaire, en conservant les distinctions de chiffres, accents et casse ; la fusion auxiliaire n’est pas évaluée par ces taux. Le texte de référence est celui du générateur, pas une transcription manuelle de boîtes réelles. Il n’y a pas de négatif arabe dans ce petit test ; on ne peut pas annoncer son taux de faux positifs.

## 12. Fiabilité — 45 s

L’API valide le contenu décodé, pas seulement l’extension. Elle limite la taille, les pixels et la concurrence. Le worker persistant est terminé et rejoint si son délai de calcul est dépassé : cela évite d’annoncer qu’un simple timeout Python aurait arrêté le code natif. Les requêtes supplémentaires sont rejetées, pas mises dans une file infinie. Plusieurs workers du serveur multiplieraient les modèles et la capacité CPU, d’où la recommandation d’un seul. Les images ne sont pas conservées par défaut et les erreurs clients ne contiennent pas de traceback.

## 13. Démonstration — 70 s

Avant le cours, démarrez le serveur sur le port 8004 et ouvrez l’interface. Uploadez le fichier Doliprane situé à la racine du projet : nom, 1000 mg, poudre pour solution buvable, 8 unités doivent apparaître. Pour l’ambiguïté, utilisez data/demo/images/demo-01-250-fr-test-partial.png ; pour l’inconnu, negative-unknown-test.png ; pour l’illisible, negative-blank-test.png. Si le temps manque, montrez Doliprane et l’image partielle. Le test navigateur réel vérifie le premier résultat ; les états supplémentaires, le texte non interprété en HTML, la surcharge et le mobile sont aussi testés. Le test privé est ignoré si le fichier utilisateur manque dans une autre installation.

## 14. Conclusion — 45 s

Résumez la contribution : une séparation nette entre OCR et identité produit, une application utilisable et une évaluation honnête. Le prototype ne constitue pas encore un système de reconnaissance robuste de tous les médicaments marocains. La priorité est un jeu réel documenté d’au moins 15 variantes et 60 photos, avec davantage de négatifs et de textes arabes. Ensuite seulement, comparer un moteur de texte de scène et reconsidérer les prétraitements et seuils. Le chatbot existant est préservé et aucun entraînement, stock, prix ou infrastructure distribuée n’a été ajouté.

## 15. Sources et questions — Annexe

Cette diapositive sert de référence, sans nécessiter une lecture à voix haute. Les métriques proviennent des JSON du projet et les identifiants réels des fichiers CIS/CIP de la BDPM. La capture d’écran provient d’un test réel ; l’illustration de la boîte a été fournie par l’utilisateur, sans source originale ni licence d’illustration vérifiée. La présentation est destinée à l’usage académique local demandé. Les références réelles françaises ne prouvent ni une disponibilité au Maroc ni la version exacte du graphisme de la boîte.

## Questions probables du professeur

**Pourquoi ne pas demander le résultat à un LLM ?** Le but est de relier des preuves visibles à un référentiel vérifié, sans compléter des champs absents ou inventer un produit.

**Le système est-il précis à 100 % ?** Non. Sur 50 images synthétiques connues, 21 ont été correctement identifiées et acceptées. Les 21/21 ne décrivent que la précision parmi les acceptations, pas l’exactitude globale.

**Pourquoi annoncer français/arabe alors que l’arabe ne fonctionne pas bien ?** Le moteur est configuré pour les deux langues et son comportement est évalué. Le résultat arabe est une limitation mesurée, pas un objectif présenté comme atteint.

**Pourquoi utiliser des médicaments fictifs ?** Pour disposer de régressions reproductibles sans fabriquer un catalogue réel ni redistribuer des illustrations de provenance incertaine. Cela ne remplace pas la collecte réelle requise.

**Comment éviter la confusion entre 500 mg et 1 000 mg ?** Les forces sont normalisées puis comparées explicitement. Une contradiction interdit l’acceptation, même avec une marque très proche.

**Pourquoi une base française pour un contexte marocain ?** C’est une référence vérifiable pour ce prototype précis, sans prétendre décrire le marché marocain. Il faut ensuite importer des références locales avec provenance et droits documentés.

**Le timeout arrête-t-il vraiment le calcul ?** L’arrêt d’une attente asynchrone ne suffirait pas. Le superviseur termine et rejoint le processus OCR avant de libérer la capacité.

**Quel est le principal travail restant ?** Collecter et annoter des photos réelles autorisées, ajouter des négatifs, puis comparer les OCR et recalibrer uniquement sur le développement.

## Commandes de démonstration

```bash
.venv/bin/python -m uvicorn recognition.api:app --host 127.0.0.1 --port 8004 --workers 1
```

Interface : http://127.0.0.1:8004/
Documentation : http://127.0.0.1:8004/docs

Fichiers : boîte Doliprane à la racine ; `data/demo/images/demo-01-250-fr-test-partial.png` ; `data/demo/images/negative-unknown-test.png` ; `data/demo/images/negative-blank-test.png`.

## Précautions de présentation des résultats

Les taux globaux sont mesurés sur des données synthétiques. Le packshot Doliprane est un cas de développement séparé. Les latences excluent HTTP et démarrage. Les faibles effectifs et les familles d’images communes limitent les conclusions. Les CER/WER portent sur le passage primaire et sur des références générées, pas sur une transcription manuelle de photos réelles.
