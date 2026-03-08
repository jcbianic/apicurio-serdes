# Avro Serializer

`AvroSerializer` sérialise des données Python en octets Avro au format Confluent, en récupérant le schema depuis Apicurio Registry lors du premier appel.

## Utilisation de base

```python
from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroSerializer
from apicurio_serdes.serialization import SerializationContext, MessageField

client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="com.example.schemas",
)
serializer = AvroSerializer(registry_client=client, artifact_id="UserEvent")

ctx = SerializationContext(topic="user-events", field=MessageField.VALUE)
payload = serializer({"userId": "abc-123", "country": "FR"}, ctx)
```

## Hook to_dict personnalisé

Lorsque vos données applicatives ne sont pas déjà un simple dictionnaire, passez un callable `to_dict`. Il reçoit `(data, ctx)` et doit retourner un dictionnaire conforme au schema.

**Avec des dataclasses :**

```python
from dataclasses import dataclass, asdict

@dataclass
class UserEvent:
    userId: str
    country: str

serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
    to_dict=lambda obj, ctx: asdict(obj),
)

event = UserEvent(userId="abc-123", country="FR")
payload = serializer(event, ctx)
```

**Avec des modèles Pydantic :**

```python
from pydantic import BaseModel

class UserEvent(BaseModel):
    userId: str
    country: str

serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
    to_dict=lambda obj, ctx: obj.model_dump(),
)
```

**Avec un hook sensible au contexte** — `ctx` contient le nom du topic et le champ (KEY ou VALUE), ce qui est utile lorsqu'un même hook doit se comporter différemment selon le topic :

```python
def to_dict(obj, ctx):
    d = obj.model_dump()
    if ctx.field == MessageField.KEY:
        return {"userId": d["userId"]}
    return d
```

Si le callable to_dict lève une exception, `AvroSerializer` l'encapsule dans une `SerializationError` en conservant l'exception d'origine via `__cause__`.

## Wire format et schema ID

Par défaut, le serializer intègre le **globalId** dans l'en-tête du wire format, ce qui correspond au comportement par défaut d'Apicurio pour le wire format Confluent. Vous pouvez basculer vers **contentId** si votre consommateur l'attend :

```python
serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
    use_id="contentId",   # or "globalId" (default)
)
```

La structure du wire format est la suivante :

```
Byte 0:    0x00  (magic byte, Confluent convention)
Bytes 1-4: schema ID as 4-byte big-endian unsigned integer
Bytes 5+:  Avro binary payload (schemaless encoding)
```

## Strict mode

Par défaut, les champs supplémentaires dans le dictionnaire d'entrée qui ne figurent pas dans le schema sont silencieusement ignorés par fastavro. Activez `strict=True` pour les rejeter avec une `ValueError` :

```python
serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
    strict=True,
)

# Raises ValueError: Extra fields not in schema: internalFlag
serializer({"userId": "abc", "country": "FR", "internalFlag": True}, ctx)
```

## Mise en cache du schema

`AvroSerializer` récupère le schema une seule fois et le met en cache pour toute la durée de vie du client. Deux serializers partageant la même instance d'`ApicurioRegistryClient` partagent également le cache :

```python
# Only one HTTP request is made, regardless of how many messages are serialized
for event in events:
    payload = serializer(event, ctx)
```

Le cache est indexé par `(group_id, artifact_id)` et est thread-safe.

## Référence des erreurs

| Exception | Quand |
|---|---|
| `SchemaNotFoundError` | L'`artifact_id` n'existe pas dans le registre (HTTP 404). |
| `RegistryConnectionError` | Le registre est injoignable (erreur réseau). |
| `SerializationError` | Le callable to_dict a levé une exception. |
| `ValueError` | Les données ne sont pas conformes au schema Avro, ou le strict mode a rejeté des champs supplémentaires. |

```python
from apicurio_serdes._errors import SchemaNotFoundError, RegistryConnectionError, SerializationError

try:
    payload = serializer(data, ctx)
except SchemaNotFoundError as e:
    # e.group_id, e.artifact_id
    logger.error("Schema not found: %s / %s", e.group_id, e.artifact_id)
except RegistryConnectionError as e:
    # e.url
    logger.error("Registry unreachable: %s", e.url)
except SerializationError as e:
    # e.cause is the original exception from to_dict
    logger.error("to_dict failed: %s", e.cause)
except ValueError as e:
    logger.error("Schema validation failed: %s", e)
```
