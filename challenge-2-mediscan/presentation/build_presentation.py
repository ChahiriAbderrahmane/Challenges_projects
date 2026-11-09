"""Présentation française, éditable, fondée sur les rapports réellement mesurés."""
import json
import os
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ASSETS = HERE / "assets"
ASSETS.mkdir(exist_ok=True)
REPORT = json.loads((ROOT / "reports/evaluation-test-layout-fallback.json").read_text())
OVERALL = REPORT["overall"]
LANGUAGES = REPORT["by_language"]
LOCAL = json.loads((ROOT / "reports/doliprane-regression.json").read_text())
THRESHOLDS = json.loads((ROOT / "data/thresholds.json").read_text())

BACKGROUND = "F7F8F3"
INK = "1C3330"
TEAL = "166B5C"
MUTED = "71817B"
LINE = "DFE7DD"
PALE = "EAF3EB"
AMBER = "9B6223"
AMBER_BG = "FAF0DC"
FONT = "Liberation Sans"
prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
prs.core_properties.title = "Mediscan — Reconnaissance de boîtes de médicaments"
prs.core_properties.subject = "Challenge 2 : vision par ordinateur, OCR et rapprochement avec un catalogue"
prs.core_properties.author = "Projet académique — nom à compléter"
prs.core_properties.keywords = "FastAPI, Tesseract, OCR, français, arabe, Python, médicaments"
TALK = []


def rgb(hex_value):
    return RGBColor.from_string(hex_value)


def text(slide, content, x, y, w, h, size=18, color=INK, bold=False, align=None, font=FONT):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = shape.text_frame
    frame.word_wrap = True
    frame.margin_left = frame.margin_right = 0
    frame.margin_top = frame.margin_bottom = 0
    for i, line in enumerate(str(content).split("\n")):
        paragraph = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
        paragraph.text = line
        paragraph.font.name = font
        paragraph.font.size = Pt(size)
        paragraph.font.bold = bold
        paragraph.font.color.rgb = rgb(color)
        paragraph.space_after = Pt(7)
        paragraph.line_spacing = 1.14
        if align is not None:
            paragraph.alignment = align
    return shape


def rect(slide, x, y, w, h, fill="FFFFFF", border=LINE, radius=True):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
                                   Inches(x), Inches(y), Inches(w), Inches(h))
    if radius:
        shape.adjustments[0] = 0.12
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(fill)
    shape.line.color.rgb = rgb(border or fill)
    shape.line.width = Pt(0.8)
    return shape


def pill(slide, label, x, y, w, color=TEAL, fill=PALE):
    rect(slide, x, y, w, 0.36, fill, fill)
    text(slide, label, x + 0.09, y + 0.065, w - 0.18, 0.24, 10, color, True)


def slide(section, title, subtitle=""):
    page = prs.slides.add_slide(prs.slide_layouts[6])
    page.background.fill.solid()
    page.background.fill.fore_color.rgb = rgb(BACKGROUND)
    text(page, section.upper(), 0.65, 0.38, 11.9, 0.25, 10, TEAL, True)
    text(page, title, 0.65, 0.91, 12.0, 0.62, 30, INK, True)
    if subtitle:
        text(page, subtitle, 0.67, 1.61, 11.9, 0.54, 14, MUTED)
    return page


def card(slide, title, body, x, y, w, h, accent=TEAL):
    rect(slide, x, y, w, h)
    text(slide, title, x + 0.22, y + 0.22, w - 0.44, 0.45, 19, accent, True)
    text(slide, body, x + 0.22, y + 0.88, w - 0.44, h - 1.02, 16, MUTED)


def note(page, title, duration, content):
    page.notes_slide.notes_text_frame.text = f"{title} — {duration}\n\n{content}"
    TALK.append((title, duration, content))


def picture_fit(page, path, x, y, w, h):
    with Image.open(path) as image:
        iw, ih = image.size
    scale = min(w / iw, h / ih)
    pw, ph = iw * scale, ih * scale
    page.shapes.add_picture(str(path), Inches(x + (w-pw)/2), Inches(y + (h-ph)/2), Inches(pw), Inches(ph))


def pct(value, decimals=0):
    return f"{100*value:.{decimals}f}".replace(".", ",") + " %"


