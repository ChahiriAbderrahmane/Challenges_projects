# Évaluation préliminaire réelle

## Conditions

Le 27 octobre 2026, appels directs à l'API ASGI dans le même processus, Ollama local `llama3.2:latest`, 3.2B Q4_K_M, Python 3.12.15, concurrence 1, température 0, sans GPU déclaré. Quatre demandes exploratoires, sans corpus final indépendant. Les chiffres ci-dessous ne sont pas des métriques généralisables. Premier essai, aucune correction automatique.

| Message | Résultat observé | Problème |
|---|---|---|
| Avez-vous du Doliprane ? | `medication_request`, aucun médicament, clarification | Disponibilité et médicament manqués ; langue `mixed` au lieu de français |
| واش كاين دوليبران؟ | `greeting`, `out_of_scope`, `unknown`, aucun médicament | Intention et médicament manqués ; langue `arabic` plutôt que darija ; 22,7 s |
| wach kayn doliprane? | `medication_request`, aucun médicament | Disponibilité et médicament manqués ; langue `mixed` ; 15,8 s |
| wach kayn Doliprane 500 mg à Rabat ? | `medication_request`, aucun médicament | Disponibilité, médicament, dosage et localisation manqués ; 22,1 s |

Les quatre appels ont retourné un JSON validé (4/4), mais aucun n'a extrait le médicament demandé (0/4). Les réponses de clarification étaient donc trompeuses sur ces exemples. Les trois latences chronométrées sont indiquées individuellement ; la première n'a pas été chronométrée.

Une seconde version avec schéma Ollama simplifié et prompt plus explicite a été essayée sur ces mêmes quatre cas de développement : 4/4 intentions de disponibilité identifiées, 3/4 médicaments extraits et 4/4 JSON conformes. Temps mesurés respectivement : 73,4 s (chargement à froid), 19,2 s, 43,7 s et 37,4 s. La darija arabe n'a pas extrait le médicament ; la darija latine est marquée `undetermined` ; le mélange est marqué `french`, et Rabat est faussement classé nom de pharmacie. L'unité `mg` a été interprétée comme unité de quantité : un garde-fou supprimant l'unité sans quantité a ensuite été ajouté, sans mesure réelle supplémentaire. Ces cas ont servi au développement et ne constituent pas une évaluation finale indépendante.

Aucun p50/p95 représentatif ni précision/rappel/F1 ou taux d'affirmations non fondées n'a été mesuré. Aucun jeu de 60 cas indépendants n'a encore été constitué. La correction conversationnelle et la robustesse face aux injections ne sont pas validées avec le modèle réel.

Six tests automatisés avec LLM simulé ont réussi : limites d'entrée, erreurs, rapprochement exact, médicament inconnu, clarification et filtrage d'une réponse inventée. Ils ne prouvent pas la qualité linguistique. Le contrôle de présence textuelle est une simple heuristique, pas une preuve que l'entité est pertinente ou qu'une correction a été correctement appliquée.

## Suite nécessaire

Revoir le prompt et le schéma d'extraction en mesurant un jeu de développement distinct, puis évaluer au moins 60 cas annotés indépendants et mesurer les métriques demandées. Si la baseline reste insuffisante, comparer un modèle multilingue compact compatible CPU tel que Qwen2.5 3B Instruct quantifié, après vérification des ressources et des performances ; aucune amélioration n'est présumée et aucun modèle supplémentaire n'a été installé. Vérifier en particulier les corrections, la négation, les posologies, les noms arabes et l'injection. Le service actuel n'atteint pas les critères d'acceptation.
