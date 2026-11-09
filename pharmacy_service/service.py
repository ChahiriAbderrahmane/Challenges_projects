import json
import re
import unicodedata
from pathlib import Path
from .models import AnalyzeResponse

CATALOG = json.loads((Path(__file__).parent / 'catalog.json').read_text(encoding='utf-8'))

def normalized(value):
    return unicodedata.normalize('NFKC', str(value)).casefold().strip()

def present(value, source):
    return normalized(value) in normalized(source)

def analyze_extraction(request_id, request, extraction):
    # Only retain values traceable to either current text or client-provided context.
    context = request.context.model_dump_json(exclude_none=True) if request.context else ''
    source = request.text + ' ' + context
    warnings = []
    meds = []
    for med in extraction.medications:
        if not present(med.expressed_name, source):
            warnings.append('unverified_medication_removed')
            continue
        exact = re.search(re.escape(med.expressed_name), request.text, flags=re.IGNORECASE)
        if exact:
            med.expressed_name = exact.group()
        for field in ('quantity', 'unit', 'dosage', 'form'):
            value = getattr(med, field)
            if value is not None and not present(str(int(value)) if field == 'quantity' and float(value).is_integer() else value, source):
                setattr(med, field, None)
                warnings.append('unverified_' + field + '_removed')
        if med.quantity is None and med.unit is not None:
            med.unit = None
            warnings.append('unit_without_quantity_removed')
        med.catalog_id = med.normalized_name = None
        med.match_status = 'unknown'
        matches = [entry for entry in CATALOG if normalized(med.expressed_name) in [normalized(a) for a in entry['aliases']]]
        if len(matches) == 1:
            med.catalog_id, med.normalized_name, med.match_status = matches[0]['id'], matches[0]['name'], 'found'
        elif len(matches) > 1:
            med.match_status = 'ambiguous'
        meds.append(med)
    pharmacy = extraction.pharmacy
    for field in ('name', 'location'):
        value = getattr(pharmacy, field)
        if value and not present(value, source):
            setattr(pharmacy, field, None)
            warnings.append('unverified_pharmacy_' + field + '_removed')
    missing = []
    if set(extraction.intents) & {'medication_request', 'availability'} and not meds:
        missing.append('medications')
    if set(extraction.intents) & {'pharmacy_phone', 'pharmacy_location'} and not (pharmacy.name or pharmacy.location):
        missing.append('pharmacy')
    if 'unknown' in extraction.intents:
        missing.append('intent')
    if any(m.match_status == 'ambiguous' for m in meds):
        missing.append('medication_identity')
    questions = {'medications': 'Quel médicament recherchez-vous ?', 'pharmacy': 'Quelle pharmacie ou quelle localisation recherchez-vous ?', 'intent': 'Pouvez-vous préciser votre demande à la pharmacie ?', 'medication_identity': 'Pouvez-vous préciser le nom du médicament ?'}
    question = questions[missing[0]] if missing else None
    safe = {'Demande comprise.', 'Bonjour !', 'Je ne peux pas répondre à cette demande.'}
    if question:
        reply = question
    elif extraction.reply in safe:
        reply = extraction.reply
    elif 'out_of_scope' in extraction.intents:
        reply = 'Je ne peux pas répondre à cette demande.'
    elif extraction.intents == ['greeting']:
        reply = 'Bonjour !'
    else:
        reply = 'Demande comprise.'
    return AnalyzeResponse(request_id=request_id, original_text=request.text, language=extraction.language,
        intents=extraction.intents, medications=meds, pharmacy=pharmacy, needs_clarification=bool(missing),
        missing_fields=missing, clarification_question=question, reply=reply, warnings=list(dict.fromkeys(warnings)))