def prepare_assets():
    source = ROOT / "doliprane-1000-mg-8-sachets-9261.dsGPD15_Z9IFisZmfHVEVVw5uGg.png"
    box_asset = ASSETS / "boite-doliprane.png"
    if source.exists():
        with Image.open(source) as image:
            image.convert("RGB").save(box_asset)
    screenshot = Path(os.getenv("PRESENTATION_UI_SCREENSHOT", "/tmp/opencode/mediscan-ui.png"))
    ui_asset = ASSETS / "interface.png"
    if screenshot.exists():
        with Image.open(screenshot) as image:
            w, h = image.size
            # Workspace crop of the genuine desktop browser test, not a mockup.
            image.crop((round(w*.087), round(h*.345), round(w*.924), round(h*.862))).convert("RGB").save(ui_asset)
    if not box_asset.exists() or not ui_asset.exists():
        raise FileNotFoundError("Assets manquants. Fournir la boîte et une capture réelle via PRESENTATION_UI_SCREENSHOT.")
    return box_asset, ui_asset


BOX, UI = prepare_assets()

# 01 — Title
p = slide("Mediscan / Challenge 02", "Reconnaissance de boîtes\nde médicaments")
# Give the two-line title its own large readable area.
p.shapes[-1].height = Inches(1.30)
text(p, "Vision par ordinateur + OCR français / arabe\nIdentification à partir d’un catalogue local", .68, 2.56, 6.3, 1.05, 22, MUTED)
pill(p, "PYTHON · FASTAPI · TESSERACT", .68, 4.02, 3.33)
text(p, "Un prototype explicable, évalué et capable de s’abstenir.", .68, 4.77, 6.5, .9, 22, TEAL, True)
text(p, "Présenté par : [votre nom]\nProjet académique · 2026", .68, 6.02, 6.4, .65, 14, MUTED)
rect(p, 8.05, 1.08, 4.58, 5.52)
picture_fit(p, BOX, 8.16, 1.35, 4.34, 4.40)
pill(p, "CAS RÉEL TESTÉ : DOLIPRANE", 8.57, 5.87, 3.49)
note(p, "Introduction", "30 s", "Présentez l’objectif en une phrase : partir de la photo d’une boîte et identifier une référence uniquement si les informations visibles le permettent. Le cas Doliprane illustré a été réellement testé avec le moteur OCR et l’API. Précisez que le projet porte sur le Challenge 2 ; le chatbot du Challenge 1 reste séparé. Remplacez [votre nom] avant de présenter.")

# 02 — Goal
p = slide("01 / Problématique", "Lire du texte ne suffit pas à identifier un produit.", "La même marque peut exister sous plusieurs forces, formes et conditionnements.")
card(p, "1. Lire", "Extraire le texte visible\nConserver le texte OCR brut\nNe pas inventer les mots manquants", .65, 2.40, 3.88, 2.55)
card(p, "2. Comprendre les champs", "Nom / marque\nForce : 1 000 mg\nForme et quantité : 8 sachets", 4.72, 2.40, 3.88, 2.55)
card(p, "3. Vérifier une référence", "Comparer au catalogue\nVérifier les conflits\nAccepter ou s’abstenir", 8.79, 2.40, 3.88, 2.55)
for x, label, fill, color in [(0.90,"Identifié",PALE,TEAL),(3.90,"Ambigu",AMBER_BG,AMBER),(6.90,"Inconnu",AMBER_BG,AMBER),(9.90,"Illisible","F5E8E7","9E5652")]:
    pill(p, label, x, 5.55, 2.45, color, fill)
text(p, "Périmètre : texte imprimé sur une boîte — pas d’ordonnance manuscrite ni de conseil de traitement.", .70, 6.28, 12, .5, 15, MUTED)
note(p, "Du texte à l’identification", "40 s", "Insistez sur la différence entre OCR et reconnaissance de produit. Doliprane seul ne distingue pas une force ou une présentation. Le système sépare donc lecture, extraction de champs et rapprochement. Les quatre issues sont normales : une photo valide ne doit pas systématiquement produire un médicament. La force décrit le produit ; le nombre de sachets décrit le conditionnement, pas un conseil de prise.")

# 03 — UI
p = slide("02 / Expérience utilisateur", "Une interface simple, une décision vérifiable.", "Capture réelle : sélection de l’image → API → OCR → Doliprane 1 000 mg identifié.")
rect(p, .65, 2.28, 9.12, 4.10)
picture_fit(p, UI, .76, 2.38, 8.90, 3.89)
text(p, "Dans le navigateur", 10.02, 2.50, 2.60, .5, 20, TEAL, True)
text(p, "01  Déposer une image\n\n02  Lancer l’analyse\n\n03  Voir les champs\n\n04  Inspecter OCR / JSON", 10.02, 3.18, 2.6, 2.8, 16, MUTED)
text(p, "Interface locale : http://127.0.0.1:8004/     |     Documentation : /docs", .70, 6.52, 12, .4, 14, TEAL, True)
note(p, "Interface et parcours utilisateur", "45 s", "Montrez le dépôt de fichier, l’aperçu, les quatre champs extraits et les panneaux OCR/JSON. Cette capture provient du test dans Chrome avec la vraie image fournie : ce n’est pas une maquette. L’interface est en HTML, CSS et JavaScript, servie par FastAPI sur le même port. Elle n’a pas de compilation ni de serveur frontend séparé. Les candidats ambigus restent explicitement non confirmés.")

