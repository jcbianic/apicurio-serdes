# Mise en cache des schemas

`apicurio-serdes` met en cache les schemas après la première récupération afin que les appels de sérialisation suivants n'effectuent pas de requêtes HTTP. Cette page explique quand le cache est alimenté, combien de temps il persiste et quelles garanties il offre.

## Fonctionnement du cache

Lorsque vous appelez un serializer pour la première fois, il demande à l'`ApicurioRegistryClient` de récupérer le schema depuis le registry. Le client stocke le résultat dans un cache en mémoire indexé par `(group_id, artifact_id)`.

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

Le cache persiste pendant toute la durée de vie de l'instance `ApicurioRegistryClient`. Il n'y a pas de TTL (time-to-live) ni d'expiration — une fois qu'un schema est mis en cache, il y reste jusqu'à ce que le client soit collecté par le ramasse-miettes.

Cela signifie :

- **Au sein d'un processus de longue durée** (par ex., une boucle de consommation Kafka), les schemas sont récupérés une seule fois au démarrage et jamais ensuite.
- **Si un schema change dans le registry**, le client en cours d'exécution ne verra pas la nouvelle version. Pour prendre en compte les changements de schema, créez une nouvelle instance d'`ApicurioRegistryClient`.

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

## Partage du cache

Plusieurs serializers qui partagent la même instance d'`ApicurioRegistryClient` partagent également le cache. Si deux serializers utilisent le même `artifact_id`, le schema n'est récupéré qu'une seule fois :

```python
# Same client → same cache → one HTTP request for "UserEvent"
ser1 = AvroSerializer(registry_client=client, artifact_id="UserEvent")
ser2 = AvroSerializer(registry_client=client, artifact_id="UserEvent")
```

Si vous créez des instances distinctes d'`ApicurioRegistryClient`, chacune possède son propre cache indépendant.

## Thread Safety

Le cache est protégé par un verrou réentrant (`threading.RLock`). Plusieurs threads peuvent appeler `get_schema` de manière concurrente en toute sécurité :

- Si deux threads demandent le même schema simultanément, un seul effectue la requête HTTP ; l'autre attend sur le verrou puis lit depuis le cache.
- Les opérations de lecture sur un schema déjà en cache n'acquièrent pas le verrou (chemin rapide).

Cela signifie que vous pouvez partager en toute sécurité une seule instance d'`ApicurioRegistryClient` et ses serializers entre plusieurs threads dans un producteur multi-thread.

## Quand créer un nouveau client

Créez une nouvelle instance d'`ApicurioRegistryClient` lorsque :

- **Le schema a été mis à jour dans le registry** et vous avez besoin de la nouvelle version.
- **Vous vous connectez à un registry différent** ou changez de groupe.
- **Vous souhaitez réinitialiser le cache** (par ex., dans les tests).

Dans la plupart des scénarios de production, une seule instance de client par application est suffisante.
