# Audit et feuille de route

## Audit initial

| Exigence | Code existant | Manque | Action |
|---|---|---|---|
| Texte multilingue | `app_chainlit.py` traduit darija → arabe → anglais → Ollama → darija | Extraction structurée et évaluation absentes | Appel direct Ollama, évaluation séparée |
| API structurée | Interface Chainlit, `main.py` Streamlit | Pas d'API challenge 1 | FastAPI isolée |
| Contexte et clarification | Historique de texte Chainlit | Contexte structuré, corrections | Contrat validé, fusion explicite |
| Médicaments et disponibilité | Instructions textuelles du chatbot modifié | Entités, catalogue, ambiguïtés | Validation et catalogue de démonstration |
| Ressources et erreurs | Verrou de génération Chainlit | Saturation HTTP, timeout, erreurs normalisées | Async HTTP, limite de concurrence |
| Tests | Aucun test challenge 1 identifié | Corpus et métriques | Tests simulés et évaluation réelle |
| Hors périmètre | `ocr.py`, `rag.py`, interfaces existantes | Dépendances lourdes | Conserver sans utiliser |

État initial : `app_chainlit.py` modifié, `.chainlit/`, `.venv312/` et `__pycache__/` non suivis. Ollama local répond, `llama3.2:latest` présent. Python 3.12.15 et asyncio fonctionnent ; l'environnement `.venv312` importe FastAPI, Pydantic et HTTPX. `requirement.txt` n'épingle presque aucune version et inclut les dépendances des anciens composants.

## Ordre et validation

1. **Design** : contrats, erreurs et contexte documentés avant implémentation.
2. **Tranche verticale** : API → Ollama → validation → JSON, tester français et les deux écritures darija puis mélange.
3. **Métier** : plusieurs entités, catalogue, clarification et contexte ; vérifier les valeurs absentes et corrections.
4. **Évaluation** : tests simulés, corpus distinct d'au moins 60 exemples annotés, mesures réelles et limites observées.
5. **Livraison** : installation reproductible, documentation, sources et démonstration ; aucune affirmation de préparation clinique.