# 04 — Architecture
p = slide("03 / Architecture", "Un pipeline modulaire, dans une application unique.", "Séparation des responsabilités ; un processus persistant pour les calculs OCR sur CPU.")
rect(p, 2.60, 2.22, 10.08, 2.55, PALE, LINE)
text(p, "PROCESSUS CPU PERSISTANT · modèle chargé une seule fois", 2.84, 2.39, 9.5, .35, 12, TEAL, True)
steps = [("API", "Envoi / limites\nErreurs HTTP"),("Image", "Décodage\nEXIF / taille"),("OCR", "Texte / boîtes\nFrançais + arabe"),("Extraction", "Nom / force\nForme / quantité"),("Catalogue", "Candidats\nConflits / score"),("Décision", "Identifié ou\nabstention")]
for i, (title, body) in enumerate(steps):
    x = .65 + i*2.04
    rect(p, x, 3.00, 1.83, 1.43)
    text(p, title, x+.13, 3.18, 1.58, .4, 18, TEAL, True)
    text(p, body, x+.13, 3.70, 1.58, .61, 13, MUTED)
    if i < 5:
        text(p, "→", x+1.85, 3.53, .18, .28, 13, TEAL)
card(p, "API réactive", "Le traitement natif ne bloque pas la boucle événementielle.", .65, 5.18, 5.88, 1.34)
card(p, "Composants testables", "Adaptateur OCR injectable et catalogue JSON local.", 6.75, 5.18, 5.92, 1.34)
# Compact bottom cards use a smaller body and explicit positions.
for shape in list(p.shapes)[-6:]:
    if shape.has_text_frame and shape.text_frame.text.startswith(("Le traitement", "Adaptateur")):
        shape.top = Inches(5.83); shape.height = Inches(.54)
        for paragraph in shape.text_frame.paragraphs: paragraph.font.size = Pt(14)
note(p, "Architecture", "50 s", "Décrivez les six étapes de gauche à droite. Le projet reste monolithique au sens déploiement : une application FastAPI et un worker local pour pouvoir interrompre réellement le calcul natif. Le catalogue est un fichier JSON, pas un serveur de base de données. Les modèles sont réutilisés par processus. Les dépendances du chatbot ne sont ni importées ni modifiées. L’injection permet de tester la logique indépendamment de l’OCR, complétée par des tests avec le moteur réel.")

# 05 — OCR
p = slide("04 / Choix techniques", "Tesseract sur CPU : un choix initial mesuré.", "Modèles officiels tessdata_fast : français (fra) et arabe (ara), versions et empreintes vérifiées.")
headers = ["Option", "Intérêt", "Compromis / décision"]
columns = [.87, 3.62, 7.17]
widths = [2.47, 3.27, 5.0]
for x, w, label in zip(columns, widths, headers): text(p, label, x, 2.38, w, .4, 15, TEAL, True)
rows = [
    ("Tesseract", "CPU, modèles légers,\nAPI native réutilisable", "Retenu pour le prototype.\nDifficultés sur chiffres arabo-indiens et mises en page."),
    ("EasyOCR", "Détection de texte de scène ;\nfrançais et arabe documentés", "Runtime Torch et modèles supplémentaires.\nPas de benchmark local comparatif annoncé."),
    ("PaddleOCR", "Pipelines multilingues ;\nmodèles arabe / latin distincts", "Installation et configuration plus complexes.\nNon installé pour ce premier prototype."),
]
for i, row in enumerate(rows):
    y = 2.94+i*1.02
    rect(p, .65, y-.08, 12.03, .96, "FFFFFF" if i%2==0 else "F0F4ED", LINE)
    for j, value in enumerate(row): text(p, value, columns[j], y+.10, widths[j], .72, 14, INK if j==0 else MUTED, j==0)
text(p, "Constat : le modèle français tessdata_best n’a pas corrigé seul le cas Doliprane ; il n’est pas activé.", .75, 6.28, 11.9, .56, 15, AMBER, True)
note(p, "Pourquoi Tesseract ?", "45 s", "Expliquez le choix par l’environnement Fedora/Python 3.12, le CPU et la simplicité. Tesserocr donne accès au moteur Tesseract natif, aux boîtes et aux confiances de mots. Les documentations officielles confirment les langues, mais cela ne prouve pas leur précision sur notre jeu. EasyOCR et PaddleOCR ont été étudiés documentairement, pas comparés par des chiffres inventés. Un modèle français best plus lourd a été essayé sur le cas difficile sans résoudre le problème ; il n’a pas été ajouté au chemin de production.")

