# Correction du cas Doliprane — 27/10/2026

## Échec reproduit

Le fichier fourni par l'utilisateur est
`doliprane-1000-mg-8-sachets-9261.dsGPD15_Z9IFisZmfHVEVVw5uGg.png`.
Le résultat initial était `unknown`, sans force, forme ni taille de boîte.
Trois causes ont été vérifiées :

1. Le catalogue ne contenait que les 15 variantes fictives.
2. L'extracteur ne gérait ni les sachets-dose ni la poudre pour solution buvable.
3. Le passage OCR automatique récupérait la marque, mais pas correctement le
   nombre « 1000 » et sa petite unité « mg » sur cette boîte colorée en perspective.

## Correction

* `recognition/extraction.py` reconnaît la forme `powder_oral_solution` et le
  conditionnement « 8 sachets-dose ». Le nombre de sachets ne devient pas une force.
* `data/catalogue-reference.json` contient **une** référence française vérifiée :
  CIS `61681702`, CIP13 `3400936246980`, DOLIPRANE 1000 mg, poudre pour solution
  buvable en sachet-dose, présentation de 8 sachets. Les sources BDPM, dates de
  mise à jour et conditions de réutilisation sont inscrites dans le fichier.
  Les données synthétiques restent distinctes et régénérables.
* Le repli OCR utilise les modes « bloc » et « texte dispersé ». Sur un nombre
  détecté, il confirme indépendamment **tous les chiffres** dans une région locale,
  puis lit l'unité immédiatement à droite. Ce sont des coordonnées relatives aux
  boîtes OCR, sans coordonnées Doliprane codées en dur, sans ajout d'unité depuis
  le catalogue et sans remplacement de 100 par 1000.
* Au maximum deux nombres sont examinés, avec deux lectures de région par nombre.
  Les passages complets et les lectures confirmées sont conservés dans
  `raw_ocr_text`; les boîtes de région sont remises dans le repère de l'image OCR.
  Les lectures de forces différentes restent contradictoires et empêchent
  l'acceptation. Le délai du processus reste inchangé.
* Les mots de présentation ne polluent plus le nom retourné lorsqu'un alias
  exact a réellement été observé : ce fichier retourne `product_name: doliprane`.
  Une correspondance floue n'est pas remplacée par un nom inventé depuis le catalogue.

Un essai du modèle français `tessdata_best` (3 972 885 octets) n'a pas résolu le
problème sur l'image entière. Il n'est donc ni activé ni requis. Son origine et
son empreinte sont enregistrées dans `models/experiments.json`; le service garde
les deux modèles `tessdata_fast` initiaux. Aucun autre moteur lourd n'a été installé
et l'image n'a pas été envoyée à un service externe.

## Résultat réel et vérification

L'intégration FastAPI avec le moteur réel retourne :

```json
{
  "status": "matched",
  "extracted_fields": {
    "product_name": "doliprane",
    "strength": "1000 mg",
    "form": "powder_oral_solution",
    "pack_size": 8,
    "observed_strengths": ["1000 mg"]
  },
  "matched_product": {
    "product_id": "fr-cip-3400936246980",
    "name": "Doliprane",
    "strength": "1000 mg",
    "form": "powder_oral_solution",
    "pack_size": 8,
    "score": 100.0
  }
}
```

Le score est une utilité de classement, **pas une probabilité**. La référence est
française : le pays de distribution et la version du graphisme de cette boîte
ne sont pas vérifiés par l'image.

* `python -m pytest -q` : **40 tests réussis** localement, dont le fichier réel,
  les sachets, la force manquante, les lectures contradictoires et le rejet d'un
  Doliprane « 500 mg » face à la référence « 1000 mg ».
* `reports/doliprane-regression.json` : une image de développement, reconnue
  correctement, 2 220,53 ms sur cette exécution. Ce n'est pas un benchmark de
  robustesse. Il n'y a pas de transcription exhaustive : CER/WER restent null.
  Un serveur Uvicorn indépendant et un véritable envoi multipart par `curl` ont
  également retourné `matched`, avec les mêmes champs, en 1 834,73 ms.
* `reports/evaluation-dev-layout-fallback.json` : 15 acceptations correctes sur
  30 images connues, aucun faux positif sur quatre négatifs de développement.
* `reports/evaluation-test-layout-fallback.json` : toujours 21 acceptations
  correctes sur 50 images connues, aucune fausse acceptation sur quatre négatifs.
  p50 393,22 ms, p95 1 032,48 ms sur 54 images synthétiques. Les seuils précédents
  ont été conservés; aucune optimisation n'a été faite sur les étiquettes test.

Pour l'OCR, le CER/WER porte maintenant explicitement sur `primary_ocr_text`, pas
sur la concaténation répétée des passages auxiliaires. L'identification utilise
les éléments de tous les passages conservés. CER primaire test : 33,59 %, WER :
40,73 %. Cela ne constitue pas une mesure de l'exactitude OCR de la fusion.

L'image utilisateur reste référencée sur place par empreinte dans
`data/local-regressions/manifest.json`. Ses droits d'illustration sont inconnus :
elle n'a pas été copiée dans le jeu synthétique redistribuable. Sans ce fichier,
le test privé est ignoré et le manifeste local ne peut pas être évalué.

## Relancer et essayer

Arrêter l'ancien processus avec Ctrl+C, puis, depuis `ph2` :

```bash
.venv/bin/python -m uvicorn recognition.api:app --host 127.0.0.1 --port 8000 --workers 1
```

Dans un autre terminal :

```bash
curl -sS http://127.0.0.1:8000/api/recognize \
  -F 'image=@doliprane-1000-mg-8-sachets-9261.dsGPD15_Z9IFisZmfHVEVVw5uGg.png;type=image/png'
```

Ce correctif valide ce cas précis et conserve les tests antérieurs. Il ne résout
pas les limites générales sur les chiffres arabo-indiens, les boîtes absentes du
catalogue, les perspectives arbitraires ou les images insuffisamment lisibles.
