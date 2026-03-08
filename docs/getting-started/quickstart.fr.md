# Démarrage rapide

Sérialisez votre premier message Kafka avec `apicurio-serdes` en cinq minutes.

## Prérequis

- **Python 3.10+** installé
- **Apicurio Registry 3.x** en cours d'exécution et accessible (voir ci-dessous pour une installation locale)
- Un schema enregistré sous un `group_id` et un `artifact_id` connus

### Installation locale du registry

Si vous ne disposez pas d'un registry accessible, lancez-en un localement avec Docker :

```bash
docker run -it -p 8080:8080 quay.io/apicurio/apicurio-registry:latest
```

L'API v3 est désormais disponible à l'adresse `http://localhost:8080/apis/registry/v3`.

Enregistrez un schema de test à l'aide de l'API REST :

```bash
curl -X POST "http://localhost:8080/apis/registry/v3/groups/com.example.schemas/artifacts" \
  -H "Content-Type: application/json" \
  -H "X-Registry-ArtifactId: UserEvent" \
  -H "X-Registry-ArtifactType: AVRO" \
  -d '{
    "content": "{\"type\":\"record\",\"name\":\"UserEvent\",\"fields\":[{\"name\":\"userId\",\"type\":\"string\"},{\"name\":\"country\",\"type\":\"string\"}]}",
    "references": []
  }'
```

## Étape 1 — Installer la bibliothèque

```bash
pip install apicurio-serdes
```

Vérifiez l'installation :

```python
from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroSerializer

print("apicurio-serdes is ready.")
```

## Étape 2 — Créer un client registry

```python
from apicurio_serdes import ApicurioRegistryClient

client = ApicurioRegistryClient(
    url="http://localhost:8080/apis/registry/v3",
    group_id="com.example.schemas",
)
```

Le client se connecte à l'API Apicurio v3 et met en cache les schemas après la première récupération — le coût HTTP n'est payé qu'une seule fois par artifact.

`group_id` indique au client quel groupe de schemas utiliser pour chaque recherche. Dans Apicurio, les schemas sont organisés en groupes (similaires à des espaces de noms). Consultez [Modèle d'adressage](../concepts/addressing-model.md) pour plus de détails.

## Étape 3 — Créer un serializer

```python
from apicurio_serdes.avro import AvroSerializer

serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
)
```

Chaque serializer est lié à un seul artifact de schema. Créez un serializer par schema dont vous avez besoin.

## Étape 4 — Sérialiser un message

```python
from apicurio_serdes.serialization import SerializationContext, MessageField

ctx = SerializationContext(topic="user-events", field=MessageField.VALUE)
payload: bytes = serializer({"userId": "abc-123", "country": "FR"}, ctx)

print(f"Serialized {len(payload)} bytes")
# Serialized 16 bytes
```

`payload` est désormais au [wire format Confluent](../concepts/wire-format.md) en octets :

```text
Byte 0:      0x00               (magic byte)
Bytes 1–4:   schema ID          (big-endian uint32)
Bytes 5+:    Avro binary data   (schemaless encoding)
```

## Étape 5 — Envoyer vers Kafka

Utilisez n'importe quel client Kafka. Voici un exemple avec `confluent-kafka` :

```python
from confluent_kafka import Producer

producer = Producer({"bootstrap.servers": "localhost:9092"})
producer.produce("user-events", value=payload)
producer.flush()
```

## Script complet fonctionnel

```python
from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroSerializer
from apicurio_serdes.serialization import SerializationContext, MessageField

# Connect to the registry
client = ApicurioRegistryClient(
    url="http://localhost:8080/apis/registry/v3",
    group_id="com.example.schemas",
)

# Create a serializer for the UserEvent schema
serializer = AvroSerializer(registry_client=client, artifact_id="UserEvent")

# Serialize a message
ctx = SerializationContext(topic="user-events", field=MessageField.VALUE)
payload: bytes = serializer({"userId": "abc-123", "country": "FR"}, ctx)

print(f"Success! Serialized {len(payload)} bytes of Confluent-framed Avro.")
print(f"Magic byte: 0x{payload[0]:02x}")
print(f"Schema ID:  {int.from_bytes(payload[1:5], 'big')}")
```

## Dépannage

### URL du registry incorrecte

**Erreur** : `RegistryConnectionError: Unable to connect to registry at http://wrong-host:8080/...: ...`

**Cause** : Le paramètre `url` ne pointe pas vers un Apicurio Registry en cours d'exécution.

**Correction** : Vérifiez que le registry est en cours d'exécution et que l'URL inclut le chemin complet de l'API v3 :

```python
# Correct — includes /apis/registry/v3
client = ApicurioRegistryClient(
    url="http://localhost:8080/apis/registry/v3",
    group_id="com.example.schemas",
)

# Wrong — missing API path
client = ApicurioRegistryClient(
    url="http://localhost:8080",  # Will fail!
    group_id="com.example.schemas",
)
```

### Artifact inexistant

**Erreur** : `SchemaNotFoundError: Schema not found: artifact 'MySchema' in group 'default'`

**Cause** : L'`artifact_id` n'existe pas dans le groupe spécifié, ou le `group_id` est incorrect.

**Correction** : Vérifiez que le schema existe dans le registry sous le bon groupe :

```bash
# List artifacts in a group
curl "http://localhost:8080/apis/registry/v3/groups/com.example.schemas/artifacts"
```

Erreurs courantes :

- Le schema se trouve dans un groupe différent de celui que vous avez spécifié
- L'artifact ID est sensible à la casse — `UserEvent` n'est pas identique à `userevent`
- Le schema a été enregistré dans le groupe `default` mais vous le cherchez dans un groupe nommé

### Données d'entrée invalides

**Erreur** : `ValueError: ... is not a valid ...` (provenant de fastavro)

**Cause** : Le dictionnaire de données ne correspond pas au schema Avro — un champ obligatoire est manquant, un champ a le mauvais type, ou la structure des données ne correspond pas à la forme attendue par le schema.

**Correction** : Vérifiez que vos données correspondent exactement au schema :

```python
# Schema expects: {"userId": string, "country": string}

# Correct
serializer({"userId": "abc", "country": "FR"}, ctx)

# Wrong — missing required field "country"
serializer({"userId": "abc"}, ctx)

# Wrong — "userId" should be a string, not an int
serializer({"userId": 123, "country": "FR"}, ctx)
```

## Prochaines étapes

- [Guide du Avro Serializer](../user-guide/avro-serializer.md) — hooks `to_dict` personnalisés, options de wire format, mode strict
- [Migration depuis confluent-kafka](../migration/from-confluent-kafka.md) — comparaison d'API côte à côte
- [Référence API](../api-reference/index.md) — documentation complète des classes et méthodes