# 06 — Real correction
p = slide("05 / Cas concret", "Doliprane : diagnostiquer l’échec avant de corriger.", "La boîte colorée combine une marque très grande, des chiffres inclinés et une petite unité « mg ».")
rect(p, .65, 2.26, 4.83, 4.24)
picture_fit(p, BOX, .78, 2.34, 4.56, 3.98)
text(p, "Avant : inconnu", 5.82, 2.35, 6.5, .4, 21, AMBER, True)
text(p, "Référence absente, sachets non extraits,\nforce mal lue par le passage automatique.", 5.84, 2.91, 6.47, .75, 17, MUTED)
text(p, "Correction fondée sur l’image", 5.82, 3.88, 6.5, .4, 21, TEAL, True)
text(p, "• Deux modes OCR complémentaires\n• Confirmation indépendante des chiffres\n• Lecture de l’unité immédiatement voisine\n• Ajout d’une référence officielle vérifiée", 5.84, 4.46, 6.45, 1.66, 16, MUTED)
text(p, "Résultat : 1 000 mg · poudre pour solution buvable · 8 sachets", .75, 6.65, 11.9, .36, 15, TEAL, True)
note(p, "Le cas Doliprane", "55 s", "Racontez le diagnostic : trois problèmes différents, pas seulement un mauvais OCR. Le catalogue ne contenait pas ce produit, l’extracteur ignorait les sachets et l’OCR global ratait la force. Le repli lit au maximum deux nombres ; il confirme tous leurs chiffres dans une région locale puis cherche une unité voisine. Aucune coordonnée propre à Doliprane n’est codée en dur et aucune force n’est déduite de la marque. Les passages bruts et les contradictions sont conservés. Le résultat est confirmé par un test API réel sur cette image, qui reste un seul cas de développement, pas une preuve de robustesse générale.")

# 07 — Match and abstain
p = slide("06 / Identification", "Le meilleur candidat n’est pas toujours acceptable.", "Un score de classement n’est ni une probabilité de produit ni la confiance de l’OCR.")
card(p, "Indices combinés", "Nom / alias : jusqu’à 70 points\nForce : 15 points\nForme : 8 points\nConditionnement : 7 points", .65, 2.35, 3.87, 3.08)
card(p, "Conditions d’acceptation", f"Similarité du nom ≥ {THRESHOLDS['accept_name']}\nScore ≥ {THRESHOLDS['accept_score']} / 100\nÉcart au suivant ≥ {THRESHOLDS['margin']} points\nForce visible et aucun conflit", 4.73, 2.35, 3.87, 3.08)
card(p, "Sinon : abstention", "Données manquantes → ambigu\nNom absent → inconnu\nForce contradictoire → refus\nTexte inexploitable → illisible", 8.81, 2.35, 3.87, 3.08, AMBER)
rect(p, .65, 5.73, 12.03, .82, AMBER_BG, AMBER_BG)
text(p, "Exemple : « Doliprane 500 mg » ne doit pas être identifié comme « Doliprane 1 000 mg ».", .88, 5.99, 11.55, .36, 16, AMBER, True)
note(p, "Score et abstention", "55 s", "Le nom sert à générer des candidats avec un seuil de 0,65, puis les autres champs départagent les références. Un champ en conflit est pénalisé et interdit l’acceptation. Une orthographe proche ne peut pas effacer un conflit clair de force. Les seuils ont été choisis sur les données de développement synthétiques, avec un objectif de zéro fausse acceptation observée et un départage conservateur. Ils ne sont pas une calibration probabiliste et ne garantissent pas le même comportement dans la population réelle. Les tests couvrent aussi B12 contre B6, les unités g/mg/mcg et les alias arabes explicites.")

