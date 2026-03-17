# Guide de configuration CI/CD

Ce guide couvre la configuration du pipeline CI/CD pour le dépôt apicurio-serdes,
y compris les secrets GitHub, les règles de protection de branche et les intégrations
avec les services externes.

## Secrets requis

Le pipeline CI/CD nécessite un seul secret GitHub :

| Nom du secret | Source | Périmètre | Utilisé par |
|---|---|---|---|
| `TESTPYPI_API_TOKEN` | [TestPyPI](https://test.pypi.org/manage/account/token/) | Périmètre projet | Job `publish-testpypi` |

### Obtenir TESTPYPI_API_TOKEN

1. Créez un compte sur [test.pypi.org](https://test.pypi.org/account/register/)
2. Allez dans **Account Settings** > **API tokens**
   ([lien direct](https://test.pypi.org/manage/account/token/))
3. Cliquez sur **Add API token**
4. Définissez **Token name** sur `apicurio-serdes-ci` (ou similaire)
5. Définissez **Scope** sur **Project: apicurio-serdes** (si le projet existe sur
   TestPyPI) ou **Entire account** pour une configuration initiale
6. Cliquez sur **Add token** et copiez le token (commence par `pypi-`)

### Ajouter le secret à GitHub

1. Allez sur votre dépôt GitHub
2. Naviguez vers **Settings** > **Secrets and variables** > **Actions**
3. Cliquez sur **New repository secret**
4. Définissez **Name** sur `TESTPYPI_API_TOKEN`
5. Collez la valeur du token
6. Cliquez sur **Add secret**

Si le secret est manquant ou expiré, le job `publish-testpypi` échouera avec un
message d'erreur clair indiquant le nom du secret et où en obtenir un nouveau.

## Règles de protection de branche

Configurez la protection de branche pour la branche `main` dans les paramètres du
dépôt GitHub (Settings > Branches > Add rule) :

### Vérifications de statut requises

Activez **Require status checks to pass before merging** et ajoutez :

| Nom de la vérification | Ce qu'elle valide |
|---|---|
| `CI / lint` | Linting et formatage Ruff via pre-commit |
| `CI / typecheck` | Vérification stricte des types mypy |
| `CI / test` | pytest avec 100% de couverture de branches |
| `CI / docs-build` | Construction de la documentation MkDocs (mode strict) |

### Paramètres recommandés

- **Require branches to be up to date before merging** : Oui
- **Do not allow bypassing the above settings** : Oui

## Intégration ReadTheDocs

ReadTheDocs construit la documentation automatiquement via webhook (aucun secret
GitHub n'est requis).

### Configuration initiale

1. Connectez-vous à [readthedocs.org](https://readthedocs.org)
2. Cliquez sur **Import a Project**
3. Connectez votre compte GitHub et sélectionnez `apicurio-serdes`
4. ReadTheDocs configurera automatiquement un webhook sur votre dépôt GitHub

### Activer les builds de prévisualisation pour les PRs

1. Allez sur le projet sur ReadTheDocs
2. Naviguez vers **Admin** > **Advanced Settings**
3. Activez **Build pull requests for this project**
4. Enregistrez

Une fois activé, ReadTheDocs va :

- Construire la documentation à chaque push sur `main`
- Construire une documentation de prévisualisation pour chaque PR et ajouter une
  vérification de statut avec un lien de prévisualisation
- Construire la documentation versionnée pour les tags de release

## PRs en mode brouillon et comportement CI

Le pipeline CI est configuré pour minimiser l'utilisation des ressources pour les PRs
en brouillon :

| Job CI | S'exécute sur les PRs brouillon | S'exécute sur les PRs prêtes | S'exécute sur Push vers Main |
|---|---|---|---|
| `lint` | Oui | Oui | Oui |
| `typecheck` | Non | Oui | Oui |
| `test` | Non | Oui | Oui |
| `docs-build` | Non | Oui | Oui |
| `publish-testpypi` | Non | Oui | Non |

### Créer une PR en mode brouillon

Lors de l'ouverture d'une PR, sélectionnez **Create draft pull request** dans le menu
déroulant du bouton "Create pull request". Cela n'exécute que la vérification lint,
économisant des ressources CI pendant que votre travail est en cours.

### Marquer comme prête pour révision

Quand votre PR est prête, cliquez sur **Ready for review** sur la page de la PR. Cela
déclenche la suite CI complète (typecheck, test, docs-build et publish-testpypi).

## Dépannage

### TESTPYPI_API_TOKEN manquant

**Symptôme** : Le job `publish-testpypi` échoue avec :

```text
::error::TESTPYPI_API_TOKEN secret is not configured.
```

**Correction** : Suivez les étapes dans [Obtenir TESTPYPI_API_TOKEN](#obtenir-testpypi_api_token)
et [Ajouter le secret à GitHub](#ajouter-le-secret-à-github) ci-dessus.

### Token TestPyPI expiré

**Symptôme** : Le job `publish-testpypi` échoue pendant l'étape "Publish to TestPyPI"
avec une erreur d'authentification.

**Correction** : Générez un nouveau token sur
[TestPyPI](https://test.pypi.org/manage/account/token/) et mettez à jour le secret
`TESTPYPI_API_TOKEN` dans GitHub (Settings > Secrets and variables > Actions > cliquez
sur le secret > Update).

### Conflit de version TestPyPI

**Symptôme** : La publication échoue avec une erreur "File already exists".

**Correction** : C'est peu probable puisque les versions utilisent `github.run_number`
(globalement unique). Si cela se produit, relancez le workflow — le nouveau numéro
d'exécution produira une version unique.

### Échec de build ReadTheDocs

**Symptôme** : La vérification de statut ReadTheDocs échoue sur la PR.

**Correction** :

1. Cliquez sur le lien de vérification de statut pour voir le journal de build sur ReadTheDocs
2. Causes communes : références `mkdocs.yml` manquantes, liens brisés dans les docs,
   erreurs d'import Python dans `mkdocstrings`
3. Exécutez `uv run mkdocs build --strict` localement pour reproduire l'erreur

### CI ne s'exécute pas sur une PR brouillon marquée prête

**Symptôme** : Marquer une PR brouillon comme "Ready for review" ne déclenche pas le CI.

**Correction** : Vérifiez que `ready_for_review` est listé dans les types d'événement
`pull_request` dans `.github/workflows/ci.yml`. Poussez un commit vide pour
redéclencher si nécessaire.
