# Conception — assistance patient/pharmacie

Le service interprète des messages textuels, sans accès à un stock ou annuaire, diagnostic, commande ni voix. La voix est une extension future non implémentée. Le catalogue local est une démonstration, pas une référence médicale. Prototype non destiné à un usage médical réel.

```text
client → FastAPI/validation → service → Ollama async (un appel JSON)
                                  ↓
                vérification des sources → catalogue local → clarification
                                  ↓
                        interprétation JSON + réponse
```

`GET /health` ne lance aucune génération. `POST /api/analyze` accepte `text` et `context` facultatif : une interprétation précédente simplifiée, limitée en taille ; Swagger décrit les champs. Les intentions autorisées sont `medication_request`, `availability`, `pharmacy_phone`, `pharmacy_location`, `greeting`, `out_of_scope`, `unknown`. Les médicaments ont nom exprimé, quantité/unité, dosage, forme et rapprochement catalogue. La posologie n'est pas déduite.

Le dernier message est analysé avec le contexte comme données. Les champs extraits doivent avoir une trace textuelle dans le message ou le contexte ; la fusion des corrections est déléguée au modèle et ne constitue pas une garantie. Une quantité n'est pas requise pour une disponibilité. Le nom de médicament est nécessaire pour une demande ou disponibilité ; nom ou localisation de pharmacie pour téléphone ou localisation. Les noms non reconnus sont conservés. La réponse générée n'est utilisée que si elle correspond à une formule sûre ; sinon une réponse déterministe est utilisée. Ceci réduit les affirmations non fondées sans garantir l'exactitude de l'extraction.

Une limite de concurrence par processus refuse immédiatement avec 503, sans file distribuée ; timeout 504, Ollama indisponible 503, sortie invalide 502, erreur de validation HTTP 422. Health ne vérifie pas l'état d'Ollama. Pas de retry : budget borné à un appel. Les logs contiennent identifiant, durée et catégorie, pas le texte. Les paramètres sont configurés par variables d'environnement. LLM local direct préféré à la chaîne de trois modèles de traduction ; résultats linguistiques à mesurer. Règles seules moins adaptées aux variations ; RAG, GPU et base serveur sans besoin démontré.