# 08 — Catalogue
p = slide("07 / Référentiel", "Un catalogue réduit, mais traçable.", "Les données réelles sont séparées des données fictives de démonstration.")
card(p, "1 référence réelle vérifiée", "Doliprane 1 000 mg\nPoudre pour solution buvable\nBoîte de 8 sachets-dose\nCIP13 : 3400936246980", .65, 2.38, 5.88, 2.98)
card(p, "15 variantes fictives", "5 noms inventés × 3 forces\nAlias français / arabes explicites\nIdentifiants stables\nJeu de régression régénérable", 6.75, 2.38, 5.92, 2.98)
text(p, "Source réelle : Base de données publique des médicaments (France), CIS + présentations CIP.\nDroits et dates documentés ; aucun catalogue exhaustif marocain n’est revendiqué.", .74, 5.79, 11.9, .89, 17, MUTED)
note(p, "Provenance du catalogue", "40 s", "La référence réelle a été vérifiée dans les fichiers officiels français CIS et CIP. Le numéro CIS est 61681702. La mise à jour de la spécialité est datée du 29 septembre 2026, celle de la présentation du 27 octobre 2026. La licence autorise la réutilisation avec attribution et dates, sans caution officielle. Les faits d’identité ne donnent pas une licence sur le graphisme de l’emballage. Les 15 autres références sont explicitement inventées. N’affirmez pas que ce produit ou ce catalogue décrit le marché marocain.")

# 09 — Dataset
p = slide("08 / Protocole d’évaluation", "88 images synthétiques + un cas utilisateur séparé.", "Les cibles de collecte réelle ne sont pas remplacées par des images générées.")
for x, value, title, body in [( .65,"60","Images claires","15 variantes × 2 langues\n× 2 mises en page / splits"),(4.73,"20","Dégradations synthétiques","Rotation, flou, contraste,\néclairage et vues partielles"),(8.81,"8","Exemples négatifs","Produit absent, conflit,\ntexte non médical et image vide")]:
    rect(p, x, 2.33, 3.87, 2.73)
    text(p, value, x+.23, 2.53, 3.37, .70, 43, TEAL, True)
    text(p, title, x+.23, 3.34, 3.37, .42, 18, INK, True)
    text(p, body, x+.23, 4.00, 3.37, .75, 15, MUTED)
pill(p, "Développement : 34 images", .83, 5.42, 3.38)
pill(p, "Test réservé : 54 images", 4.61, 5.42, 3.38)
pill(p, "Cas Doliprane : hors test", 8.39, 5.42, 3.68)
text(p, "Toutes les copies dégradées d’un original restent dans le même split.\nÀ collecter : ≥ 15 variantes réelles et ≥ 60 photos avec provenance et droits vérifiés.", .74, 6.05, 11.9, .78, 16, MUTED)
note(p, "Données et séparation", "50 s", "Distinguez trois types de données : les rendus indépendants, leurs dégradations artificielles et le packshot utilisateur. Le manifeste fournit identifiants, familles, empreintes, labels et provenance. Les dégradations ne traversent pas les splits. Les 54 images test comprennent 50 images de produits connus et quatre négatifs ; vingt sont dégradées, donc les observations ne sont pas toutes indépendantes. La photo utilisateur n’est pas ajoutée rétroactivement au test : c’est un cas de développement, sans transcription exhaustive et avec des droits d’illustration non établis. La cible de 60 photos réelles n’est donc pas atteinte.")

