# Avro Deserializer

`AvroDeserializer` lit des octets au format Confluent wire format, résout l'identifiant de schema intégré auprès d'Apicurio Registry, et retourne un dict Python (ou un objet du domaine si un hook `from_dict` est configuré).

## Utilisation de base

```python
from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroDeserializer
from apicurio_serdes.serialization import SerializationContext, MessageField

client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="com.example.schemas",
)

deserializer = AvroDeserializer(client)

ctx = SerializationContext("my-topic", MessageField.VALUE)
record = deserializer(kafka_message.value(), ctx)
# record est un dict Python : {"userId": "abc123", "country": "FR"}
```

## Paramètres

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `registry_client` | `ApicurioRegistryClient` | obligatoire | Le client registry utilisé pour résoudre les identifiants de schema. |
| `from_dict` | callable | `None` | Transformation optionnelle `(dict, ctx) -> Any` appliquée après le décodage. |
| `use_id` | `"contentId"` ou `"globalId"` | `"globalId"` | Comment interpréter l'identifiant de schema de 4 octets dans l'en-tête du wire format. |

### Mode d'identifiant de schema (`use_id`)

Le format Confluent wire format stocke un identifiant de schema de 4 octets aux octets 1–4. Le paramètre `use_id` contrôle comment cet entier est résolu auprès du registry :

| `use_id` | Endpoint du registry |
|----------|----------------------|
| `"globalId"` (défaut) | `GET /ids/globalIds/{id}` |
| `"contentId"` | `GET /ids/contentIds/{id}` |

**Important** : `use_id` doit correspondre à la valeur utilisée par le producteur. Si le producteur a intégré un `globalId`, le désérialiseur doit utiliser `use_id="globalId"`.

## Aller-retour avec AvroSerializer

```python
from apicurio_serdes.avro import AvroSerializer, AvroDeserializer

serializer = AvroSerializer(client, "UserEvent", use_id="contentId")
deserializer = AvroDeserializer(client, use_id="contentId")

ctx = SerializationContext("events", MessageField.VALUE)
data = {"userId": "abc123", "country": "FR"}
payload = serializer(data, ctx)

result = deserializer(payload, ctx)
assert result == data
```

## Transformation personnalisée (`from_dict`)

Passez un callable `from_dict` pour convertir le dict décodé en objet du domaine :

```python
from dataclasses import dataclass

@dataclass
class UserEvent:
    userId: str
    country: str

def from_dict(d: dict, ctx: SerializationContext) -> UserEvent:
    return UserEvent(userId=d["userId"], country=d["country"])

deserializer = AvroDeserializer(client, from_dict=from_dict)
event = deserializer(payload, ctx)
# event est une instance de UserEvent, pas un dict brut
```

Quand `from_dict` est `None` (valeur par défaut), le dict décodé est retourné directement.

## Mise en cache du schema

Les schemas résolus lors de la désérialisation sont mis en cache après la première requête au registry. Les désérialisations répétées de messages partageant le même identifiant de schema n'entraînent qu'un seul appel HTTP au registry. Le cache est thread-safe et partagé entre tous les désérialiseurs utilisant la même instance d'`ApicurioRegistryClient`.

## Gestion des erreurs

```python
from apicurio_serdes._errors import (
    DeserializationError,
    RegistryConnectionError,
    SchemaNotFoundError,
)

try:
    result = deserializer(payload, ctx)
except DeserializationError as e:
    # Magic byte invalide, trop peu d'octets, échec de décodage Avro, ou échec de from_dict
    print(f"Désérialisation échouée : {e}")
    if e.__cause__:
        print(f"Causé par : {e.__cause__}")
except SchemaNotFoundError as e:
    # L'identifiant de schema du wire format est introuvable dans le registry
    print(f"Schema inconnu : {e.id_type}={e.id_value}")
except RegistryConnectionError as e:
    # Registry inaccessible lors de la résolution du schema
    print(f"Le registry à {e.url} est inaccessible : {e}")
```

### Référence des exceptions

| Exception | Quand |
|-----------|-------|
| `DeserializationError` | Entrée de moins de 5 octets, magic byte ≠ `0x00`, payload Avro impossible à décoder, ou `from_dict` a levé une exception |
| `SchemaNotFoundError` | L'identifiant de schema du wire format est introuvable dans le registry (HTTP 404) |
| `RegistryConnectionError` | Registry inaccessible lors de la résolution du schema |
