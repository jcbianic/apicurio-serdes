# Pipeline CI/CD

Cette page documente le pipeline d'intégration et de livraison continue pour
apicurio-serdes.

## Architecture du pipeline

Le pipeline se compose de trois workflows GitHub Actions et d'une configuration
Dependabot :

| Workflow | Déclencheur | Objectif |
|----------|-------------|---------|
| `ci.yml` | Push sur main, pull requests | Portes qualité (lint, typecheck, test, docs) |
| `publish.yml` | Publication d'une GitHub Release | Publication du paquet vers TestPyPI → PyPI |
| `security.yml` | Push sur main, pull requests, planning hebdomadaire | Analyse des vulnérabilités et analyse CodeQL |
| `dependabot.yml` | Quotidien (pip), hebdomadaire (Actions) | PRs automatiques de mise à jour des dépendances |

## Workflow CI

Chaque push sur `main` et chaque pull request déclenche quatre jobs parallèles :

- **lint** — Exécute `ruff check .` pour l'analyse statique
- **typecheck** — Exécute `mypy` pour la vérification des types
- **test** — Exécute `pytest` avec 100% de couverture de branches sur Python
  3.10, 3.11, 3.12 et 3.13
- **docs** — Exécute `mkdocs build --strict` pour valider la construction de la documentation

Les quatre jobs doivent passer pour qu'une PR soit fusionnable.

### Rapport de couverture

Le job de test envoie les résultats de couverture à [Codecov](https://codecov.io).
Codecov fournit :

- Un badge de pourcentage de couverture dans le README
- Des commentaires sur les PRs montrant le delta de couverture par rapport à la branche de base
- Un tableau de bord public pour le dépôt

L'envoi vers Codecov est non bloquant — si le service Codecov est indisponible, le CI
passe ou échoue toujours selon l'application locale de la couverture.

## Workflow de publication

Le workflow de publication se déclenche lors de la création d'une GitHub Release. Il
exécute un pipeline séquentiel avec des portes strictes :

1. **validate-version** — Compare le tag de release (ex. `v0.2.0`) avec la version
   dans `pyproject.toml`. Échoue si les deux ne correspondent pas.
2. **build** — Exécute `uv build` pour produire les distributions sdist et wheel.
3. **publish-testpypi** — Publie sur TestPyPI via le trusted publishing OIDC.
4. **validate-testpypi** — Installe depuis TestPyPI et exécute un test d'import smoke.
5. **publish-pypi** — Publie sur PyPI via le trusted publishing OIDC.

Chaque étape nécessite que la précédente réussisse. Un échec à n'importe quelle étape
interrompt le pipeline.

### Configuration du Trusted Publishing

Le workflow de publication utilise le trusted publishing OIDC — aucun token API stocké
n'est nécessaire. Configurez les trusted publishers sur les deux registries :

**TestPyPI** (`https://test.pypi.org/manage/project/apicurio-serdes/settings/publishing/`) :

- Propriétaire du dépôt : `jcbianic`
- Nom du dépôt : `apicurio-serdes`
- Nom du workflow : `publish.yml`
- Nom de l'environnement : `testpypi`

**PyPI** (`https://pypi.org/manage/project/apicurio-serdes/settings/publishing/`) :

- Propriétaire du dépôt : `jcbianic`
- Nom du dépôt : `apicurio-serdes`
- Nom du workflow : `publish.yml`
- Nom de l'environnement : `pypi`

Créez deux environnements GitHub dans les paramètres du dépôt : `testpypi` et `pypi`.

## Workflow de sécurité

S'exécute à chaque push sur `main`, chaque PR vers `main`, et selon un planning
hebdomadaire (lundi 06:00 UTC) :

- **dependency-audit** — Exécute `pip-audit` pour analyser les vulnérabilités connues
  dans l'arbre de dépendances
- **codeql** — Exécute l'analyse de sécurité statique GitHub CodeQL pour Python

### Dependabot

Dependabot surveille les dépendances et crée des PRs de mise à jour automatiques :

- Écosystème **pip** : vérifié quotidiennement
- Écosystème **github-actions** : vérifié hebdomadairement

## Badges qualité

Le README affiche deux badges :

- **Statut CI** — Indique si la dernière exécution CI sur `main` a réussi ou échoué
- **Codecov** — Affiche le pourcentage de couverture actuel

## Processus de release

1. Mettre à jour la version dans `pyproject.toml` (ex. `0.2.0`)
2. Committer et fusionner sur `main`
3. Créer une GitHub Release avec un tag correspondant à la version (ex. `v0.2.0`)
4. Le workflow de publication gère automatiquement la publication TestPyPI → PyPI

## Checklist de configuration initiale

Après la fusion des fichiers de workflow :

- [ ] Activer la protection de branche sur `main` avec les vérifications de statut requises
- [ ] Marquer `lint`, `typecheck`, `test` et `docs` comme vérifications requises
- [ ] Installer l'[application GitHub Codecov](https://github.com/apps/codecov) sur le dépôt
- [ ] Configurer les trusted publishers sur TestPyPI et PyPI (voir ci-dessus)
- [ ] Créer l'environnement `testpypi` dans les paramètres du dépôt (sans règles de protection)
- [ ] Créer l'environnement `pypi` dans les paramètres du dépôt avec au moins un valideur requis
  (porte de publication en production)
- [ ] Activer les alertes Dependabot dans les paramètres du dépôt
