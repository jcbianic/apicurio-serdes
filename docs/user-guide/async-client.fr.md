# Client Registry Asynchrone

`AsyncApicurioRegistryClient` est l'équivalent asynchrone d'`ApicurioRegistryClient`.
Il utilise `httpx.AsyncClient` pour une communication HTTP non bloquante avec l'API
Apicurio Registry v3.

## Utilisation de base

```python
from apicurio_serdes import AsyncApicurioRegistryClient

client = AsyncApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="my-group",
)

cached = await client.get_schema("UserEvent")
print(cached.schema)      # Dict de schema Avro parsé
print(cached.global_id)   # globalId du registry
print(cached.content_id)  # contentId du registry
```

## Gestionnaire de contexte

Utilisez `async with` pour vous assurer que le pool de connexions HTTP sous-jacent est
fermé lorsque vous avez terminé :

```python
async with AsyncApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="my-group",
) as client:
    cached = await client.get_schema("UserEvent")
# Le pool de connexions est fermé ici
```

Si vous n'utilisez pas de gestionnaire de contexte, appelez explicitement `aclose()` :

```python
client = AsyncApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="my-group",
)
try:
    cached = await client.get_schema("UserEvent")
finally:
    await client.aclose()
```

## Intégration avec le lifespan FastAPI

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from apicurio_serdes import AsyncApicurioRegistryClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncApicurioRegistryClient(
        url="http://registry:8080/apis/registry/v3",
        group_id="my-group",
    ) as client:
        app.state.registry = client
        yield


app = FastAPI(lifespan=lifespan)


@app.post("/produce")
async def produce(request):
    client = request.app.state.registry
    cached = await client.get_schema("UserEvent")
    # Utiliser cached.schema pour la sérialisation...
```

## Comparaison Sync vs Async

| Fonctionnalité | Sync | Async |
|----------------|------|-------|
| Classe | `ApicurioRegistryClient` | `AsyncApicurioRegistryClient` |
| Récupération de schema | `client.get_schema(id)` | `await client.get_schema(id)` |
| Enregistrement de schema | `client.register_schema(id, schema)` | `await client.register_schema(id, schema)` |
| Type de retour | `CachedSchema` | `CachedSchema` (même classe) |
| Paramètres du constructeur | `url`, `group_id`, `max_retries`, `retry_backoff_ms`, `retry_max_backoff_ms`, `http_client`, `auth` | identiques |
| Sécurité du cache | `threading.RLock` | `asyncio.Lock` |
| Nettoyage | (GC automatique) | `async with` ou `await client.aclose()` |
| Erreurs | `SchemaNotFoundError`, `RegistryConnectionError` | Mêmes types d'erreurs |

## Enregistrement de schemas

`register_schema` publie un nouvel artifact de schema dans le registry. Le résultat est
mis en cache, de sorte qu'un appel ultérieur à `get_schema` pour le même `artifact_id`
est toujours un succès de cache sans requête HTTP supplémentaire :

```python
cached = await client.register_schema(
    "UserEvent",
    {
        "type": "record",
        "name": "UserEvent",
        "namespace": "com.example",
        "fields": [
            {"name": "userId", "type": "string"},
            {"name": "country", "type": "string"},
        ],
    },
    if_exists="FIND_OR_CREATE_VERSION",  # défaut — retourne la version existante ou en crée une nouvelle
)
print(cached.global_id)   # globalId assigné par le registry
print(cached.content_id)  # contentId assigné par le registry
```

Le paramètre `if_exists` accepte `"FAIL"`, `"FIND_OR_CREATE_VERSION"` (défaut), ou
`"CREATE_VERSION"`. `SchemaRegistrationError` est levée quand le registry retourne
une réponse 4xx ou 5xx.

## Gestion des erreurs

Le client asynchrone lève les mêmes types d'erreurs que le client synchrone :

```python
from apicurio_serdes._errors import (
    RegistryConnectionError,
    SchemaNotFoundError,
)

try:
    cached = await client.get_schema("NonExistent")
except SchemaNotFoundError as e:
    print(e.group_id)     # "my-group"
    print(e.artifact_id)  # "NonExistent"
except RegistryConnectionError as e:
    print(e.url)          # URL du registry injoignable
```

## Mise en cache

Les schemas sont mis en cache après la première récupération. Les appels suivants pour
le même `artifact_id` retournent le résultat en cache sans contacter le registry. Les
coroutines concurrentes demandant le même schema non mis en cache produiront exactement
une seule requête HTTP (prévention des stampedes via `asyncio.Lock`).
