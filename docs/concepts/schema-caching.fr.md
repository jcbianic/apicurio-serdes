# Mise en cache des schemas

`apicurio-serdes` met en cache les schemas après la première récupération afin que les appels de sérialisation
suivants n'effectuent pas de requêtes HTTP. Cette page explique le fonctionnement de la mise en cache des schemas et
ce qu'il faut en attendre.

## Fonctionnement du cache

Lorsque vous appelez un serializer pour la première fois, il demande à l'`ApicurioRegistryClient` de récupérer le
schema depuis le registry. Le client stocke le résultat sous forme de `CachedSchema` — une dataclass gelée (immutable)
— dans un cache en mémoire indexé par `(group_id, artifact_id)`. Le gel de l'entrée en cache empêche la mutation
accidentelle des données de schema partagées.

```text
First call:

  serializer(data, ctx)
       │
       ▼
  ApicurioRegistryClient.get_schema("UserEvent")
       │
       ├── Cache miss → HTTP GET /groups/.../artifacts/UserEvent/versions/latest/content
       │                  └── Store result in cache
       │
       └── Return CachedSchema (schema dict + globalId + contentId)


Subsequent calls:

  serializer(data, ctx)
       │
       ▼
  ApicurioRegistryClient.get_schema("UserEvent")
       │
       └── Cache hit → Return immediately (no HTTP request)
```

## Durée de vie du cache

Le cache persiste pendant toute la durée de vie de l'instance `ApicurioRegistryClient`. Par défaut, il n'y a pas de
TTL (time-to-live) ni d'expiration — une fois qu'un schema est mis en cache, il y reste jusqu'à ce que le client soit
collecté par le ramasse-miettes ou que l'entrée soit évincée par la politique LRU.

Les lookups basés sur l'artifact (`get_schema`, `register_schema`) peuvent recevoir un TTL configurable via
`cache_ttl_seconds`. Une fois le TTL écoulé, le prochain appel récupère à nouveau depuis le registry et intègre
automatiquement toute nouvelle version de schema.

Les lookups basés sur l'identifiant (`get_schema_by_global_id`, `get_schema_by_content_id`) sont adressés par contenu
et immuables — un `globalId` ou `contentId` fait toujours référence au même contenu de schema. Ces entrées n'expirent
jamais, quelle que soit la valeur de `cache_ttl_seconds`.

Cela signifie :

- **Au sein d'un processus de longue durée** (par ex., une boucle de consommation Kafka), les schemas sont récupérés
  une seule fois au démarrage et jamais ensuite (sauf si un TTL est configuré ou si des entrées sont évincées par la
  politique LRU).
- **Si un schema change dans le registry** et qu'aucun TTL n'est configuré, le client en cours d'exécution ne verra
  pas la nouvelle version avant un redémarrage. Avec `cache_ttl_seconds` configuré, le client intègre les nouvelles
  versions automatiquement après chaque fenêtre TTL.

```python
# Schema cached for the lifetime of this client
client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="com.example.schemas",
)

# All serializers sharing this client share the same cache
serializer_a = AvroSerializer(registry_client=client, artifact_id="UserEvent")
serializer_b = AvroSerializer(registry_client=client, artifact_id="OrderEvent")

# Only 2 HTTP requests total, regardless of how many messages are serialized
for event in events:
    serializer_a(event, ctx)
```

## Éviction du cache et limites de taille

Deux paramètres de constructeur contrôlent le comportement du cache :

- `cache_max_size` (défaut `1000`) : nombre maximum d'entrées dans chaque cache. Lorsque la limite est atteinte,
  l'entrée la moins récemment utilisée est évincée pour faire de la place aux nouvelles entrées (politique LRU).
  S'applique au cache de schemas et au cache d'identifiants.
- `cache_ttl_seconds` (défaut `None`) : TTL optionnel en secondes pour les entrées du cache de schemas basé sur
  l'artifact. Après cette durée, l'entrée est traitée comme un cache miss et le registry est de nouveau interrogé.
  Les entrées du cache d'identifiants n'expirent jamais.

```python
from apicurio_serdes import ApicurioRegistryClient

# Limiter les deux caches à 500 entrées et récupérer les schemas d'artifact toutes les 5 minutes
client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="com.example.schemas",
    cache_max_size=500,
    cache_ttl_seconds=300,
)
```

Ces deux paramètres lèvent une `ValueError` en cas de valeur invalide : `cache_max_size` doit être au moins `1` ;
`cache_ttl_seconds` doit être `None` ou strictement positif.

## Partage du cache

Plusieurs serializers qui partagent la même instance d'`ApicurioRegistryClient` partagent également le cache.
Si deux serializers utilisent le même `artifact_id`, le schema n'est récupéré qu'une seule fois :

```python
# Same client → same cache → one HTTP request for "UserEvent"
ser1 = AvroSerializer(registry_client=client, artifact_id="UserEvent")
ser2 = AvroSerializer(registry_client=client, artifact_id="UserEvent")
```

Si vous créez des instances distinctes d'`ApicurioRegistryClient`, chacune possède son propre cache indépendant.

## Thread Safety

Le cache est protégé par un verrou réentrant (`threading.RLock`). Plusieurs threads peuvent appeler `get_schema`
de manière concurrente en toute sécurité :

- Si deux threads demandent le même schema simultanément, un seul effectue la requête HTTP ; l'autre attend sur le
  verrou puis lit depuis le cache.
- Les opérations de lecture sur un schema déjà en cache n'acquièrent pas le verrou (chemin rapide).

Cela signifie que vous pouvez partager en toute sécurité une seule instance d'`ApicurioRegistryClient` et ses
serializers entre plusieurs threads dans un producteur multi-thread.

## Quand créer un nouveau client

Créez une nouvelle instance d'`ApicurioRegistryClient` lorsque :

- **Le schema a été mis à jour dans le registry** et vous avez besoin de la nouvelle version, et qu'aucun
  `cache_ttl_seconds` n'est configuré. Avec `cache_ttl_seconds` configuré, le client intègre les nouvelles versions
  de schemas automatiquement après chaque fenêtre TTL.
- **Vous vous connectez à un registry différent** ou changez de groupe.
- **Vous souhaitez réinitialiser le cache** (par ex., dans les tests).

Dans la plupart des scénarios de production, une seule instance de client par application est suffisante.
