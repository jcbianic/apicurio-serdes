# Mode Wire Format KAFKA_HEADERS

Le mode `WireFormat.KAFKA_HEADERS` permet de produire des messages Avro où
l'identifiant de schema est transporté dans les en-têtes du message Kafka plutôt
qu'intégré dans les octets du message. C'est un pattern de déploiement important
dans les configurations Apicurio Registry qui préfèrent des messages au contenu
propre avec une identification de schema hors-bande.

Contrairement au mode `CONFLUENT_PAYLOAD` par défaut (qui préfixe un octet magique
et un identifiant de schema sur 4 octets au payload), `KAFKA_HEADERS` produit du
binaire Avro brut comme corps du message et communique l'identifiant de schema via
un en-tête Kafka dédié.

## Configuration

Aucune dépendance supplémentaire n'est requise. Toutes les classes nécessaires font
partie de la bibliothèque principale.

```python
from apicurio_serdes import ApicurioRegistryClient, WireFormat
from apicurio_serdes.avro import AvroSerializer
from apicurio_serdes.serialization import SerializationContext, MessageField
```

Créez un client registry comme d'habitude :

```python
client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="com.example.schemas",
)
```

## Utilisation

### Sérialisation avec KAFKA_HEADERS

Passez `wire_format=WireFormat.KAFKA_HEADERS` lors de la construction du sérialiseur,
puis utilisez la méthode `serialize()` pour obtenir à la fois les octets du payload et
les en-têtes Kafka :

```python
serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
    wire_format=WireFormat.KAFKA_HEADERS,
)

ctx = SerializationContext(topic="user-events", field=MessageField.VALUE)

result = serializer.serialize({"userId": "abc", "country": "FR"}, ctx)

# result.payload  -> binaire Avro brut (sans octet magique, sans préfixe d'ID de schema)
# result.headers  -> {"apicurio.value.globalId": b"\x00\x00\x00\x00\x00\x00\x00\x01"}

# Passez les deux à votre producteur Kafka :
producer.produce(
    topic=ctx.topic,
    value=result.payload,
    headers=list(result.headers.items()),
)
```

La méthode `serialize()` retourne un dataclass `SerializedMessage` avec deux champs :

- **`payload`** (`bytes`) : Les données Avro binaires brutes — sans préfixe de cadrage.
- **`headers`** (`dict[str, bytes]`) : Un dict à une seule entrée avec l'en-tête
  d'identifiant de schema.

### Sérialisation d'une CLE Kafka

Lors de la sérialisation d'une clé de message, utilisez `MessageField.KEY` dans le
contexte de sérialisation. Le nom de l'en-tête utilise automatiquement le préfixe
`key` :

```python
serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserKey",
    wire_format=WireFormat.KAFKA_HEADERS,
)

ctx = SerializationContext(topic="user-events", field=MessageField.KEY)
result = serializer.serialize({"userId": "abc"}, ctx)

# La clé de result.headers est "apicurio.key.globalId"
```

### Utiliser contentId au lieu de globalId

Par défaut, l'en-tête transporte le `globalId`. Passez `use_id="contentId"` pour
utiliser l'identifiant de contenu à la place :

```python
serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
    use_id="contentId",
    wire_format=WireFormat.KAFKA_HEADERS,
)

ctx = SerializationContext(topic="user-events", field=MessageField.VALUE)
result = serializer.serialize({"userId": "abc", "country": "FR"}, ctx)

# La clé de result.headers est "apicurio.value.contentId"
```

### Le défaut CONFLUENT_PAYLOAD reste inchangé

Le code existant continue de fonctionner sans modification. Le wire format par défaut
reste `WireFormat.CONFLUENT_PAYLOAD` :

```python
# Sans argument wire_format -- utilise CONFLUENT_PAYLOAD par défaut
serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
)

ctx = SerializationContext(topic="user-events", field=MessageField.VALUE)
payload = serializer({"userId": "abc", "country": "FR"}, ctx)

# payload[0:1] == b"\x00"           (octet magique)
# payload[1:5]                       (ID de schema big-endian sur 4 octets)
# payload[5:]                        (données Avro binaires)
```

Passer `wire_format=WireFormat.CONFLUENT_PAYLOAD` explicitement produit une sortie
identique. La méthode `serialize()` fonctionne pour les deux modes — pour
CONFLUENT_PAYLOAD, `result.headers` est toujours un dict vide :

```python
result = serializer.serialize({"userId": "abc", "country": "FR"}, ctx)
# result.payload == serializer({"userId": "abc", "country": "FR"}, ctx)
# result.headers == {}
```

## Référence du format d'en-tête

Le nom de l'en-tête suit la convention de nommage native d'Apicurio Registry,
combinant le type de champ du message et le type d'identifiant :

| MessageField | use_id        | Nom de l'en-tête             | Encodage de la valeur de l'en-tête                |
|:-------------|:--------------|:-----------------------------|:--------------------------------------------------|
| VALUE        | `"globalId"`  | `apicurio.value.globalId`    | `struct.pack(">q", global_id)` — 8 octets         |
| VALUE        | `"contentId"` | `apicurio.value.contentId`   | `struct.pack(">q", content_id)` — 8 octets        |
| KEY          | `"globalId"`  | `apicurio.key.globalId`      | `struct.pack(">q", global_id)` — 8 octets         |
| KEY          | `"contentId"` | `apicurio.key.contentId`     | `struct.pack(">q", content_id)` — 8 octets        |

## Encodage de la valeur de l'en-tête

L'identifiant de schema est encodé comme un **entier signé big-endian sur 8 octets**
(`struct.pack(">q", schema_id)`). Cela correspond à l'encodage utilisé par le serde
Java KAFKA_HEADERS natif d'Apicurio Registry, assurant l'interopérabilité au niveau
des octets.

```python
import struct

# Encodage (Python -> valeur d'en-tête Kafka)
header_value = struct.pack(">q", schema_id)  # 8 octets

# Décodage (valeur d'en-tête Kafka -> Python)
(schema_id,) = struct.unpack(">q", header_value)

# Équivalent Java : ByteBuffer.wrap(headerBytes).getLong()
```

## Mise en cache des schemas

La mise en cache des schemas est entièrement préservée en mode KAFKA_HEADERS. La clé
de cache est `(group_id, artifact_id)`, identique au mode CONFLUENT_PAYLOAD. Quel que
soit le nombre de messages ou le paramètre de wire format, seul **un appel HTTP** est
effectué vers le registry par artifact unique :

```python
# 1 appel HTTP quel que soit le nombre de messages ou le wire_format
for record in records:
    result = serializer.serialize(record, ctx)
```

## Pour aller plus loin

- Exemples de démarrage rapide : `specs/004-kafka-headers-wire-format/quickstart.md`
- Spécification de la fonctionnalité : `specs/004-kafka-headers-wire-format/spec.md`
- Référence API : générée automatiquement depuis les docstrings dans
  `apicurio_serdes.serialization` et `apicurio_serdes.avro`