# 10 — Overall measured results
p = slide("09 / Résultats mesurés", "Une bonne précision parmi les acceptations… au prix d’abstentions.", "Test synthétique réservé : 54 images — 50 positives connues et 4 négatives.")
metrics = [
    (pct(OVERALL["end_to_end_top1_accuracy"]), "Identification de bout en bout", "21 / 50 images connues acceptées correctement"),
    (pct(OVERALL["top3_candidate_recall"]), "Rappel des 3 premiers candidats", "37 / 50 références connues présentes au top 3"),
    ("21 / 21", "Acceptations correctes observées", "Petit échantillon synthétique ; pas une garantie"),
    ("0 / 4", "Fausses acceptations sur négatifs", "Trop peu de négatifs pour estimer un risque réel"),
]
for i, (value, label, detail) in enumerate(metrics):
    x = .65 + (i % 2)*6.10
    y = 2.32 + (i // 2)*1.78
    rect(p, x, y, 5.92, 1.57)
    text(p, value, x+.23, y+.15, 1.75, .70, 35, TEAL, True)
    text(p, label, x+2.02, y+.21, 3.63, .65, 16, INK, True)
    text(p, detail, x+.23, y+1.06, 5.43, .36, 12, MUTED)
text(p, f"Acceptation : {pct(OVERALL['acceptance_rate'], 2)}  |  Abstention : {pct(OVERALL['abstention_rate'], 2)}", .75, 6.12, 11.8, .4, 18, TEAL, True)
text(p, f"Latence chaude p50 : {OVERALL['latency_p50_ms']:.0f} ms · p95 : {OVERALL['latency_p95_ms']/1000:.2f} s · Intel i5-1335U, CPU seul, hors HTTP et démarrage".replace("1.03", "1,03"), .75, 6.65, 11.8, .32, 12, MUTED)
note(p, "Interpréter les résultats globaux", "60 s", "Commencez par l’exactitude de bout en bout : 21 sur 50, soit 42 %, et non 100 %. Les 100 % observés concernent uniquement les 21 résultats que le système a accepté de donner. Le taux d’acceptation sur toutes les images est de 38,89 %, donc il s’abstient souvent. Quatre négatifs seulement ne permettent pas de conclure à un risque nul. Le top 3 est utile pour comprendre la génération de candidats mais ne remplace pas une identification correcte. Les temps sont ceux du service préchauffé, avec décodage et OCR, sans réseau ni chargement initial.")

# 11 — Languages
p = slide("10 / Limite principale", "Français et arabe : des performances très différentes.", "Même moteur initial, mais la lecture des chiffres arabo-indiens reste un obstacle mesuré.")
for i, (key, label) in enumerate([("fr", "Français"), ("ar", "Arabe")]):
    row = LANGUAGES[key]
    y = 2.52 + i*1.40
    text(p, label, .78, y, 2.12, .42, 22, TEAL if key=="fr" else AMBER, True)
    rect(p, 3.02, y+.05, 7.36, .36, "E3EAE0", "E3EAE0")
    if row["end_to_end_top1_accuracy"]:
        rect(p, 3.02, y+.05, 7.36*row["end_to_end_top1_accuracy"], .36, TEAL, TEAL)
    text(p, f"{row['accepted_count']} / {row['known_count']}", 10.67, y-.04, 1.85, .52, 25, TEAL if key=="fr" else AMBER, True)
    text(p, f"CER primaire : {pct(row['cer'],2)}   ·   WER primaire : {pct(row['wer'],2)}", 3.02, y+.57, 9.4, .42, 16, MUTED)
rect(p, .65, 5.45, 12.03, 1.08, AMBER_BG, AMBER_BG)
text(p, "La prise en charge d’une langue par le moteur ne prouve pas une identification fiable.\nQuand la force n’est pas lisible, le système refuse de deviner.", .89, 5.69, 11.55, .73, 18, AMBER, True)
note(p, "La limite arabe", "55 s", "Les 25 images positives françaises incluent 21 acceptations correctes. Pour les 25 images positives arabes, aucune identification n’a été acceptée. Les alias arabes peuvent être lus, mais les chiffres de force ou de quantité sont fréquemment omis ou confondus. Les CER et WER affichés concernent le passage OCR primaire, en conservant les distinctions de chiffres, accents et casse ; la fusion auxiliaire n’est pas évaluée par ces taux. Le texte de référence est celui du générateur, pas une transcription manuelle de boîtes réelles. Il n’y a pas de négatif arabe dans ce petit test ; on ne peut pas annoncer son taux de faux positifs.")

# 12 — Reliability
p = slide("11 / Fiabilité et ressources", "Une API bornée plutôt qu’une file d’attente incontrôlée.", "Une instance serveur recommandée sur ce déploiement CPU ; erreurs explicites, calcul natif interruptible.")
card(p, "Contrat HTTP", "GET / → interface\nGET /health → état OCR\nPOST /api/recognize → image\n/docs → contrat OpenAPI", .65, 2.37, 3.87, 3.10)
card(p, "Limites d’entrée", "JPEG / PNG réellement décodés\n8 Mio · 16 millions de pixels\n1 traitement admis à la fois\nSurcharge → HTTP 429", 4.73, 2.37, 3.87, 3.10)
card(p, "Délai et erreurs", "Upload : 10 s · calcul : 20 s\nTimeout → processus terminé\nDépendance absente → 503\nCalcul trop long → 504", 8.81, 2.37, 3.87, 3.10)
text(p, "Les logs contiennent l’ID de requête, la durée et la catégorie — pas l’image ni le texte intégral.\nAnnuler une attente asynchrone ne suffit pas à arrêter un calcul OCR natif.", .75, 5.92, 11.8, .88, 17, MUTED)
note(p, "Fiabilité", "45 s", "L’API valide le contenu décodé, pas seulement l’extension. Elle limite la taille, les pixels et la concurrence. Le worker persistant est terminé et rejoint si son délai de calcul est dépassé : cela évite d’annoncer qu’un simple timeout Python aurait arrêté le code natif. Les requêtes supplémentaires sont rejetées, pas mises dans une file infinie. Plusieurs workers du serveur multiplieraient les modèles et la capacité CPU, d’où la recommandation d’un seul. Les images ne sont pas conservées par défaut et les erreurs clients ne contiennent pas de traceback.")

# 13 — Tests and demo
p = slide("12 / Vérification et démonstration", "Des tests de composants jusqu’au navigateur.", "41 tests Python réussis localement + test réel de l’interface dans Chrome.")
card(p, "Tests automatisés", "Normalisation, unités, alias\nForces et formes contradictoires\nValidation des images et surcharge\nTimeout réel / redémarrage OCR", .65, 2.34, 5.88, 2.71)
card(p, "Scénario devant le professeur", "1. Doliprane → identifié\n2. Marque seule → ambigu\n3. Produit absent → inconnu\n4. Image vide → illisible", 6.75, 2.34, 5.92, 2.71)
rect(p, .65, 5.38, 12.03, 1.12, INK, INK)
text(p, ".venv/bin/python -m uvicorn recognition.api:app --host 127.0.0.1 --port 8004 --workers 1", .88, 5.62, 11.55, .35, 13, "FFFFFF", font="Liberation Mono")
text(p, "Ouvrir http://127.0.0.1:8004/ · Conserver les captures comme solution de secours.", .88, 6.07, 11.55, .29, 13, "C8DED2")
note(p, "Démonstration", "70 s", "Avant le cours, démarrez le serveur sur le port 8004 et ouvrez l’interface. Uploadez le fichier Doliprane situé à la racine du projet : nom, 1000 mg, poudre pour solution buvable, 8 unités doivent apparaître. Pour l’ambiguïté, utilisez data/demo/images/demo-01-250-fr-test-partial.png ; pour l’inconnu, negative-unknown-test.png ; pour l’illisible, negative-blank-test.png. Si le temps manque, montrez Doliprane et l’image partielle. Le test navigateur réel vérifie le premier résultat ; les états supplémentaires, le texte non interprété en HTML, la surcharge et le mobile sont aussi testés. Le test privé est ignoré si le fichier utilisateur manque dans une autre installation.")

# 14 — Conclusion
p = slide("13 / Bilan et perspectives", "Un prototype fonctionnel, avec des limites identifiées.", "La suite du projet doit être guidée par des données réelles, pas par une infrastructure plus complexe.")
card(p, "Ce qui fonctionne", "Pipeline image → décision\nCas Doliprane vérifié\nAPI et interface locales\nAbstention et résultats explicables", .65, 2.37, 3.87, 2.94)
card(p, "Ce qui reste limité", "Catalogue réel très réduit\nChiffres arabo-indiens\nÉclairage / perspectives difficiles\nPeu de négatifs indépendants", 4.73, 2.37, 3.87, 2.94, AMBER)
card(p, "Prochaines étapes", "Collecter des photos autorisées\nEnrichir le catalogue sourcé\nComparer les OCR sur ces photos\nRecalibrer sur le développement", 8.81, 2.37, 3.87, 2.94)
text(p, "Reconnaître quand les preuves suffisent. S’abstenir quand elles ne suffisent pas.", .78, 5.87, 11.8, .90, 26, TEAL, True)
note(p, "Conclusion", "45 s", "Résumez la contribution : une séparation nette entre OCR et identité produit, une application utilisable et une évaluation honnête. Le prototype ne constitue pas encore un système de reconnaissance robuste de tous les médicaments marocains. La priorité est un jeu réel documenté d’au moins 15 variantes et 60 photos, avec davantage de négatifs et de textes arabes. Ensuite seulement, comparer un moteur de texte de scène et reconsidérer les prétraitements et seuils. Le chatbot existant est préservé et aucun entraînement, stock, prix ou infrastructure distribuée n’a été ajouté.")

# 15 — Sources
p = slide("Annexe / Sources", "Références et éléments reproductibles.", "Documentation officielle vérifiée et résultats locaux ; aucune métrique comparative inventée.")
references = [
    ("Tesseract / langues et modèles", "https://tesseract-ocr.github.io/tessdoc/Data-Files-in-different-versions.html"),
    ("tesserocr / API Python native", "https://github.com/sirfz/tesserocr"),
    ("EasyOCR / langues et contraintes", "https://www.jaided.ai/easyocr/"),
    ("PaddleOCR / modèles multilingues", "https://www.paddleocr.ai/main/en/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.html"),
    ("Référence Doliprane / BDPM France", "https://base-donnees-publique.medicaments.gouv.fr/telechargement"),
    ("Mesures du projet", "reports/evaluation-test-layout-fallback.json\nreports/doliprane-regression.json"),
]
for i, (title, source) in enumerate(references):
    x = .70 + (i % 2)*6.08
    y = 2.30 + (i // 2)*1.28
    text(p, title, x, y, 5.63, .37, 16, TEAL, True)
    shape = text(p, source, x, y+.47, 5.63, .61, 11, MUTED)
    if source.startswith("https://"):
        for paragraph in shape.text_frame.paragraphs:
            for run in paragraph.runs: run.hyperlink.address = source
text(p, "Code, manifests, sources du catalogue, modèles vérifiés et notes orales sont livrés avec le projet.", .75, 6.54, 11.8, .36, 14, MUTED)
note(p, "Sources et questions", "Annexe", "Cette diapositive sert de référence, sans nécessiter une lecture à voix haute. Les métriques proviennent des JSON du projet et les identifiants réels des fichiers CIS/CIP de la BDPM. La capture d’écran provient d’un test réel ; l’illustration de la boîte a été fournie par l’utilisateur, sans source originale ni licence d’illustration vérifiée. La présentation est destinée à l’usage académique local demandé. Les références réelles françaises ne prouvent ni une disponibilité au Maroc ni la version exacte du graphisme de la boîte.")

for i, page in enumerate(prs.slides, 1):
    rect(page, .65, 7.00, 12.03, .012, LINE, LINE, False)
    text(page, "MEDISCAN  /  CHALLENGE 02", .68, 7.15, 8, .20, 9, MUTED)
    text(page, f"{i:02d} / {len(prs.slides):02d}", 11.52, 7.12, 1.12, .24, 10, TEAL, True, PP_ALIGN.RIGHT)

output = HERE / "Mediscan_Challenge_2.pptx"
prs.save(output)

guide = ["# Guide oral — Mediscan / Challenge 2", "", "Présentation : 14 diapositives principales + 1 annexe. Durée visée : environ 11 à 12 minutes, démonstration comprise.", "", "À personnaliser avant le cours : remplacer `[votre nom]` sur la première diapositive.", ""]
for i, (title, duration, content) in enumerate(TALK, 1):
    guide.extend([f"## {i:02d}. {title} — {duration}", "", content, ""])
guide.extend([
    "## Questions probables du professeur", "",
    "**Pourquoi ne pas demander le résultat à un LLM ?** Le but est de relier des preuves visibles à un référentiel vérifié, sans compléter des champs absents ou inventer un produit.", "",
    "**Le système est-il précis à 100 % ?** Non. Sur 50 images synthétiques connues, 21 ont été correctement identifiées et acceptées. Les 21/21 ne décrivent que la précision parmi les acceptations, pas l’exactitude globale.", "",
    "**Pourquoi annoncer français/arabe alors que l’arabe ne fonctionne pas bien ?** Le moteur est configuré pour les deux langues et son comportement est évalué. Le résultat arabe est une limitation mesurée, pas un objectif présenté comme atteint.", "",
    "**Pourquoi utiliser des médicaments fictifs ?** Pour disposer de régressions reproductibles sans fabriquer un catalogue réel ni redistribuer des illustrations de provenance incertaine. Cela ne remplace pas la collecte réelle requise.", "",
    "**Comment éviter la confusion entre 500 mg et 1 000 mg ?** Les forces sont normalisées puis comparées explicitement. Une contradiction interdit l’acceptation, même avec une marque très proche.", "",
    "**Pourquoi une base française pour un contexte marocain ?** C’est une référence vérifiable pour ce prototype précis, sans prétendre décrire le marché marocain. Il faut ensuite importer des références locales avec provenance et droits documentés.", "",
    "**Le timeout arrête-t-il vraiment le calcul ?** L’arrêt d’une attente asynchrone ne suffirait pas. Le superviseur termine et rejoint le processus OCR avant de libérer la capacité.", "",
    "**Quel est le principal travail restant ?** Collecter et annoter des photos réelles autorisées, ajouter des négatifs, puis comparer les OCR et recalibrer uniquement sur le développement.", "",
    "## Commandes de démonstration", "", "```bash", ".venv/bin/python -m uvicorn recognition.api:app --host 127.0.0.1 --port 8004 --workers 1", "```", "", "Interface : http://127.0.0.1:8004/", "Documentation : http://127.0.0.1:8004/docs", "",
    "Fichiers : boîte Doliprane à la racine ; `data/demo/images/demo-01-250-fr-test-partial.png` ; `data/demo/images/negative-unknown-test.png` ; `data/demo/images/negative-blank-test.png`.", "",
    "## Précautions de présentation des résultats", "", "Les taux globaux sont mesurés sur des données synthétiques. Le packshot Doliprane est un cas de développement séparé. Les latences excluent HTTP et démarrage. Les faibles effectifs et les familles d’images communes limitent les conclusions. Les CER/WER portent sur le passage primaire et sur des références générées, pas sur une transcription manuelle de photos réelles.", "",
])
(HERE / "guide_oral.md").write_text("\n".join(guide), encoding="utf-8")
print(f"Généré : {output} ({len(prs.slides)} diapositives, notes orales incluses)")
print(f"Guide : {HERE / 'guide_oral.md'}")
