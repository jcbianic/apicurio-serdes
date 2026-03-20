# Authentification

Passez un argument `auth` à l'un ou l'autre client pour vous connecter à un registry
protégé. Deux gestionnaires sont intégrés : `BearerAuth` pour les tokens statiques ou
fournis par un provider, et `KeycloakAuth` pour les identifiants clients OAuth2 contre
un endpoint Keycloak.

Le paramètre `auth` est mutuellement exclusif avec `http_client` — si vous fournissez
votre propre client httpx, configurez l'authentification directement dessus.

## `BearerAuth` — token statique ou dynamique

### Token statique

```python
from apicurio_serdes import ApicurioRegistryClient, BearerAuth

auth = BearerAuth(token="my-static-token")

client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="com.example.schemas",
    auth=auth,
)
```

### Token dynamique (rafraîchi à chaque requête)

Passez un callable sans argument via `token_provider` à la place. Il est appelé à chaque
requête et peut retourner un token frais à chaque fois — utile pour les identifiants
de courte durée comme les tokens OIDC GCP ou les baux Vault :

```python
from apicurio_serdes import BearerAuth

auth = BearerAuth(token_provider=lambda: fetch_oidc_token())
```

`token` et `token_provider` sont mutuellement exclusifs ; exactement l'un des deux doit
être fourni.

## `KeycloakAuth` — identifiants clients OAuth2

Pour les registries protégés par Keycloak, `KeycloakAuth` gère le flux des identifiants
clients, y compris le rafraîchissement du token. Fournissez-lui une URL de token, un
identifiant client et un secret :

```python
from apicurio_serdes import ApicurioRegistryClient, KeycloakAuth

auth = KeycloakAuth(
    token_url="https://keycloak.example.com/realms/myrealm/protocol/openid-connect/token",
    client_id="my-client",
    client_secret="secret",
    scope="openid",          # optionnel
)

client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="com.example.schemas",
    auth=auth,
)
```

Le token est récupéré lors de la première requête. Ensuite, `KeycloakAuth` le rafraîchit
automatiquement lorsqu'il reste moins de 20% de son TTL. Le client asynchrone dispose de
son propre chemin de rafraîchissement non bloquant pour ne jamais bloquer la boucle
d'événements.

## Utilisation avec `AsyncApicurioRegistryClient`

`BearerAuth` et `KeycloakAuth` fonctionnent sans modification avec le client asynchrone :

```python
from apicurio_serdes import AsyncApicurioRegistryClient, KeycloakAuth

auth = KeycloakAuth(
    token_url="https://keycloak.example.com/realms/myrealm/protocol/openid-connect/token",
    client_id="my-client",
    client_secret="secret",
)

async with AsyncApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="com.example.schemas",
    auth=auth,
) as client:
    ...
```

## Utilisation d'un client `httpx` personnalisé (trappe de sortie)

Aucun des gestionnaires ne convient ? Fournissez directement un `httpx.Client`
préconfiguré via `http_client`. Le client est utilisé tel quel et `close()` ne le
touchera pas :

```python
import httpx
from apicurio_serdes import ApicurioRegistryClient

http_client = httpx.Client(
    headers={"X-Api-Key": "my-api-key"},
    verify="/chemin/vers/ca-personnalise.pem",
)

client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="com.example.schemas",
    http_client=http_client,
)
```

## Gestion des erreurs

Les échecs d'authentification lèvent `AuthenticationError` :

```python
from apicurio_serdes._errors import AuthenticationError

try:
    payload = serializer(data, ctx)
except AuthenticationError as e:
    print(f"Authentification échouée : {e}")
```

Voir [Gestion des erreurs](./error-handling.md#gerer-authenticationerror) pour les
causes fréquentes et les étapes de récupération.
